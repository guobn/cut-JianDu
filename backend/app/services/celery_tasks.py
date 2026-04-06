"""Celery 异步任务定义"""

import time
import uuid
import logging
import cv2
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import requests
from celery import group

from app.worker import celery_app
from app.models.detection import BoundingBox, DetectionParameters, DetectionResult, ModelType
from app.models.rotation import RotationDetectionResult, RotationCorrectionResult
from app.services.segmentation_service import SegmentationService
from app.services.rotation_service import RotationService
from app.services.image_service import ImageService
from app.utils.image_utils import ImageProcessor
from app.utils.file_utils import FileManager
from app.config import settings
from pathlib import Path

log = logging.getLogger(__name__)

# 服务实例（在 worker 进程中复用）
_segmentation_service = None
_rotation_service = None
_image_service = None


def _clean_detection_config(config: dict) -> dict:
    """转换 SegmentConfig 参数为 DetectionParameters 格式"""
    if not config:
        return {}
    # 复制避免修改原字典
    cleaned = {k: v for k, v in config.items()}

    # 转换 model_type 字符串为枚举值
    model_type_str = cleaned.get("model_type", "")
    if model_type_str == "yolov11-finetuned":
        cleaned["model_type"] = ModelType.YOLOV11_FINETUNED
    elif model_type_str in ("yolov8", "auto", "opencv", ""):
        # 'auto' 和 'opencv' 使用默认的 YOLOV8
        cleaned["model_type"] = ModelType.YOLOV8

    return cleaned


def _get_segmentation_service() -> SegmentationService:
    """获取 SegmentationService 单例"""
    global _segmentation_service
    if _segmentation_service is None:
        _segmentation_service = SegmentationService()
    return _segmentation_service


def _get_rotation_service() -> RotationService:
    """获取 RotationService 单例"""
    global _rotation_service
    if _rotation_service is None:
        _rotation_service = RotationService()
    return _rotation_service


def _get_image_service() -> ImageService:
    """获取 ImageService 单例"""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service


# ============================================
# 单图检测任务（保持不变）
# ============================================

@celery_app.task(bind=True, name="detect_single_slips_task")
def detect_single_slips_task(
    self,
    image_data: bytes,
    image_id: str,
    parameters: Optional[dict] = None
) -> dict:
    """异步检测单支简牍"""
    try:
        self.update_state(state="STARTED", meta={"progress": 0.1})
        params = DetectionParameters(**parameters) if parameters else DetectionParameters()
        image = ImageProcessor.load_image_from_bytes(image_data)
        h, w = image.shape[:2]
        log.info("detect_single_slips_task: image_id=%s, 尺寸=%sx%s", image_id, w, h)
        self.update_state(state="STARTED", meta={"progress": 0.2})
        start_time = time.time()
        segmentation_service = _get_segmentation_service()
        self.update_state(state="STARTED", meta={"progress": 0.5})
        bounding_boxes = segmentation_service.detect_single_slips(image, params)
        self.update_state(state="STARTED", meta={"progress": 0.8})
        processing_time = time.time() - start_time
        detection_id = f"det_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        result = DetectionResult(
            detection_id=detection_id,
            image_id=image_id,
            mode="single-slip",
            detections=bounding_boxes,
            parameters=params.model_dump(),
            total_count=len(bounding_boxes),
            processing_time=processing_time,
            created_at=datetime.now(),
        )
        log.info("detect_single_slips_task 完成: total_count=%s", result.total_count)
        return result.model_dump()
    except Exception as e:
        log.exception("detect_single_slips_task 失败")
        raise


