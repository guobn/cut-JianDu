"""统一异常处理模块"""

from typing import Optional, Any
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 图像相关错误
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    INVALID_IMAGE_DATA = "INVALID_IMAGE_DATA"
    IMAGE_LOAD_FAILED = "IMAGE_LOAD_FAILED"

    # 检测相关错误
    DETECTION_FAILED = "DETECTION_FAILED"
    INVALID_MODE = "INVALID_MODE"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    MODEL_INFERENCE_FAILED = "MODEL_INFERENCE_FAILED"

    # 切割相关错误
    SEGMENTATION_FAILED = "SEGMENTATION_FAILED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    SAVE_FAILED = "SAVE_FAILED"

    # 旋转相关错误
    ROTATION_DETECTION_FAILED = "ROTATION_DETECTION_FAILED"
    ROTATION_CORRECTION_FAILED = "ROTATION_CORRECTION_FAILED"

    # 存储相关错误
    STORAGE_ERROR = "STORAGE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"

    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class ServiceException(Exception):
    """服务层异常基类"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        suggested_solution: Optional[str] = None,
        details: Optional[Any] = None
    ):
        self.error_code = error_code
        self.message = message
        self.suggested_solution = suggested_solution or "请稍后重试或联系管理员"
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {
            "status": "error",
            "error_code": self.error_code.value,
            "error_message": self.message,
            "suggested_solution": self.suggested_solution
        }
        if self.details:
            result["details"] = self.details
        return result


class ImageNotFoundException(ServiceException):
    """图像未找到异常"""
    def __init__(self, image_id: str, details: Optional[Any] = None):
        super().__init__(
            error_code=ErrorCode.IMAGE_NOT_FOUND,
            message=f"图像不存在: {image_id}",
            suggested_solution="请检查图像ID是否正确",
            details=details
        )


class InvalidImageDataException(ServiceException):
    """无效图像数据异常"""
    def __init__(self, message: str = "无效的图像数据", details: Optional[Any] = None):
        super().__init__(
            error_code=ErrorCode.INVALID_IMAGE_DATA,
            message=message,
            suggested_solution="请上传有效的图像文件",
            details=details
        )


class ModelInferenceException(ServiceException):
    """模型推理异常"""
    def __init__(self, model_name: str, error: str, details: Optional[Any] = None):
        super().__init__(
            error_code=ErrorCode.MODEL_INFERENCE_FAILED,
            message=f"模型 {model_name} 推理失败: {error}",
            suggested_solution="请检查图像质量或稍后重试",
            details=details
        )


class DetectionException(ServiceException):
    """检测异常"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            error_code=ErrorCode.DETECTION_FAILED,
            message=message,
            suggested_solution="请检查图像质量和参数设置",
            details=details
        )


class SegmentationException(ServiceException):
    """切割异常"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            error_code=ErrorCode.SEGMENTATION_FAILED,
            message=message,
            suggested_solution="请检查边界框参数是否正确",
            details=details
        )


class RotationException(ServiceException):
    """旋转异常"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            error_code=ErrorCode.ROTATION_DETECTION_FAILED,
            message=message,
            suggested_solution="请检查图像质量或尝试手动指定角度",
            details=details
        )


class StorageException(ServiceException):
    """存储异常"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            error_code=ErrorCode.STORAGE_ERROR,
            message=message,
            suggested_solution="存储服务暂时不可用，请稍后重试",
            details=details
        )