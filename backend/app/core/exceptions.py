"""统一异常处理模块"""

from typing import Optional, Any
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    INVALID_IMAGE_DATA = "INVALID_IMAGE_DATA"
    DETECTION_FAILED = "DETECTION_FAILED"
    MODEL_INFERENCE_FAILED = "MODEL_INFERENCE_FAILED"
    SEGMENTATION_FAILED = "SEGMENTATION_FAILED"
    ROTATION_DETECTION_FAILED = "ROTATION_DETECTION_FAILED"
    STORAGE_ERROR = "STORAGE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


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
        self.suggested_solution = suggested_solution or "请稍后重试"
        self.details = details
        super().__init__(message)

    def to_response(self) -> dict:
        """转换为 API 响应格式"""
        return {
            "status": "error",
            "error_code": self.error_code.value,
            "error_message": self.message,
            "suggested_solution": self.suggested_solution,
            "data": None
        }