@celery_app.task(bind=True, name="detect_single_characters_task")
def detect_single_characters_task(
    self,
    image_data: bytes,
    image_id: str,
    parameters: Optional[dict] = None
) -> dict:
    """异步检测单字符"""
    try:
        self.update_state(state="STARTED", meta={"progress": 0.1})
        params = DetectionParameters(**parameters) if parameters else DetectionParameters()
        image = ImageProcessor.load_image_from_bytes(image_data)
        h, w = image.shape[:2]
        log.info("detect_single_characters_task: image_id=%s, 尺寸=%sx%s", image_id, w, h)
        self.update_state(state="STARTED", meta={"progress": 0.2})
        start_time = time.time()
        segmentation_service = _get_segmentation_service()
        self.update_state(state="STARTED", meta={"progress": 0.5})
        bounding_boxes = segmentation_service.detect_single_characters(image, params)
        self.update_state(state="STARTED", meta={"progress": 0.8})
        processing_time = time.time() - start_time
        detection_id = f"det_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        result = DetectionResult(
            detection_id=detection_id,
            image_id=image_id,
            mode="single-character",
            detections=bounding_boxes,
            parameters=params.model_dump(),
            total_count=len(bounding_boxes),
            processing_time=processing_time,
            created_at=datetime.now(),
        )
        log.info("detect_single_characters_task 完成: total_count=%s", result.total_count)
        return result.model_dump()
    except Exception as e:
        log.exception("detect_single_characters_task 失败")
        raise


@celery_app.task(bind=True, name="detect_rotation_angle_task")
def detect_rotation_angle_task(
    self,
    image_id: str,
    user_id: Optional[str] = None
) -> dict:
    """异步检测图像倾斜角度"""
    try:
        self.update_state(state="STARTED", meta={"progress": 0.1})
        image_service = _get_image_service()
        image = image_service.load_image_with_supabase_fallback(image_id, user_id)
        self.update_state(state="STARTED", meta={"progress": 0.3})
        start_time = time.time()
        rotation_service = _get_rotation_service()
        self.update_state(state="STARTED", meta={"progress": 0.6})
        angle, confidence = rotation_service.detect_rotation_angle(image)
        processing_time = time.time() - start_time
        self.update_state(state="STARTED", meta={"progress": 1.0})
        result = RotationDetectionResult(
            image_id=image_id,
            detected_angle=angle,
            confidence=confidence,
            processing_time=processing_time,
            created_at=datetime.now()
        )
        log.info("detect_rotation_angle_task 完成: angle=%.2f, confidence=%.2f", angle, confidence)
        return result.model_dump()
    except Exception as e:
        log.exception("detect_rotation_angle_task 失败")
        raise


@celery_app.task(bind=True, name="correct_rotation_task")
def correct_rotation_task(
    self,
    image_id: str,
    angle: Optional[float] = None,
    auto_crop: bool = True,
    user_id: Optional[str] = None
) -> dict:
    """异步执行旋转校正"""
    try:
        self.update_state(state="STARTED", meta={"progress": 0.1})
        image_service = _get_image_service()
        image = image_service.load_image_with_supabase_fallback(image_id, user_id)
        image_path = image_service.get_image_path(image_id)
        self.update_state(state="STARTED", meta={"progress": 0.3})
        start_time = time.time()
        rotation_service = _get_rotation_service()
        self.update_state(state="STARTED", meta={"progress": 0.6})
        auto_detect = angle is None
        corrected_image, rotation_angle = rotation_service.correct_rotation(
            image, auto_detect=auto_detect, angle=angle, auto_crop=auto_crop
        )
        self.update_state(state="STARTED", meta={"progress": 0.9})
        correction_id = f"rot_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        output_dir = Path(settings.result_dir) / "rotations"
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = image_path.suffix
        output_filename = f"{correction_id}{ext}"
        output_path = output_dir / output_filename
        ImageProcessor.save_image(corrected_image, output_path)
        processing_time = time.time() - start_time
        height, width = corrected_image.shape[:2]
        self.update_state(state="STARTED", meta={"progress": 1.0})
        result = RotationCorrectionResult(
            correction_id=correction_id,
            image_id=image_id,
            original_angle=rotation_angle,
            corrected_angle=0.0,
            output_path=str(output_path),
            width=width,
            height=height,
            processing_time=processing_time,
            created_at=datetime.now()
        )
        log.info("correct_rotation_task 完成: correction_id=%s", correction_id)
        return result.model_dump()
    except Exception as e:
        log.exception("correct_rotation_task 失败")
        raise


# ============================================
# 辅助函数（Supabase 操作）
# ============================================

def _get_session() -> requests.Session:
    """获取配置了重试的 requests session"""
    import os
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    ssl_verify = os.getenv("SSL_VERIFY", "true").lower() != "false"
    session.verify = ssl_verify
    return session


