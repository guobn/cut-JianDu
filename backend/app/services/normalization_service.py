import cv2
import numpy as np
from typing import Tuple, List, Optional

from app.utils.image_utils import ImageProcessor


class NormalizationService:
    """图像尺寸归一化服务"""
    
    def __init__(self):
        self.image_processor = ImageProcessor()
    
    def normalize_size(
        self,
        image: np.ndarray,
        target_width: int = 800,
        target_height: int = 1200,
        keep_aspect_ratio: bool = True,
        padding_color: str = 'white',
        interpolation: str = 'linear'
    ) -> np.ndarray:
        """
        归一化图像尺寸
        
        Args:
            image: 输入图像
            target_width: 目标宽度
            target_height: 目标高度
            keep_aspect_ratio: 是否保持长宽比
            padding_color: 填充颜色 ('white', 'black', 'gray')
            interpolation: 插值方法
            
        Returns:
            归一化后的图像
        """
        if keep_aspect_ratio:
            # 保持长宽比的缩放
            resized = self._resize_keep_aspect_ratio(
                image,
                target_width,
                target_height,
                interpolation
            )
            
            # 添加边距使其达到目标尺寸
            normalized = self.add_padding(
                resized,
                target_width,
                target_height,
                padding_color
            )
        else:
            # 直接缩放到目标尺寸
            normalized = self.image_processor.resize_image(
                image,
                width=target_width,
                height=target_height,
                keep_aspect_ratio=False,
                interpolation=interpolation
            )
        
        return normalized
    
    def _resize_keep_aspect_ratio(
        self,
        image: np.ndarray,
        target_width: int,
        target_height: int,
        interpolation: str = 'linear'
    ) -> np.ndarray:
        """
        保持长宽比缩放图像
        
        Args:
            image: 输入图像
            target_width: 目标宽度
            target_height: 目标高度
            interpolation: 插值方法
            
        Returns:
            缩放后的图像
        """
        h, w = image.shape[:2]
        
        # 计算缩放比例
        scale_w = target_width / w
        scale_h = target_height / h
        scale = min(scale_w, scale_h)
        
        # 计算新尺寸
        new_width = int(w * scale)
        new_height = int(h * scale)
        
        # 缩放
        resized = self.image_processor.resize_image(
            image,
            width=new_width,
            height=new_height,
            keep_aspect_ratio=False,
            interpolation=interpolation
        )
        
        return resized
    
    def add_padding(
        self,
        image: np.ndarray,
        target_width: int,
        target_height: int,
        padding_color: str = 'white',
        position: str = 'center'
    ) -> np.ndarray:
        """
        添加边距
        
        Args:
            image: 输入图像
            target_width: 目标宽度
            target_height: 目标高度
            padding_color: 填充颜色
            position: 位置 ('center', 'top-left', 'top-center', 'bottom-center')
            
        Returns:
            添加边距后的图像
        """
        h, w = image.shape[:2]
        
        # 如果图像已经大于或等于目标尺寸，直接返回
        if w >= target_width and h >= target_height:
            return image
        
        # 确定填充颜色
        color_map = {
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'gray': (128, 128, 128)
        }
        
        if len(image.shape) == 2:
            # 灰度图
            fill_color = color_map.get(padding_color, (255,))[0]
        else:
            # 彩色图
            fill_color = color_map.get(padding_color, (255, 255, 255))
        
        # 创建目标尺寸的画布
        if len(image.shape) == 2:
            canvas = np.full((target_height, target_width), fill_color, dtype=image.dtype)
        else:
            canvas = np.full((target_height, target_width, image.shape[2]), fill_color, dtype=image.dtype)
        
        # 计算放置位置
        if position == 'center':
            x_offset = (target_width - w) // 2
            y_offset = (target_height - h) // 2
        elif position == 'top-left':
            x_offset = 0
            y_offset = 0
        elif position == 'top-center':
            x_offset = (target_width - w) // 2
            y_offset = 0
        elif position == 'bottom-center':
            x_offset = (target_width - w) // 2
            y_offset = target_height - h
        else:
            x_offset = (target_width - w) // 2
            y_offset = (target_height - h) // 2
        
        # 放置图像
        canvas[y_offset:y_offset+h, x_offset:x_offset+w] = image
        
        return canvas
    
    def batch_normalize(
        self,
        images: List[np.ndarray],
        target_width: int = 800,
        target_height: int = 1200,
        keep_aspect_ratio: bool = True,
        padding_color: str = 'white'
    ) -> List[np.ndarray]:
        """
        批量归一化图像
        
        Args:
            images: 图像列表
            target_width: 目标宽度
            target_height: 目标高度
            keep_aspect_ratio: 是否保持长宽比
            padding_color: 填充颜色
            
        Returns:
            归一化后的图像列表
        """
        normalized_images = []
        
        for image in images:
            normalized = self.normalize_size(
                image,
                target_width,
                target_height,
                keep_aspect_ratio,
                padding_color
            )
            normalized_images.append(normalized)
        
        return normalized_images
    
    def normalize_to_fixed_height(
        self,
        image: np.ndarray,
        target_height: int = 1200,
        padding_color: str = 'white'
    ) -> np.ndarray:
        """
        归一化到固定高度（宽度自适应）
        
        Args:
            image: 输入图像
            target_height: 目标高度
            padding_color: 填充颜色
            
        Returns:
            归一化后的图像
        """
        h, w = image.shape[:2]
        
        # 计算缩放比例
        scale = target_height / h
        new_width = int(w * scale)
        
        # 缩放
        resized = self.image_processor.resize_image(
            image,
            width=new_width,
            height=target_height,
            keep_aspect_ratio=False
        )
        
        return resized
    
    def normalize_to_fixed_width(
        self,
        image: np.ndarray,
        target_width: int = 800,
        padding_color: str = 'white'
    ) -> np.ndarray:
        """
        归一化到固定宽度（高度自适应）
        
        Args:
            image: 输入图像
            target_width: 目标宽度
            padding_color: 填充颜色
            
        Returns:
            归一化后的图像
        """
        h, w = image.shape[:2]
        
        # 计算缩放比例
        scale = target_width / w
        new_height = int(h * scale)
        
        # 缩放
        resized = self.image_processor.resize_image(
            image,
            width=target_width,
            height=new_height,
            keep_aspect_ratio=False
        )
        
        return resized
    
    def crop_to_content(
        self,
        image: np.ndarray,
        threshold: int = 250,
        margin: int = 10
    ) -> np.ndarray:
        """
        裁剪到内容区域
        
        Args:
            image: 输入图像
            threshold: 背景阈值
            margin: 边距
            
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
        
        # 添加边距
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(image.shape[1] - x, w + 2 * margin)
        h = min(image.shape[0] - y, h + 2 * margin)
        
        # 裁剪
        cropped = image[y:y+h, x:x+w]
        
        return cropped
