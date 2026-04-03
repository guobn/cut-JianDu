from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RotationDetectionResult(BaseModel):
    """旋转角度检测结果"""
    image_id: str
    detected_angle: float = Field(..., description="检测到的角度（度）")
    confidence: float = Field(..., ge=0, le=1, description="检测置信度")
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.now)


class RotationCorrectionRequest(BaseModel):
    """旋转校正请求"""
    image_id: str
    angle: Optional[float] = Field(None, description="指定角度，不指定则自动检测")
    auto_crop: bool = Field(True, description="是否自动裁剪黑边")


class RotationCorrectionResult(BaseModel):
    """旋转校正结果"""
    correction_id: str
    image_id: str
    original_angle: float
    corrected_angle: float
    output_path: str
    width: int
    height: int
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.now)