def _get_source_images_from_supabase(group_id: str) -> List[dict]:
    """从 Supabase 获取组内所有源图像"""
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    url = f"{base_url}/rest/v1/source_images"
    params = {"group_id": f"eq.{group_id}"}
    resp = _get_session().get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        log.error("获取源图像失败: %s %s", resp.status_code, resp.text[:200])
        return []
    return resp.json() or []


def _get_validated_slips(source_image_id: str) -> List[dict]:
    """获取某原图的所有已验证 slip segments"""
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    url = f"{base_url}/rest/v1/segments"
    params = {
        "source_image_id": f"eq.{source_image_id}",
        "segment_type": "eq.slip",
        "validated": "eq.true",
        "order": "segment_index.asc"
    }
    resp = _get_session().get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        return []
    return resp.json() or []


def _delete_old_segments(source_image_id: str, segment_type: str) -> None:
    """删除某图像的旧 segments（重新检测前清空）"""
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    url = f"{base_url}/rest/v1/segments"
    params = {
        "source_image_id": f"eq.{source_image_id}",
        "segment_type": f"eq.{segment_type}"
    }
    _get_session().delete(url, headers=headers, params=params)


def _delete_old_char_segments_for_slip(slip_id: str) -> None:
    """删除某 slip 下的旧 char segments"""
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    url = f"{base_url}/rest/v1/segments"
    params = {"parent_segment_id": f"eq.{slip_id}", "segment_type": "eq.char"}
    _get_session().delete(url, headers=headers, params=params)


def _update_group_status(group_id: str, new_status: str) -> None:
    """更新图像组状态"""
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    _get_session().patch(
        f"{base_url}/rest/v1/image_groups",
        headers=headers,
        params={"id": f"eq.{group_id}"},
        json={"status": new_status}
    )


def _increment_group_processed(group_id: str) -> None:
    """
    递增 image_groups.processed_images。
    Supabase REST API 不支持原子 increment，
    改用先 SELECT 当前值再 PATCH 新值（在任务串行场景下安全）。
    """
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    # 读当前值
    resp = _get_session().get(
        f"{base_url}/rest/v1/image_groups",
        headers=headers,
        params={"id": f"eq.{group_id}", "select": "processed_images"}
    )
    if resp.status_code >= 400:
        return
    rows = resp.json() or []
    current = rows[0].get("processed_images", 0) if rows else 0
    # 写新值
    _get_session().patch(
        f"{base_url}/rest/v1/image_groups",
        headers=headers,
        params={"id": f"eq.{group_id}"},
        json={"processed_images": current + 1}
    )


def _write_segment_to_supabase(segment_data: dict) -> Optional[dict]:
    """将片段结果写入 Supabase segments 表（接受完整字段 dict）"""
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    url = f"{base_url}/rest/v1/segments"
    # 过滤掉 None 值（避免不必要的 null 写入）
    clean_data = {k: v for k, v in segment_data.items() if v is not None}
    resp = _get_session().post(url, headers=headers, json=clean_data)
    if resp.status_code >= 400:
        log.error("写入片段失败: %s %s", resp.status_code, resp.text[:200])
        return None
    rows = resp.json()
    return rows[0] if rows else None


def _crop_and_save_segment(
    image: np.ndarray,
    bbox: BoundingBox,
    group_id: str,
    source_image_id: str,
    segment_type: str,
    segment_index: int,
    parent_id: Optional[str] = None
) -> Optional[Path]:
    """
    裁剪并保存 segment 图像到本地。
    保存路径：./results/{group_id}/{segment_type}/{source_image_id}_{segment_index}.jpg
    返回本地路径 Path 对象，失败返回 None。
    """
    try:
        x, y, w, h = int(bbox.x), int(bbox.y), int(bbox.width), int(bbox.height)
        img_h, img_w = image.shape[:2]
        # 边界裁剪保护
        x = max(0, x)
        y = max(0, y)
        w = min(w, img_w - x)
        h = min(h, img_h - y)
        if w <= 0 or h <= 0:
            return None
        cropped = image[y:y+h, x:x+w]

        save_dir = Path(settings.result_dir) / group_id / segment_type
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{source_image_id}_{segment_index}.jpg"
        save_path = save_dir / filename
        cv2.imwrite(str(save_path), cropped)
        return save_path
    except Exception as e:
        log.warning("裁剪保存失败: %s", e)
        return None


# ============================================
# 批量切割任务（串行处理）
# ============================================

