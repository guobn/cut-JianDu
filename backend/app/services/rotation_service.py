import cv2
import numpy as np
from typing import Tuple, Optional
from pathlib import Path
import logging

from app.utils.image_utils import ImageProcessor
from app.services.exceptions import RotationException, ServiceException


class RotationService:
    """图像旋转校正服务"""

    def __init__(self):
        self.image_processor = ImageProcessor()

    def detect_rotation_angle(
        self,
        image: np.ndarray,
        angle_threshold: float = 45.0,
        line_threshold: int = 100
    ) -> Tuple[float, float]:
        """
        检测图像倾斜角度

        Args:
            image: 输入图像
            angle_threshold: 角度阈值（度）
            line_threshold: 霍夫直线检测阈值

        Returns:
            (检测到的角度, 置信度)
        """
        log = logging.getLogger(__name__)

        try:
            # 图像增强预处理
            enhanced_image = ImageProcessor.enhance_for_detection(image, detection_type='rotation')

            # 预处理
            gray = self.image_processor.convert_to_grayscale(enhanced_image)
            edges = self.image_processor.detect_edges(gray, method='canny')

            # 霍夫直线检测
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=line_threshold,
                minLineLength=50,
                maxLineGap=10
            )

            if lines is None or len(lines) == 0:
                return 0.0, 0.0

            # 计算每条直线的角度
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # 计算角度（相对于水平线）
                if x2 - x1 == 0:
                    angle = 90.0
                else:
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))

                # 归一化到 [-90, 90]
                if angle > 90:
                    angle -= 180
                elif angle < -90:
                    angle += 180

                # 只考虑接近垂直或水平的线
                if abs(angle) < angle_threshold or abs(angle - 90) < angle_threshold:
                    angles.append(angle)

            if not angles:
                return 0.0, 0.0

            # 统计分析，找出主要角度
            angles = np.array(angles)

            # 使用中位数作为主要角度（对异常值更鲁棒）
            median_angle = np.median(angles)

            # 计算置信度（基于角度的一致性）
            std_dev = np.std(angles)
            confidence = max(0.0, min(1.0, 1.0 - (std_dev / 45.0)))

            return float(median_angle), float(confidence)

        except ServiceException:
            raise
        except Exception as e:
            log.exception("角度检测失败: %s", e)
            raise RotationException(f"角度检测失败: {str(e)}")
    
    def rotate_image(
        self,
        image: np.ndarray,
        angle: float,
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """
        旋转图像
        
        Args:
            image: 输入图像
            angle: 旋转角度（度，逆时针为正）
            background_color: 背景填充颜色
            
        Returns:
            旋转后的图像
        """
        if abs(angle) < 0.1:
            return image
        
        # 获取图像尺寸
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # 计算旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 计算旋转后的边界框大小
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))
        
        # 调整旋转矩阵以适应新的图像大小
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]
        
        # 执行旋转
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (new_width, new_height),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=background_color
        )
        
        return rotated
    
    def auto_crop_borders(
        self,
        image: np.ndarray,
        threshold: int = 250
    ) -> np.ndarray:
        """
        自动裁剪图像边缘的空白区域
        
        Args:
            image: 输入图像
            threshold: 背景阈值（用于检测空白区域）
            
        Returns:
            裁剪后的图像
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 二值化
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
        
        # 查找非零区域
        coords = cv2.findNonZero(binary)
        
        if coords is None:
            return image
        
        # 获取边界框
        x, y, w, h = cv2.boundingRect(coords)
        
        # 添加小边距
        margin = 10
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(image.shape[1] - x, w + 2 * margin)
        h = min(image.shape[0] - y, h + 2 * margin)
        
        # 裁剪
        cropped = image[y:y+h, x:x+w]
        
        return cropped
    
    def correct_rotation(
        self,
        image: np.ndarray,
        auto_detect: bool = True,
        angle: Optional[float] = None,
        auto_crop: bool = True
    ) -> Tuple[np.ndarray, float]:
        """
        执行旋转校正

        Args:
            image: 输入图像
            auto_detect: 是否自动检测角度
            angle: 指定的旋转角度（如果不自动检测）
            auto_crop: 是否自动裁剪黑边

        Returns:
            (校正后的图像, 实际旋转角度)
        """
        log = logging.getLogger(__name__)

        try:
            # 检测或使用指定角度
            if auto_detect:
                detected_angle, confidence = self.detect_rotation_angle(image)
                rotation_angle = detected_angle
            else:
                if angle is None:
                    return image, 0.0
                rotation_angle = angle

            # 如果角度很小，不需要旋转
            if abs(rotation_angle) < 0.5:
                return image, 0.0

            # 旋转图像
            rotated = self.rotate_image(image, -rotation_angle)  # 负号是为了校正

            # 自动裁剪
            if auto_crop:
                rotated = self.auto_crop_borders(rotated)

            return rotated, rotation_angle

        except ServiceException:
            raise
        except Exception as e:
            log.exception("旋转校正失败: %s", e)
            raise RotationException(f"旋转校正失败: {str(e)}")
    
    def rotate_with_bounding_boxes(
        self,
        image: np.ndarray,
        angle: float,
        bounding_boxes: list
    ) -> Tuple[np.ndarray, list]:
        """
        旋转图像并更新边界框坐标
        
        Args:
            image: 输入图像
            angle: 旋转角度
            bounding_boxes: 边界框列表
            
        Returns:
            (旋转后的图像, 更新后的边界框列表)
        """
        # 旋转图像
        rotated = self.rotate_image(image, angle)
        
        # 计算旋转矩阵
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 更新边界框坐标
        updated_boxes = []
        for bbox in bounding_boxes:
            # 获取边界框的四个角点
            corners = np.array([
                [bbox.x, bbox.y],
                [bbox.x + bbox.width, bbox.y],
                [bbox.x + bbox.width, bbox.y + bbox.height],
                [bbox.x, bbox.y + bbox.height]
            ], dtype=np.float32)
            
            # 应用旋转变换
            ones = np.ones(shape=(len(corners), 1))
            corners_homogeneous = np.hstack([corners, ones])
            transformed_corners = rotation_matrix.dot(corners_homogeneous.T).T
            
            # 计算新的边界框
            x_coords = transformed_corners[:, 0]
            y_coords = transformed_corners[:, 1]
            
            new_x = int(np.min(x_coords))
            new_y = int(np.min(y_coords))
            new_width = int(np.max(x_coords) - new_x)
            new_height = int(np.max(y_coords) - new_y)
            
            # 更新边界框
            bbox.x = new_x
            bbox.y = new_y
            bbox.width = new_width
            bbox.height = new_height
            bbox.rotation = angle
            
            updated_boxes.append(bbox)
        
        return rotated, updated_boxes


def estimate_skew_angle(image_path: str) -> Tuple[float, float]:
    image = ImageProcessor.load_image(image_path)
    enhanced = ImageProcessor.enhance_for_detection(image, detection_type='rotation')
    gray = ImageProcessor.convert_to_grayscale(enhanced)
    edges = cv2.Canny(gray, 50, 150)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=max(40, min(gray.shape[:2]) // 4),
        maxLineGap=12,
    )

    if lines is None or len(lines) == 0:
        return 0.0, 0.0

    weighted_angles = []
    weights = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            continue
        angle = float(np.degrees(np.arctan2(dy, dx)))
        while angle <= -90:
            angle += 180
        while angle > 90:
            angle -= 180
        if abs(angle) >= 60:
            continue
        length = float(np.hypot(dx, dy))
        if length <= 0:
            continue
        weighted_angles.append(angle)
        weights.append(length)

    if not weighted_angles:
        return 0.0, 0.0

    angles = np.array(weighted_angles, dtype=np.float32)
    weights_array = np.array(weights, dtype=np.float32)
    order = np.argsort(angles)
    sorted_angles = angles[order]
    sorted_weights = weights_array[order]
    cumulative = np.cumsum(sorted_weights)
    midpoint = sorted_weights.sum() / 2.0
    median_index = int(np.searchsorted(cumulative, midpoint))
    median_angle = float(sorted_angles[min(median_index, len(sorted_angles) - 1)])

    std_dev = float(np.sqrt(np.average((angles - median_angle) ** 2, weights=weights_array)))
    confidence = float(np.clip(1.0 - (std_dev / 15.0), 0.0, 1.0))
    return median_angle, confidence
