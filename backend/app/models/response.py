from pydantic import BaseModel
from typing import Optional, Any, Generic, TypeVar
from enum import Enum

T = TypeVar('T')


class ResponseStatus(str, Enum):
    """响应状态"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = "操作成功"
    data: Optional[T] = None

    class Config:
        use_enum_values = True


class ErrorResponse(BaseModel):
    """统一错误响应"""
    status: str = "error"
    error_code: str
    error_message: str
    suggested_solution: str
    data: Optional[Any] = None


class SuccessResponse(BaseModel, Generic[T]):
    """统一成功响应"""
    status: str = "success"
    message: str
    data: Optional[T] = None


class TaskSubmitResponse(BaseModel):
    """任务提交响应"""
    task_id: str
    status: str
    message: str


class DetectionResponse(BaseModel):
    """检测响应"""
    status: str = "success"
    message: str = "检测完成"
    data: Optional[Any] = None


class SegmentationResponse(BaseModel):
    """切割响应"""
    status: str = "success"
    message: str = "切割完成"
    data: Optional[Any] = None


class RotationResponse(BaseModel):
    """旋转响应"""
    status: str = "success"
    message: str = "旋转校正完成"
    data: Optional[Any] = None


# 辅助函数
def success_response(data: Any = None, message: str = "操作成功") -> dict:
    """构建成功响应"""
    return {
        "status": "success",
        "message": message,
        "data": data
    }


def error_response(
    error_code: str,
    error_message: str,
    suggested_solution: str = "请稍后重试",
    data: Any = None
) -> dict:
    """构建错误响应"""
    return {
        "status": "error",
        "error_code": error_code,
        "error_message": error_message,
        "suggested_solution": suggested_solution,
        "data": data
    }