@celery_app.task(bind=True, name="batch_segment_slips_task")
def batch_segment_slips_task(self, group_id: str, config: dict) -> dict:
    """
    批量检测单支简牍任务（串行处理，本地文件直接读写）

    流程：
    1. 从 Supabase 获取组内所有 source_images 记录
    2. 逐张读取本地文件 → 运行单支检测
    3. 将检测到的 bbox 写入 Supabase segments 表（segment_type='slip'）
    4. 同步更新 group 的 processed_images 计数和 status
    """
    self.update_state(state="STARTED", meta={"progress": 0.0, "total": 0, "completed": 0, "failed": 0})

    # 1. 获取组内所有源图像
    source_images = _get_source_images_from_supabase(group_id)
    total = len(source_images)
    if total == 0:
        _update_group_status(group_id, "completed")
        return {"total": 0, "completed": 0, "failed": 0, "errors": ["组内无图像"]}

    log.info("batch_segment_slips_task: group_id=%s, total=%s", group_id, total)

    # 初始化检测服务
    seg_service = _get_segmentation_service()
    # 过滤掉无效的 model_type（如 'auto'），使用默认的 YOLOV8
    clean_config = _clean_detection_config(config)
    params = DetectionParameters(**clean_config) if clean_config else DetectionParameters()

    completed = 0
    failed = 0
    errors = []

    for i, img in enumerate(source_images):
        image_id = img["id"]
        storage_path = img.get("storage_path", "")
        filename = img.get("filename", "")

        # 更新进度
        self.update_state(state="PROGRESS", meta={
            "progress": i / total,
            "total": total,
            "completed": completed,
            "failed": failed,
            "current_file": filename
        })

        try:
            # 2. 从本地加载图像（优先用 storage_path，其次用 group_id/filename 拼路径）
            if storage_path and Path(storage_path).exists():
                image_path = Path(storage_path)
            else:
                image_path = Path(settings.upload_dir) / group_id / filename

            if not image_path.exists():
                raise FileNotFoundError(f"图像文件不存在: {image_path}")

            image = ImageProcessor.load_image(image_path)

            # 3. 检测单支简牍
            bounding_boxes: List[BoundingBox] = seg_service.detect_single_slips(image, params)

            # 4. 删除该图旧的 slip segments（重新检测时清理）
            _delete_old_segments(image_id, "slip")

            # 5. 将检测结果写入 Supabase segments 表
            for idx, bbox in enumerate(bounding_boxes):
                # 同时裁剪并保存本地 slip 图像文件
                slip_local_path = _crop_and_save_segment(
                    image=image,
                    bbox=bbox,
                    group_id=group_id,
                    source_image_id=image_id,
                    segment_type="slip",
                    segment_index=idx
                )
                segment_data = {
                    "source_image_id": image_id,
                    "segment_type": "slip",
                    "segment_index": idx,
                    "bbox_x": float(bbox.x),
                    "bbox_y": float(bbox.y),
                    "bbox_width": float(bbox.width),
                    "bbox_height": float(bbox.height),
                    "confidence": float(bbox.confidence) if hasattr(bbox, "confidence") and bbox.confidence else None,
                    "storage_path": str(slip_local_path) if slip_local_path else None,
                    "validated": False,
                }
                _write_segment_to_supabase(segment_data)

            # 6. 更新已处理计数
            _increment_group_processed(group_id)
            completed += 1
            log.info("slip检测完成: image_id=%s, 检测到 %s 支", image_id, len(bounding_boxes))

        except Exception as e:
            failed += 1
            errors.append(f"{filename}: {str(e)}")
            log.exception("slip检测失败: image_id=%s", image_id)

    # 7. 更新组状态
    _update_group_status(group_id, "completed" if failed == 0 else "segmenting")

    result = {"total": total, "completed": completed, "failed": failed, "errors": errors}
    log.info("batch_segment_slips_task 完成: %s", result)
    return result


