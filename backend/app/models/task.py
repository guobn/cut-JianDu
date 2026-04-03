"""任务状态模型"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"


class TaskResult(BaseModel):
    """任务结果模型"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[float] = None

    class Config:
        use_enum_values = True