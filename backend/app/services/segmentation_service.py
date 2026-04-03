import cv2
import numpy as np
from typing import List, Tuple, Optional, Generator
from pathlib import Path
import logging
import json
from datetime import datetime
from dataclasses import dataclass

from app.config import settings
from app.models.detection import BoundingBox, DetectionParameters, DetectionResult, SegmentationResult, ModelType
from app.utils.image_utils import ImageProcessor
from app.utils.file_utils import FileManager
from app.services.model_factory import get_model_factory
from app.services.exceptions import (
    ServiceException, DetectionException, SegmentationException,
    ModelInferenceException, ErrorCode
)

# 可选：YOLOv8 用于单支检测
try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False
    YOLO = None

# 可选：PyTorch 用于单字符 TorchScript 模型
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    torch = None


@dataclass
class SliceInfo:
    """切片信息"""
    x_offset: int  # 切片在原图中的 x 偏移
    y_offset: int  # 切片在原图中的 y 偏移
    width: int     # 切片宽度
    height: int    # 切片高度


class SahiInference:
    """SAHI (Slicing Aided Hyper Inference) 切片推理工具类"""

    @staticmethod
    def get_sahi_params_for_model(model_type) -> dict:
        """
        Get SAHI parameters optimized for specific model type

        单支检测模型参数：
        - YOLOv8: 标准参数
        - YOLOv11_FINETUNED: 微调模型参数

        Args:
            model_type: Detection model type (ModelType enum or string)

        Returns:
            Dict with slice_size, overlap_ratio, nms_threshold, use_soft_nms
        """
        # Handle string input by converting to ModelType if possible
        if isinstance(model_type, str):
            try:
                model_type = ModelType(model_type)
            except ValueError:
                # Unknown model type, default to YOLOv8 params
                return {
                    'slice_size': 640,
                    'overlap_ratio': 0.25,
                    'nms_threshold': 0.5,
                    'use_soft_nms': True,
                }

        params_map = {
            ModelType.YOLOV8: {
                'slice_size': 640,
                'overlap_ratio': 0.25,
                'nms_threshold': 0.35,
                'use_soft_nms': True,
            },
            ModelType.YOLOV11_FINETUNED: {
                'slice_size': 640,
                'overlap_ratio': 0.25,
                'nms_threshold': 0.35,
                'use_soft_nms': True,
            },
        }
        return params_map.get(model_type, params_map.get(ModelType.YOLOV8, {
            'slice_size': 640,
            'overlap_ratio': 0.25,
            'nms_threshold': 0.5,
            'use_soft_nms': True,
        }))

    @staticmethod
    def generate_slices(
        image_shape: Tuple[int, int],
        slice_size: int = 640,
        overlap_ratio: float = 0.25
    ) -> List[SliceInfo]:
        """
        生成切片信息列表

        Args:
            image_shape: 图像形状 (height, width)
            slice_size: 切片大小（正方形）
            overlap_ratio: 切片重叠比例

        Returns:
            切片信息列表
        """
        height, width = image_shape[:2]
        slices = []

        # 如果图像小于切片大小，直接返回整个图像作为一个切片
        if height <= slice_size and width <= slice_size:
            return [SliceInfo(0, 0, width, height)]

        # 计算步长（考虑重叠）
        stride = int(slice_size * (1 - overlap_ratio))

        # 生成切片
        y = 0
        while y < height:
            x = 0
            slice_h = min(slice_size, height - y)

            while x < width:
                slice_w = min(slice_size, width - x)

                slices.append(SliceInfo(x, y, slice_w, slice_h))

                # 如果已经到达右边界，跳出内层循环
                if x + slice_size >= width:
                    break
                x += stride

            # 如果已经到达下边界，跳出外层循环
            if y + slice_size >= height:
                break
            y += stride

        return slices

    @staticmethod
    def extract_slice(image: np.ndarray, slice_info: SliceInfo) -> np.ndarray:
        """
        从原图中提取切片

        Args:
            image: 原图
            slice_info: 切片信息

        Returns:
            切片图像
        """
        x, y = slice_info.x_offset, slice_info.y_offset
        return image[y:y + slice_info.height, x:x + slice_info.width].copy()

    @staticmethod
    def map_boxes_to_original(
        boxes: List[Tuple[float, float, float, float, float]],
        slice_info: SliceInfo,
        min_w: int = 5,
        min_h: int = 5
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        将切片上的检测框坐标映射回原图坐标

        Args:
            boxes: 切片上的检测框列表 (x1, y1, w, h, conf)
            slice_info: 切片信息
            min_w: 最小宽度过滤
            min_h: 最小高度过滤

        Returns:
            映射到原图坐标的检测框列表
        """
        mapped_boxes = []

        for x1, y1, w, h, conf in boxes:
            # 映射到原图坐标
            orig_x1 = x1 + slice_info.x_offset
            orig_y1 = y1 + slice_info.y_offset

            # 过滤太小的框
            if w < min_w or h < min_h:
                continue

            mapped_boxes.append((orig_x1, orig_y1, w, h, conf))

        return mapped_boxes

    @staticmethod
    def remove_overlapping_boxes(
        boxes: List[BoundingBox],
        iou_threshold: float = 0.3,
        min_confidence: float = 0.3
    ) -> List[BoundingBox]:
        """
        移除高重叠度的边界框（基于 IoU）

        算法说明：
        1. 按置信度降序排序
        2. 选择置信度最高的框作为"保留框"
        3. 计算其他框与"保留框"的 IoU
        4. 如果 IoU > 阈值，且置信度较低，则过滤掉该框
        5. 重复直到所有框都被处理

        Args:
            boxes: 边界框列表
            iou_threshold: IoU 阈值，超过此值的框视为重叠（默认 0.3 较严格）
            min_confidence: 最小置信度，低于此值的框直接过滤（默认 0.3）

        Returns:
            过滤后的边界框列表
        """
        if len(boxes) <= 1:
            return boxes

        # 按置信度降序排序
        sorted_boxes = sorted(boxes, key=lambda b: b.confidence, reverse=True)

        keep = []
        used = set()

        for i, box in enumerate(sorted_boxes):
            if i in used:
                continue

            # 过滤低置信度的框
            if box.confidence < min_confidence:
                used.add(i)
                continue

            # 保留当前框
            keep.append(box)
            used.add(i)

            # 计算与其他框的 IoU，标记高重叠的框
            for j in range(i + 1, len(sorted_boxes)):
                if j in used:
                    continue

                other = sorted_boxes[j]
                iou = SahiInference._calculate_iou(box, other)

                # 如果 IoU 超过阈值，过滤掉这个框（因为它的置信度较低）
                if iou > iou_threshold:
                    used.add(j)

        return keep

    @staticmethod
    def _calculate_iou(box1: BoundingBox, box2: BoundingBox) -> float:
        """
        计算两个边界框的 IoU（交并比）

        Args:
            box1: 第一个边界框
            box2: 第二个边界框

        Returns:
            IoU 值 (0-1)
        """
        # 转换为 (x1, y1, x2, y2) 格式
        x1_1, y1_1 = box1.x, box1.y
        x2_1, y2_1 = box1.x + box1.width, box1.y + box1.height

        x1_2, y1_2 = box2.x, box2.y
        x2_2, y2_2 = box2.x + box2.width, box2.y + box2.height

        # 计算交集
        xx1 = max(x1_1, x1_2)
        yy1 = max(y1_1, y1_2)
        xx2 = min(x2_1, x2_2)
        yy2 = min(y2_1, y2_2)

        inter_w = max(0, xx2 - xx1)
        inter_h = max(0, yy2 - yy1)
        inter_area = inter_w * inter_h

        # 计算并集
        area1 = box1.width * box1.height
        area2 = box2.width * box2.height
        union_area = area1 + area2 - inter_area

        # 计算 IoU
        if union_area == 0:
            return 0.0

        return inter_area / union_area

    @staticmethod
    def nms(
        boxes: List[Tuple[float, float, float, float, float]],
        iou_threshold: float = 0.5
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        非极大值抑制 (NMS)

        Args:
            boxes: 检测框列表 (x1, y1, w, h, conf)
            iou_threshold: IoU 阈值

        Returns:
            经过 NMS 过滤后的检测框列表
        """
        if not boxes:
            return []

        # 转换为 numpy 数组
        boxes_array = np.array(boxes)
        x1 = boxes_array[:, 0]
        y1 = boxes_array[:, 1]
        w = boxes_array[:, 2]
        h = boxes_array[:, 3]
        scores = boxes_array[:, 4]

        # 计算 x2, y2
        x2 = x1 + w
        y2 = y1 + h

        # 计算面积
        areas = w * h

        # 按置信度排序
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)

            # 计算 IoU
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            inter_w = np.maximum(0, xx2 - xx1)
            inter_h = np.maximum(0, yy2 - yy1)
            inter = inter_w * inter_h

            iou = inter / (areas[i] + areas[order[1:]] - inter)

            # 保留 IoU 小于阈值的框
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]

        return [boxes[i] for i in keep]

    @staticmethod
    def soft_nms(
        boxes: List[Tuple[float, float, float, float, float]],
        iou_threshold: float = 0.5,
        score_threshold: float = 0.001,
        sigma: float = 0.5
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        Soft-NMS: Apply score decay to overlapping boxes instead of hard suppression

        Args:
            boxes: 检测框列表 (x1, y1, w, h, conf)
            iou_threshold: IoU 阈值
            score_threshold: 置信度阈值
            sigma: 高斯衰减参数

        Returns:
            经过 Soft-NMS 过滤后的检测框列表
        """
        if not boxes:
            return []

        boxes_array = np.array(boxes, dtype=np.float64)
        x1 = boxes_array[:, 0].copy()
        y1 = boxes_array[:, 1].copy()
        w = boxes_array[:, 2].copy()
        h = boxes_array[:, 3].copy()
        scores = boxes_array[:, 4].copy()

        x2 = x1 + w
        y2 = y1 + h
        areas = w * h

        n = len(boxes)
        keep = []

        for _ in range(n):
            # 找到最高置信度的框
            max_idx = np.argmax(scores)
            max_score = scores[max_idx]

            # If max score is below threshold, stop
            if max_score < score_threshold:
                break

            # Add the box index to keep list with its current (possibly decayed) score
            keep.append((max_idx, max_score))

            # 计算 IoU
            xx1 = np.maximum(x1[max_idx], x1)
            yy1 = np.maximum(y1[max_idx], y1)
            xx2 = np.minimum(x2[max_idx], x2)
            yy2 = np.minimum(y2[max_idx], y2)

            inter_w = np.maximum(0, xx2 - xx1)
            inter_h = np.maximum(0, yy2 - yy1)
            inter = inter_w * inter_h

            iou = inter / (areas[max_idx] + areas - inter + 1e-10)

            # 高斯衰减 - only decay other boxes, not the current selected one
            weights = np.exp(-(iou ** 2) / sigma)
            weights[max_idx] = 0.0  # Set selected box score to 0 so it won't be selected again

            scores = scores * weights

        # Return boxes with their scores at time of selection
        return [boxes[i] for i, score in keep]


class SegmentationService:
    """图像切割服务"""

    def __init__(self):
        self.image_processor = ImageProcessor()
        self._model_factory = get_model_factory()
        # Keep old model caches for backward compatibility
        self._yolo_slip_model = None
        self._char_torchscript_model = None
        self._slip_torchscript_model = None
    
    def _get_yolo_slip_model(self):
        """懒加载单支检测 YOLO 模型（yolov8l.pt），仅当配置了路径且文件存在时加载。"""
        import logging
        log = logging.getLogger(__name__)

        if self._yolo_slip_model is not None:
            return self._yolo_slip_model
        if not _YOLO_AVAILABLE:
            log.debug("YOLO 单支: 未安装 ultralytics，使用 OpenCV 回退")
            return None
        if not getattr(settings, "yolov8_slip_model_path", None):
            return None
        path = settings.yolov8_slip_model_path.strip()
        if not path:
            return None
        p = Path(path)
        if not p.is_absolute():
            base = Path(__file__).resolve().parent.parent.parent
            p = base / path
        if not p.exists():
            log.warning("YOLO 单支: 模型文件不存在，使用 OpenCV 回退。路径: %s", p)
            return None
        try:
            self._yolo_slip_model = YOLO(str(p))
            log.info("YOLO 单支: 已加载模型 %s", p)
            return self._yolo_slip_model
        except Exception as e:
            log.warning("YOLO 单支: 加载失败 %s，使用 OpenCV 回退", e)
            return None

    def _get_char_torchscript_model(self):
        """懒加载单字符区域识别 TorchScript 模型（best.torchscript）。"""
        log = logging.getLogger(__name__)
        if self._char_torchscript_model is not None:
            return self._char_torchscript_model
        if not _TORCH_AVAILABLE:
            log.debug("单字符 TorchScript: 未安装 torch，使用 OpenCV 回退")
            return None
        path = getattr(settings, "char_torchscript_model_path", None) or ""
        path = path.strip()
        if not path:
            return None
        p = Path(path)
        if not p.is_absolute():
            base = Path(__file__).resolve().parent.parent.parent
            p = base / path
        if not p.exists():
            log.warning("单字符 TorchScript: 模型文件不存在 %s，使用 OpenCV 回退", p)
            return None
        try:
            # 用 Python 打开文件再传给 torch.jit.load，避免 Windows 下中文路径导致
            # LibTorch fopen "Illegal byte sequence" (errno 42)
            with open(p, "rb") as f:
                self._char_torchscript_model = torch.jit.load(f, map_location="cpu")
            self._char_torchscript_model.eval()
            log.info("单字符 TorchScript: 已加载模型 %s", p)
            return self._char_torchscript_model
        except Exception as e:
            log.warning("单字符 TorchScript: 加载失败 %s，使用 OpenCV 回退", e)
            return None

    def _get_slip_torchscript_model(self):
        """懒加载单支简牍 TorchScript 模型（默认 best.torchscript）。"""
        log = logging.getLogger(__name__)

        if self._slip_torchscript_model is not None:
            return self._slip_torchscript_model

        path = getattr(settings, "slip_torchscript_model_path", None) or ""
        if not path:
            return None

        p = Path(path)
        if not p.is_absolute():
            base = Path(__file__).resolve().parent.parent.parent
            p = base / path
        if not p.exists():
            log.warning("slip_torchscript_model_path 不存在: %s", path)
            return None

        try:
            import torch
            with open(str(p), "rb") as f:
                self._slip_torchscript_model = torch.jit.load(f, map_location="cpu")
            self._slip_torchscript_model.eval()
            log.info("单支 TorchScript 模型加载成功: %s", path)
            return self._slip_torchscript_model
        except Exception as e:
            log.warning("单支 TorchScript 模型加载失败: %s", e)
            return None

    def detect_single_slips(
        self,
        image: np.ndarray,
        params: Optional[DetectionParameters] = None
    ) -> List[BoundingBox]:
        """
        检测单支简牍。使用 ModelFactory 动态加载模型，支持 fallback 机制。

        模型优先级：
        1. params 指定的 model_type
        2. Fallback 链 (DeConv-YOLO -> APS-YOLO -> YOLOv8)
        3. OpenCV fallback
        """
        log = logging.getLogger(__name__)

        if params is None:
            params = DetectionParameters()

        try:
            # 图像增强预处理
            enhanced_image = ImageProcessor.enhance_for_detection(image, detection_type='slip')

            # ----------------------------------------------------------
            # 优先使用 TorchScript 模型（best.torchscript），与单字检测逻辑一致
            # ----------------------------------------------------------
            ts_model = self._get_slip_torchscript_model()
            if ts_model is not None:
                log.info("使用 TorchScript 模型进行单支检测")
                return self._detect_single_characters_torchscript(enhanced_image, params, ts_model)

            # 次选：ModelFactory YOLO 模型（带 fallback）
            model = self._model_factory.get_model(params.model_type, use_fallback=True)
            if model is not None:
                log.info("使用 %s 模型进行单支检测", params.model_type.value)
                return self._detect_single_slips_yolo(enhanced_image, params, model)

            # OpenCV fallback
            log.info("无可用模型，使用 OpenCV 回退")
            return self._detect_single_slips_opencv(enhanced_image, params)

        except ServiceException:
            raise
        except Exception as e:
            log.exception("单支简牍检测失败: %s", e)
            raise DetectionException(f"单支简牍检测失败: {str(e)}")
    
    def _detect_single_slips_yolo(
        self,
        image: np.ndarray,
        params: DetectionParameters,
        model,
    ) -> List[BoundingBox]:
        """使用 YOLO 检测单支简牍，带 NMS 后处理过滤重叠框"""
        import logging
        log = logging.getLogger(__name__)

        # 根据模型类型选择对应的置信度阈值
        if params.model_type == ModelType.YOLOV11_FINETUNED:
            conf_threshold = getattr(settings, "yolov11_finetuned_conf_threshold", 0.4)
        else:
            conf_threshold = getattr(settings, "yolov8_slip_conf_threshold", 0.01)

        # 获取 NMS 阈值
        nms_threshold = getattr(settings, "sahi_nms_threshold", 0.35)
        use_soft_nms = getattr(settings, "sahi_use_soft_nms", True)

        results = model.predict(
            source=image,
            conf=conf_threshold,
            verbose=False,
        )
        if not results or len(results) == 0:
            log.warning("YOLO 单支检测: 无推理结果")
            return []

        boxes_out = results[0].boxes
        if boxes_out is None or len(boxes_out) == 0:
            log.warning("YOLO 单支检测: 无检测框")
            return []

        xyxy = boxes_out.xyxy
        conf = boxes_out.conf
        cls = boxes_out.cls
        if hasattr(xyxy, "cpu"):
            xyxy = xyxy.cpu().numpy()
            conf = conf.cpu().numpy()
            cls = cls.cpu().numpy()
        xyxy = np.asarray(xyxy)
        conf = np.asarray(conf)
        cls = np.asarray(cls)

        log.info("YOLO 单支检测: 置信度阈值=%.2f, 原始框数=%d", conf_threshold, len(xyxy))

        # 构建检测框列表 (x1, y1, w, h, conf)
        raw_boxes = []
        for i in range(len(xyxy)):
            x1, y1, x2, y2 = float(xyxy[i, 0]), float(xyxy[i, 1]), float(xyxy[i, 2]), float(xyxy[i, 3])
            w = x2 - x1
            h = y2 - y1
            if w <= 0 or h <= 0:
                continue
            raw_boxes.append((x1, y1, w, h, float(conf[i])))

        # NMS / Soft-NMS 后处理，过滤重叠框
        if use_soft_nms:
            filtered_boxes = SahiInference.soft_nms(raw_boxes, iou_threshold=nms_threshold)
            log.info("YOLO 单支检测: Soft-NMS(iou=%.2f) 后剩余 %d 个框", nms_threshold, len(filtered_boxes))
        else:
            filtered_boxes = SahiInference.nms(raw_boxes, iou_threshold=nms_threshold)
            log.info("YOLO 单支检测: NMS(iou=%.2f) 后剩余 %d 个框", nms_threshold, len(filtered_boxes))

        # 转换为 BoundingBox 对象
        bounding_boxes = []
        for i, (x1, y1, w, h, c) in enumerate(filtered_boxes):
            bbox = BoundingBox(
                id=FileManager.generate_unique_id("bbox"),
                x=int(round(x1)),
                y=int(round(y1)),
                width=int(round(w)),
                height=int(round(h)),
                confidence=c,
                rotation=0.0,
                order=i + 1,
            )
            bounding_boxes.append(bbox)

        log.info("YOLO 单支检测: 最终返回 %d 个框", len(bounding_boxes))
        return self._sort_bounding_boxes(bounding_boxes, direction="left-to-right")
    
    def _detect_single_slips_opencv(
        self,
        image: np.ndarray,
        params: DetectionParameters,
    ) -> List[BoundingBox]:
        """OpenCV 边缘+轮廓的单支检测（未配置 YOLO 时的回退）。"""
        gray, binary = self.image_processor.preprocess_for_detection(image)
        edges = self.image_processor.detect_edges(gray, method="canny")
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=2)
        edges = cv2.erode(edges, kernel, iterations=1)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bounding_boxes = self._filter_slip_contours(contours, image.shape, params)
        return self._sort_bounding_boxes(bounding_boxes, direction="left-to-right")

    def _detect_single_characters_torchscript(
        self,
        image: np.ndarray,
        params: DetectionParameters,
        model,
    ) -> List[BoundingBox]:
        """
        使用 TorchScript 模型检测单字符区域（SAHI 切片推理模式）

        Args:
            image: 输入图像
            params: 检测参数
            model: TorchScript 模型

        Returns:
            检测到的边界框列表
        """
        log = logging.getLogger(__name__)
        conf_threshold = getattr(settings, "char_conf_threshold", 0.25)
        orig_h, orig_w = image.shape[:2]
        input_size = 640

        # SAHI 参数
        slice_size = getattr(settings, "sahi_slice_size", 640)
        overlap_ratio = getattr(settings, "sahi_overlap_ratio", 0.25)
        nms_threshold = getattr(settings, "sahi_nms_threshold", 0.5)
        use_soft_nms = getattr(settings, "sahi_use_soft_nms", True)

        # 判断是否需要切片推理
        need_slicing = orig_h > slice_size or orig_w > slice_size

        if need_slicing:
            log.info("单字符检测: 启用 SAHI 切片推理, 图像尺寸=%sx%s, 切片大小=%s, 重叠率=%.2f",
                     orig_w, orig_h, slice_size, overlap_ratio)

            # 生成切片信息
            slices = SahiInference.generate_slices(
                image.shape, slice_size=slice_size, overlap_ratio=overlap_ratio
            )
            log.info("单字符检测: 生成 %d 个切片", len(slices))

            all_boxes = []

            # 对每个切片进行推理
            for idx, slice_info in enumerate(slices):
                # 提取切片
                slice_image = SahiInference.extract_slice(image, slice_info)

                # 对切片进行推理
                slice_boxes = self._inference_on_slice(
                    slice_image, slice_info, model, input_size,
                    conf_threshold, params, log
                )

                all_boxes.extend(slice_boxes)

            log.info("单字符检测: 切片推理共检测到 %d 个框", len(all_boxes))

            # 合并重叠检测框
            if use_soft_nms:
                merged_boxes = SahiInference.soft_nms(all_boxes, iou_threshold=nms_threshold)
                log.info("单字符检测: Soft-NMS 后剩余 %d 个框", len(merged_boxes))
            else:
                merged_boxes = SahiInference.nms(all_boxes, iou_threshold=nms_threshold)
                log.info("单字符检测: NMS 后剩余 %d 个框", len(merged_boxes))

        else:
            # 图像较小，直接推理
            all_boxes = self._inference_on_slice(
                image, SliceInfo(0, 0, orig_w, orig_h), model, input_size,
                conf_threshold, params, log
            )
            merged_boxes = all_boxes
            log.info("单字符检测: 直接推理检测到 %d 个框", len(merged_boxes))

        # 过滤和格式转换
        min_w = max(5, getattr(params, "min_width", 20))
        min_h = max(5, getattr(params, "min_height", 20))
        max_w = getattr(params, "max_width", None) or orig_w
        max_h = getattr(params, "max_height", None) or orig_h

        out_boxes = []
        for x1, y1, bw, bh, conf in merged_boxes:
            # 边界检查
            x1 = max(0, min(x1, orig_w - 1))
            y1 = max(0, min(y1, orig_h - 1))
            x2 = min(x1 + bw, orig_w)
            y2 = min(y1 + bh, orig_h)
            bw = x2 - x1
            bh = y2 - y1

            # 尺寸过滤
            if bw < min_w or bh < min_h or bw > max_w or bh > max_h:
                continue

            bbox = BoundingBox(
                id=FileManager.generate_unique_id("char"),
                x=int(round(x1)),
                y=int(round(y1)),
                width=int(round(bw)),
                height=int(round(bh)),
                confidence=float(conf),
                rotation=0.0,
                order=len(out_boxes) + 1,
            )
            out_boxes.append(bbox)

        log.info("单字符检测: 最终输出 %d 个框", len(out_boxes))

        # 过滤重叠区域（基于 IoU），进一步减少重复检测
        filtered_boxes = SahiInference.remove_overlapping_boxes(out_boxes, iou_threshold=0.3, min_confidence=0.25)
        log.info("单字符检测：重叠过滤后剩余 %d 个框", len(filtered_boxes))

        return self._sort_bounding_boxes(filtered_boxes, direction="top-to-bottom")

    def _inference_on_slice(
        self,
        slice_image: np.ndarray,
        slice_info: SliceInfo,
        model,
        input_size: int,
        conf_threshold: float,
        params: DetectionParameters,
        log: logging.Logger
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        对单个切片进行推理

        Args:
            slice_image: 切片图像
            slice_info: 切片信息
            model: TorchScript 模型
            input_size: 模型输入大小
            conf_threshold: 置信度阈值
            params: 检测参数
            log: 日志记录器

        Returns:
            检测框列表 (x1, y1, w, h, conf) - 原图坐标
        """
        slice_h, slice_w = slice_image.shape[:2]

        # 预处理：BGR -> RGB, resize, normalize, HWC -> CHW, to tensor
        img_rgb = cv2.cvtColor(slice_image, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (input_size, input_size), interpolation=cv2.INTER_LINEAR)
        img_np = img_resized.astype(np.float32) / 255.0
        img_chw = np.transpose(img_np, (2, 0, 1))
        inp = torch.from_numpy(img_chw).unsqueeze(0)

        scale_x = slice_w / input_size
        scale_y = slice_h / input_size

        try:
            with torch.no_grad():
                out = model(inp)
        except Exception as e:
            log.warning("单字符 TorchScript 推理失败: %s", e)
            return []

        if out is None:
            return []

        if isinstance(out, (list, tuple)):
            out = out[0]

        pred = out
        if hasattr(pred, "cpu"):
            pred = pred.cpu().numpy()
        pred = np.asarray(pred)

        if pred.ndim != 3:
            return []

        # 解析输出形状 [1, 5, N]、[1, N, 5] 或 [1, 4+K, N]
        if pred.shape[0] != 1:
            pred = pred[np.newaxis, ...]

        b, dim, n = pred.shape[0], pred.shape[1], pred.shape[2]

        if dim >= 5 and n > dim:
            pred = np.squeeze(pred, axis=0).T
        elif dim > 5 and pred.shape[2] == dim:
            pred = np.squeeze(pred, axis=0)
        else:
            return []

        # 解析检测框
        boxes = []
        for i in range(pred.shape[0]):
            row = pred[i]
            if row.shape[0] < 5:
                continue

            conf = float(np.max(row[4:])) if row.shape[0] > 5 else float(row[4])
            if conf < conf_threshold:
                continue

            a, b0, c, d = float(row[0]), float(row[1]), float(row[2]), float(row[3])

            # 判断是 xyxy 还是 center-wh 格式
            if c > a and d > b0 and (c - a) < slice_w and (d - b0) < slice_h:
                x1, y1, x2, y2 = a, b0, c, d
            else:
                xc, yc, w, h = a, b0, c, d
                x1 = xc - w / 2
                y1 = yc - h / 2
                x2 = xc + w / 2
                y2 = yc + h / 2

            # 缩放到切片坐标
            x1 = x1 * scale_x
            y1 = y1 * scale_y
            x2 = x2 * scale_x
            y2 = y2 * scale_y

            # 边界限制
            x1 = max(0, min(x1, slice_w))
            y1 = max(0, min(y1, slice_h))
            x2 = max(0, min(x2, slice_w))
            y2 = max(0, min(y2, slice_h))

            bw = x2 - x1
            bh = y2 - y1

            if bw <= 0 or bh <= 0:
                continue

            # 映射到原图坐标
            orig_x1 = x1 + slice_info.x_offset
            orig_y1 = y1 + slice_info.y_offset

            boxes.append((orig_x1, orig_y1, bw, bh, conf))

        return boxes

    def _detect_single_characters_rga_crnn(
        self,
        image: np.ndarray,
        params: DetectionParameters,
        model
    ) -> List[BoundingBox]:
        '''
        使用 RGA-CRNN 模型检测单字符区域（SAHI 切片推理模式）
        
        RGA-CRNN (2026: Rotated Glyph Attention CRNN) 专用于字符识别，支持旋转处理
        '''
        log = logging.getLogger(__name__)
        log.info("RGA-CRNN 检测：当前使用 TorchScript 推理流程")
        # RGA-CRNN 使用与 TorchScript 相同的推理流程
        # 后续可根据需要扩展旋转校正等预处理
        return self._detect_single_characters_torchscript(image, params, model)
    
    def detect_single_characters(
        self,
        image: np.ndarray,
        params: Optional[DetectionParameters] = None
    ) -> List[BoundingBox]:
        """
        检测单个文字。使用 ModelFactory 动态加载模型，支持 RGA-CRNN 和 TorchScript。

        模型优先级：
        1. RGA-CRNN (如果指定 model_type)
        2. TorchScript character model
        3. OpenCV fallback
        """
        log = logging.getLogger(__name__)

        if params is None:
            params = DetectionParameters(
                min_width=20,
                min_height=20,
                max_width=150,
                max_height=150,
                aspect_ratio_min=0.3,
                aspect_ratio_max=3.0
            )

        try:
            # 图像增强预处理
            enhanced_image = ImageProcessor.enhance_for_detection(image, detection_type='character')

            # 直接使用 TorchScript 模型进行单字符检测
            model = self._get_char_torchscript_model()
            if model is not None:
                return self._detect_single_characters_torchscript(enhanced_image, params, model)

            # OpenCV fallback
            log.info("无可用模型，使用 OpenCV 回退")
            return self._detect_characters_opencv(enhanced_image, params)

        except ServiceException:
            raise
        except Exception as e:
            log.exception("单字符检测失败: %s", e)
            raise DetectionException(f"单字符检测失败: {str(e)}")

    def _detect_characters_opencv(
        self,
        image: np.ndarray,
        params: DetectionParameters
    ) -> List[BoundingBox]:
        """OpenCV 连通域检测单字符"""
        gray = self.image_processor.convert_to_grayscale(image)

        # 自适应二值化
        binary = self.image_processor.apply_binary_threshold(
            gray,
            method='adaptive',
            adaptive_block_size=15,
            adaptive_c=5
        )

        # 反转图像（如果背景是白色）
        if params.background_type == 'white':
            binary = cv2.bitwise_not(binary)

        # 形态学操作，去除噪点
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # 连通域分析
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )

        # 提取字符区域
        bounding_boxes = self._filter_character_regions(
            stats,
            num_labels,
            image.shape,
            params
        )

        # 合并距离很近的区域
        bounding_boxes = self._merge_close_regions(bounding_boxes, threshold=10)

        # 过滤重叠区域（基于 IoU）
        bounding_boxes = SahiInference.remove_overlapping_boxes(bounding_boxes, iou_threshold=0.3, min_confidence=0.3)

        # 排序（从上到下）
        return self._sort_bounding_boxes(bounding_boxes, direction='top-to-bottom')
    
    def _filter_slip_contours(
        self,
        contours: List,
        image_shape: Tuple,
        params: DetectionParameters
    ) -> List[BoundingBox]:
        """
        过滤简牍轮廓并提取边界框
        
        Args:
            contours: 轮廓列表
            image_shape: 图像形状
            params: 检测参数
            
        Returns:
            边界框列表
        """
        bounding_boxes = []
        img_height, img_width = image_shape[:2]
        
        for idx, contour in enumerate(contours):
            # 获取边界框
            x, y, w, h = cv2.boundingRect(contour)
            
            # 计算面积和长宽比
            area = w * h
            aspect_ratio = w / h if h > 0 else 0
            
            # 过滤条件
            if (w >= params.min_width and
                h >= params.min_height and
                params.aspect_ratio_min <= aspect_ratio <= params.aspect_ratio_max and
                area > 1000):  # 最小面积阈值
                
                # 排除太靠近边缘的框（可能是边界噪声）
                margin = 5
                if (x > margin and y > margin and
                    x + w < img_width - margin and
                    y + h < img_height - margin):
                    
                    # 计算置信度（基于轮廓面积与边界框面积的比值）
                    contour_area = cv2.contourArea(contour)
                    confidence = contour_area / area if area > 0 else 0
                    
                    bbox = BoundingBox(
                        id=FileManager.generate_unique_id('bbox'),
                        x=int(x),
                        y=int(y),
                        width=int(w),
                        height=int(h),
                        confidence=float(confidence),
                        rotation=0.0,
                        order=idx + 1
                    )
                    bounding_boxes.append(bbox)
        
        return bounding_boxes
    
    def _filter_character_regions(
        self,
        stats: np.ndarray,
        num_labels: int,
        image_shape: Tuple,
        params: DetectionParameters
    ) -> List[BoundingBox]:
        """
        过滤字符区域
        
        Args:
            stats: 连通域统计信息
            num_labels: 标签数量
            image_shape: 图像形状
            params: 检测参数
            
        Returns:
            边界框列表
        """
        bounding_boxes = []
        
        # 跳过背景（label 0）
        for i in range(1, num_labels):
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]
            
            # 计算长宽比
            aspect_ratio = w / h if h > 0 else 0
            
            # 过滤条件
            max_width = params.max_width or image_shape[1]
            max_height = params.max_height or image_shape[0]
            
            if (w >= params.min_width and
                h >= params.min_height and
                w <= max_width and
                h <= max_height and
                params.aspect_ratio_min <= aspect_ratio <= params.aspect_ratio_max and
                area > 50):  # 最小面积阈值
                
                bbox = BoundingBox(
                    id=FileManager.generate_unique_id('char'),
                    x=int(x),
                    y=int(y),
                    width=int(w),
                    height=int(h),
                    confidence=1.0,
                    rotation=0.0,
                    order=i
                )
                bounding_boxes.append(bbox)
        
        return bounding_boxes
    
    def _merge_close_regions(
        self,
        bounding_boxes: List[BoundingBox],
        threshold: int = 10
    ) -> List[BoundingBox]:
        """
        合并距离很近的区域
        
        Args:
            bounding_boxes: 边界框列表
            threshold: 距离阈值
            
        Returns:
            合并后的边界框列表
        """
        if len(bounding_boxes) <= 1:
            return bounding_boxes
        
        merged = []
        used = set()
        
        for i, box1 in enumerate(bounding_boxes):
            if i in used:
                continue
            
            # 初始化合并区域
            min_x = box1.x
            min_y = box1.y
            max_x = box1.x + box1.width
            max_y = box1.y + box1.height
            
            # 查找可以合并的框
            for j, box2 in enumerate(bounding_boxes[i+1:], start=i+1):
                if j in used:
                    continue
                
                # 计算垂直距离
                vertical_dist = abs(box1.y - box2.y)
                
                # 如果垂直距离很近，考虑合并
                if vertical_dist <= threshold:
                    # 检查水平重叠或接近
                    horizontal_gap = min(
                        abs(box1.x - (box2.x + box2.width)),
                        abs(box2.x - (box1.x + box1.width))
                    )
                    
                    if horizontal_gap <= threshold:
                        min_x = min(min_x, box2.x)
                        min_y = min(min_y, box2.y)
                        max_x = max(max_x, box2.x + box2.width)
                        max_y = max(max_y, box2.y + box2.height)
                        used.add(j)
            
            # 创建合并后的框
            merged_box = BoundingBox(
                id=box1.id,
                x=int(min_x),
                y=int(min_y),
                width=int(max_x - min_x),
                height=int(max_y - min_y),
                confidence=box1.confidence,
                rotation=0.0,
                order=box1.order
            )
            merged.append(merged_box)
            used.add(i)
        
        return merged
    
    def _sort_bounding_boxes(
        self,
        bounding_boxes: List[BoundingBox],
        direction: str = 'left-to-right'
    ) -> List[BoundingBox]:
        """
        排序边界框
        
        Args:
            bounding_boxes: 边界框列表
            direction: 排序方向 ('left-to-right', 'top-to-bottom')
            
        Returns:
            排序后的边界框列表
        """
        if direction == 'left-to-right':
            sorted_boxes = sorted(bounding_boxes, key=lambda b: b.x)
        elif direction == 'top-to-bottom':
            sorted_boxes = sorted(bounding_boxes, key=lambda b: b.y)
        else:
            sorted_boxes = bounding_boxes
        
        # 更新order
        for idx, box in enumerate(sorted_boxes, start=1):
            box.order = idx
        
        return sorted_boxes
    
    def extract_regions(
        self,
        image: np.ndarray,
        bounding_boxes: List[BoundingBox],
        add_padding: bool = False,
        padding_size: int = 10
    ) -> List[np.ndarray]:
        """
        提取边界框区域
        
        Args:
            image: 输入图像
            bounding_boxes: 边界框列表
            add_padding: 是否添加边距
            padding_size: 边距大小
            
        Returns:
            提取的图像区域列表
        """
        regions = []
        img_height, img_width = image.shape[:2]
        
        for bbox in bounding_boxes:
            # 计算提取区域
            if add_padding:
                x1 = max(0, bbox.x - padding_size)
                y1 = max(0, bbox.y - padding_size)
                x2 = min(img_width, bbox.x + bbox.width + padding_size)
                y2 = min(img_height, bbox.y + bbox.height + padding_size)
            else:
                x1 = bbox.x
                y1 = bbox.y
                x2 = bbox.x + bbox.width
                y2 = bbox.y + bbox.height
            
            # 提取区域
            region = image[y1:y2, x1:x2].copy()
            regions.append(region)
        
        return regions
    
    async def save_segmented_regions(
        self,
        regions: List[np.ndarray],
        bounding_boxes: List[BoundingBox],
        output_dir: Path,
        output_format: str = 'png',
        prefix: str = 'seg',
        slip_number: Optional[str] = None,
    ) -> List[dict]:
        """
        保存切割后的区域（带持久化备份）

        Args:
            regions: 图像区域列表
            bounding_boxes: 边界框列表
            output_dir: 输出目录
            output_format: 输出格式
            prefix: 文件名前缀
            slip_number: 简牍编号（可选），用于文件命名前缀

        Returns:
            保存结果列表
        """
        log = logging.getLogger(__name__)

        try:
            FileManager.ensure_directory(output_dir)
            results = []

            # 创建备份目录
            backup_dir = Path(settings.result_dir) / "backups" / datetime.now().strftime("%Y%m%d")
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 创建元数据文件
            metadata = {
                "created_at": datetime.now().isoformat(),
                "total_count": len(regions),
                "output_format": output_format,
                "prefix": prefix,
                "regions": []
            }

            for idx, (region, bbox) in enumerate(zip(regions, bounding_boxes), start=1):
                # 生成文件名：优先使用简牍编号作为前缀
                segment_type = "char" if bbox.id.startswith("char_") else "slip"
                if slip_number:
                    filename = f"{slip_number}_{segment_type}_{idx:04d}.{output_format}"
                else:
                    filename = f"{prefix}_{idx:04d}.{output_format}"
                file_path = output_dir / filename

                # 保存图像
                self.image_processor.save_image(region, file_path)

                # 备份到 backups 目录
                backup_path = backup_dir / filename
                try:
                    self.image_processor.save_image(region, backup_path)
                except Exception as e:
                    log.warning("备份保存失败: %s", e)

                # 记录结果
                result = {
                    'id': bbox.id,
                    'order': bbox.order,
                    'filename': filename,
                    'path': str(file_path),
                    'backup_path': str(backup_path),
                    'width': region.shape[1],
                    'height': region.shape[0]
                }
                results.append(result)

                # 添加到元数据
                metadata["regions"].append({
                    "id": bbox.id,
                    "filename": filename,
                    "x": bbox.x,
                    "y": bbox.y,
                    "width": bbox.width,
                    "height": bbox.height,
                    "confidence": bbox.confidence
                })

            # 保存元数据文件
            metadata_path = output_dir / "metadata.json"
            try:
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            except Exception as e:
                log.warning("元数据保存失败: %s", e)

            log.info("切割结果已保存: %d 个文件, 备份目录: %s", len(results), backup_dir)
            return results

        except Exception as e:
            log.exception("保存切割结果失败: %s", e)
            raise SegmentationException(f"保存切割结果失败: {str(e)}")