@celery_app.task(bind=True, name="batch_segment_chars_task")
def batch_segment_chars_task(self, group_id: str, config: dict) -> dict:
    """
    批量检测单字符任务

    流程：
    1. 从 Supabase 获取组内所有 source_images
    2. 对每张原图，获取其 validated slip segments
    3. 对每个 slip，读取本地裁剪图（或实时裁剪）→ 运行字符检测
    4. 将字符 bbox 写入 segments 表（segment_type='char', parent_segment_id=slip.id）
       字符坐标相对于原图坐标系（slip_bbox.x + char.x）
    """
    self.update_state(state="STARTED", meta={"progress": 0.0, "total": 0, "completed": 0, "failed": 0})

    source_images = _get_source_images_from_supabase(group_id)
    if not source_images:
        return {"total": 0, "completed": 0, "failed": 0, "errors": ["组内无图像"]}

    # 统计总 slip 数（进度的分母）
    all_slip_ids = []
    for img in source_images:
        slips = _get_validated_slips(img["id"])
        all_slip_ids.extend([(img, slip) for slip in slips])

    total = len(all_slip_ids)
    if total == 0:
        return {"total": 0, "completed": 0, "failed": 0, "errors": ["无已验证的单支，请先完成单支校验"]}

    seg_service = _get_segmentation_service()
    clean_config = _clean_detection_config(config)
    params = DetectionParameters(**clean_config) if clean_config else DetectionParameters(
        min_width=20, min_height=20, max_width=150, max_height=150,
        aspect_ratio_min=0.3, aspect_ratio_max=3.0
    )

    completed = 0
    failed = 0
    errors = []

    for i, (img, slip) in enumerate(all_slip_ids):
        image_id = img["id"]
        slip_id = slip["id"]
        filename = img.get("filename", "")

        self.update_state(state="PROGRESS", meta={
            "progress": i / total,
            "total": total,
            "completed": completed,
            "failed": failed,
            "current_file": f"{filename} / slip {slip['segment_index']}"
        })

        try:
            # 加载 slip 裁剪图（优先用已保存的 storage_path，否则实时裁剪）
            slip_storage = slip.get("storage_path")
            if slip_storage and Path(slip_storage).exists():
                slip_image = ImageProcessor.load_image(Path(slip_storage))
            else:
                # 实时从原图裁剪
                source_path = img.get("storage_path") or (Path(settings.upload_dir) / group_id / filename)
                source_image = ImageProcessor.load_image(Path(source_path))
                bx = int(slip["bbox_x"])
                by = int(slip["bbox_y"])
                bw = int(slip["bbox_width"])
                bh = int(slip["bbox_height"])
                slip_image = source_image[by:by+bh, bx:bx+bw]

            # 字符检测（在 slip 坐标系下）
            char_boxes: List[BoundingBox] = seg_service.detect_single_characters(slip_image, params)

            # 删除旧的 char segments（属于该 slip 的）
            _delete_old_char_segments_for_slip(slip_id)

            # slip 原点在原图中的偏移
            slip_origin_x = int(slip["bbox_x"])
            slip_origin_y = int(slip["bbox_y"])

            for idx, bbox in enumerate(char_boxes):
                # 字符坐标转换回原图坐标系
                abs_x = slip_origin_x + int(bbox.x)
                abs_y = slip_origin_y + int(bbox.y)

                # 裁剪字符图并保存本地
                char_local_path = _crop_and_save_segment(
                    image=slip_image,
                    bbox=bbox,
                    group_id=group_id,
                    source_image_id=image_id,
                    segment_type="char",
                    segment_index=idx,
                    parent_id=slip_id
                )

                segment_data = {
                    "source_image_id": image_id,
                    "segment_type": "char",
                    "segment_index": idx,
                    "parent_segment_id": slip_id,
                    "bbox_x": float(abs_x),
                    "bbox_y": float(abs_y),
                    "bbox_width": float(bbox.width),
                    "bbox_height": float(bbox.height),
                    "confidence": float(bbox.confidence) if hasattr(bbox, "confidence") and bbox.confidence else None,
                    "storage_path": str(char_local_path) if char_local_path else None,
                    "validated": False,
                }
                _write_segment_to_supabase(segment_data)

            completed += 1

        except Exception as e:
            failed += 1
            errors.append(f"{filename}/slip-{slip.get('segment_index', '?')}: {str(e)}")
            log.exception("char检测失败: slip_id=%s", slip_id)

    _update_group_status(group_id, "completed" if failed == 0 else "segmenting")
    result = {"total": total, "completed": completed, "failed": failed, "errors": errors}
    log.info("batch_segment_chars_task 完成: %s", result)
    return result
