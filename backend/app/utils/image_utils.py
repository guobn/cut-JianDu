import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple, Optional, Union
from pathlib import Path


class ImageProcessor:
    """图像处理工具类"""
    
    @staticmethod
    def load_image(file_path: Union[str, Path]) -> np.ndarray:
        """
        加载图像文件
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            numpy数组格式的图像
        """
        # 使用cv2.imdecode处理中文路径问题
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError(f"无法加载图像: {file_path}")
        
        return image
    
    @staticmethod
    def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
        """
        从字节数据加载图像
        
        Args:
            image_bytes: 图像字节数据
            
        Returns:
            numpy数组格式的图像
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("无法从字节数据加载图像")
        
        return image
    
    @staticmethod
    def save_image(image: np.ndarray, output_path: Union[str, Path], quality: int = 95) -> str:
        """
        保存图像文件
        
        Args:
            image: numpy数组格式的图像
            output_path: 输出路径
            quality: 图像质量 (1-100)
            
        Returns:
            保存的文件路径
        """
        if isinstance(output_path, str):
            output_path = Path(output_path)
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 根据文件扩展名设置编码参数
        ext = output_path.suffix.lower()
        if ext in ['.jpg', '.jpeg']:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        elif ext == '.png':
            encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 9 - (quality // 10)]
        else:
            encode_param = []
        
        # 编码并保存
        success, encoded_image = cv2.imencode(ext, image, encode_param)
        if not success:
            raise ValueError(f"无法编码图像: {output_path}")
        
        with open(output_path, 'wb') as f:
            f.write(encoded_image.tobytes())
        
        return str(output_path)
    
    @staticmethod
    def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
        """
        转换为灰度图像
        
        Args:
            image: 输入图像
            
        Returns:
            灰度图像
        """
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    @staticmethod
    def apply_binary_threshold(
        image: np.ndarray,
        method: str = 'otsu',
        threshold_value: int = 127,
        adaptive_block_size: int = 11,
        adaptive_c: int = 2
    ) -> np.ndarray:
        """
        应用二值化阈值
        
        Args:
            image: 输入图像（灰度图）
            method: 二值化方法 ('otsu', 'adaptive', 'simple')
            threshold_value: 阈值（用于simple方法）
            adaptive_block_size: 自适应阈值的块大小
            adaptive_c: 自适应阈值的常数
            
        Returns:
            二值化图像
        """
        if len(image.shape) == 3:
            image = ImageProcessor.convert_to_grayscale(image)
        
        if method == 'otsu':
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == 'adaptive':
            binary = cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, adaptive_block_size, adaptive_c
            )
        elif method == 'simple':
            _, binary = cv2.threshold(image, threshold_value, 255, cv2.THRESH_BINARY)
        else:
            raise ValueError(f"不支持的二值化方法: {method}")
        
        return binary
    
    @staticmethod
    def denoise_image(image: np.ndarray, method: str = 'gaussian', kernel_size: int = 5) -> np.ndarray:
        """
        图像降噪
        
        Args:
            image: 输入图像
            method: 降噪方法 ('gaussian', 'median', 'bilateral')
            kernel_size: 核大小
            
        Returns:
            降噪后的图像
        """
        if method == 'gaussian':
            return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        elif method == 'median':
            return cv2.medianBlur(image, kernel_size)
        elif method == 'bilateral':
            return cv2.bilateralFilter(image, kernel_size, 75, 75)
        else:
            raise ValueError(f"不支持的降噪方法: {method}")
    
    @staticmethod
    def detect_edges(
        image: np.ndarray,
        method: str = 'canny',
        low_threshold: int = 50,
        high_threshold: int = 150
    ) -> np.ndarray:
        """
        边缘检测
        
        Args:
            image: 输入图像（灰度图）
            method: 边缘检测方法 ('canny', 'sobel')
            low_threshold: Canny低阈值
            high_threshold: Canny高阈值
            
        Returns:
            边缘图像
        """
        if len(image.shape) == 3:
            image = ImageProcessor.convert_to_grayscale(image)
        
        if method == 'canny':
            edges = cv2.Canny(image, low_threshold, high_threshold)
        elif method == 'sobel':
            sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.sqrt(sobelx**2 + sobely**2).astype(np.uint8)
        else:
            raise ValueError(f"不支持的边缘检测方法: {method}")
        
        return edges
    
    @staticmethod
    def resize_image(
        image: np.ndarray,
        width: Optional[int] = None,
        height: Optional[int] = None,
        keep_aspect_ratio: bool = True,
        interpolation: str = 'linear'
    ) -> np.ndarray:
        """
        调整图像大小
        
        Args:
            image: 输入图像
            width: 目标宽度
            height: 目标高度
            keep_aspect_ratio: 是否保持长宽比
            interpolation: 插值方法 ('linear', 'cubic', 'nearest')
            
        Returns:
            调整大小后的图像
        """
        h, w = image.shape[:2]
        
        # 选择插值方法
        interp_methods = {
            'linear': cv2.INTER_LINEAR,
            'cubic': cv2.INTER_CUBIC,
            'nearest': cv2.INTER_NEAREST,
            'area': cv2.INTER_AREA
        }
        interp = interp_methods.get(interpolation, cv2.INTER_LINEAR)
        
        if width is None and height is None:
            return image
        
        if keep_aspect_ratio:
            if width is not None and height is None:
                ratio = width / w
                height = int(h * ratio)
            elif height is not None and width is None:
                ratio = height / h
                width = int(w * ratio)
            else:
                # 两者都指定时，选择较小的缩放比例
                ratio = min(width / w, height / h)
                width = int(w * ratio)
                height = int(h * ratio)
        else:
            if width is None:
                width = w
            if height is None:
                height = h
        
        return cv2.resize(image, (width, height), interpolation=interp)
    
    @staticmethod
    def get_image_info(image: np.ndarray) -> dict:
        """
        获取图像信息
        
        Args:
            image: 输入图像
            
        Returns:
            图像信息字典
        """
        height, width = image.shape[:2]
        channels = 1 if len(image.shape) == 2 else image.shape[2]
        
        return {
            'width': width,
            'height': height,
            'channels': channels,
            'dtype': str(image.dtype),
            'shape': image.shape
        }
    
    @staticmethod
    def image_to_bytes(image: np.ndarray, format: str = 'png', quality: int = 95) -> bytes:
        """
        将图像转换为字节数据
        
        Args:
            image: 输入图像
            format: 输出格式 ('png', 'jpg')
            quality: 图像质量
            
        Returns:
            图像字节数据
        """
        ext = f'.{format.lower()}'
        if ext in ['.jpg', '.jpeg']:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        elif ext == '.png':
            encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 9 - (quality // 10)]
        else:
            encode_param = []
        
        success, encoded_image = cv2.imencode(ext, image, encode_param)
        if not success:
            raise ValueError(f"无法编码图像为 {format} 格式")
        
        return encoded_image.tobytes()
    
    @staticmethod
    def preprocess_for_detection(
        image: np.ndarray,
        denoise: bool = True,
        enhance_contrast: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        检测前的预处理
        
        Args:
            image: 输入图像
            denoise: 是否降噪
            enhance_contrast: 是否增强对比度
            
        Returns:
            (灰度图, 二值图)
        """
        # 转换为灰度图
        gray = ImageProcessor.convert_to_grayscale(image)
        
        # 降噪
        if denoise:
            gray = ImageProcessor.denoise_image(gray, method='gaussian', kernel_size=5)
        
        # 增强对比度
        if enhance_contrast:
            gray = cv2.equalizeHist(gray)
        
        # 二值化
        binary = ImageProcessor.apply_binary_threshold(gray, method='otsu')

        return gray, binary

    @staticmethod
    def enhance_image(
        image: np.ndarray,
        grayscale: bool = False,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: Tuple[int, int] = (8, 8),
        denoise_method: str = 'fastNlMeans',
        denoise_strength: int = 10,
        return_bgr: bool = True
    ) -> np.ndarray:
        """
        图像增强预处理流水线

        包含：灰度化（可选）、CLAHE 局部对比度增强、自动去噪

        Args:
            image: 输入图像 (BGR 格式的 numpy array)
            grayscale: 是否转为灰度图（模型通常需要彩色输入，默认 False）
            clahe_clip_limit: CLAHE 对比度限制（默认 2.0，值越大对比度增强越明显）
            clahe_grid_size: CLAHE 网格大小（默认 8x8）
            denoise_method: 去噪方法 ('fastNlMeans', 'gaussian', 'median', 'bilateral', 'none')
            denoise_strength: 去噪强度（fastNlMeans 的 h 参数，或滤波器核大小）
            return_bgr: 是否返回 BGR 格式（确保与模型输入兼容，默认 True）

        Returns:
            增强后的图像 (numpy array，格式与模型输入兼容)
        """
        original_is_color = len(image.shape) == 3 and image.shape[2] == 3

        # 1. 灰度化（可选）
        if grayscale:
            if original_is_color:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image if len(image.shape) == 2 else image[:, :, 0]
            enhanced = gray
        else:
            # 保持彩色，但分别处理亮度通道
            if original_is_color:
                # 转换到 LAB 色彩空间，只对 L 通道做 CLAHE
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                l_channel, a_channel, b_channel = cv2.split(lab)

                # 2. CLAHE 局部对比度增强（对 L 通道）
                clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=clahe_grid_size)
                l_enhanced = clahe.apply(l_channel)

                # 3. 自动去噪（对 L 通道）
                if denoise_method != 'none':
                    l_enhanced = ImageProcessor._apply_denoise(l_enhanced, denoise_method, denoise_strength)

                # 合并通道并转回 BGR
                lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
                enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
            else:
                # 输入已经是灰度图
                enhanced = image

                # 2. CLAHE 局部对比度增强
                clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=clahe_grid_size)
                enhanced = clahe.apply(enhanced)

                # 3. 自动去噪
                if denoise_method != 'none':
                    enhanced = ImageProcessor._apply_denoise(enhanced, denoise_method, denoise_strength)

                # 如果需要返回 BGR 格式
                if return_bgr:
                    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

        return enhanced

    @staticmethod
    def _apply_denoise(
        image: np.ndarray,
        method: str,
        strength: int
    ) -> np.ndarray:
        """
        内部方法：应用去噪处理

        Args:
            image: 输入图像（灰度图）
            method: 去噪方法
            strength: 去噪强度

        Returns:
            去噪后的图像
        """
        if method == 'fastNlMeans':
            # 非局部均值去噪，效果最好但较慢
            # strength 是 h 参数，值越大去噪越强但细节损失越多
            return cv2.fastNlMeansDenoising(image, None, h=strength)
        elif method == 'gaussian':
            # 高斯滤波，快速但可能模糊边缘
            kernel_size = max(3, strength // 2 * 2 + 1)  # 确保是奇数
            return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        elif method == 'median':
            # 中值滤波，对椒盐噪声效果好
            kernel_size = max(3, strength // 2 * 2 + 1)
            return cv2.medianBlur(image, kernel_size)
        elif method == 'bilateral':
            # 双边滤波，保边去噪
            return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        else:
            return image

    @staticmethod
    def enhance_for_detection(
        image: np.ndarray,
        detection_type: str = 'slip'
    ) -> np.ndarray:
        """
        针对检测任务的图像增强预设

        Args:
            image: 输入图像
            detection_type: 检测类型 ('slip' 单支检测, 'character' 单字检测, 'rotation' 旋转检测)

        Returns:
            增强后的图像（BGR 格式，与模型输入兼容）
        """
        if detection_type == 'slip':
            # 单支简牍检测：中等对比度增强，轻度去噪
            return ImageProcessor.enhance_image(
                image,
                grayscale=False,
                clahe_clip_limit=2.0,
                clahe_grid_size=(8, 8),
                denoise_method='fastNlMeans',
                denoise_strength=8,
                return_bgr=True
            )
        elif detection_type == 'character':
            # 单字检测：较强对比度增强，保持细节
            return ImageProcessor.enhance_image(
                image,
                grayscale=False,
                clahe_clip_limit=3.0,
                clahe_grid_size=(8, 8),
                denoise_method='fastNlMeans',
                denoise_strength=6,
                return_bgr=True
            )
        elif detection_type == 'rotation':
            # 旋转检测：轻度增强，保留边缘信息
            return ImageProcessor.enhance_image(
                image,
                grayscale=False,
                clahe_clip_limit=1.5,
                clahe_grid_size=(8, 8),
                denoise_method='gaussian',
                denoise_strength=5,
                return_bgr=True
            )
        else:
            # 默认增强
            return ImageProcessor.enhance_image(image)
