from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NormalizationRequest(BaseModel):
    """尺寸归一化请求"""
    image_id: str
    target_width: int = Field(800, gt=0, description="目标宽度")
    target_height: int = Field(1200, gt=0, description="目标高度")
    keep_aspect_ratio: bool = Field(True, description="是否保持长宽比")
    padding_color: str = Field("white", description="填充颜色")
    interpolation: str = Field("linear", description="插值方法")


class NormalizationResult(BaseModel):
    """尺寸归一化结果"""
    normalization_id: str
    image_id: str
    original_width: int
    original_height: int
    target_width: int
    target_height: int
    output_path: str
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.now)
