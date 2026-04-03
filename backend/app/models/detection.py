from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ModelType(str, Enum):
    """Detection model types - 单支检测只使用 YOLOV8 和 YOLOV11_FINETUNED"""
    YOLOV8 = "yolov8"
    YOLOV11_FINETUNED = "yolov11-finetuned"  # YOLOv11微调模型，用于单支简牍检测


class BoundingBox(BaseModel):
    """边界框"""
    id: str = Field(..., description="边界框ID")
    x: int = Field(..., description="左上角X坐标")
    y: int = Field(..., description="左上角Y坐标")
    width: int = Field(..., gt=0, description="宽度")
    height: int = Field(..., gt=0, description="高度")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="置信度")
    rotation: float = Field(0.0, description="旋转角度")
    order: int = Field(..., gt=0, description="排列顺序")


class DetectionParameters(BaseModel):
    """检测参数"""
    min_width: int = Field(50, gt=0, description="最小宽度")
    min_height: int = Field(200, gt=0, description="最小高度")
    max_width: Optional[int] = Field(None, description="最大宽度")
    max_height: Optional[int] = Field(None, description="最大高度")
    aspect_ratio_min: float = Field(0.05, gt=0, description="最小长宽比")
    aspect_ratio_max: float = Field(0.2, gt=0, description="最大长宽比")
    edge_sensitivity: float = Field(0.5, ge=0, le=1, description="边缘检测灵敏度")
    background_type: str = Field("white", description="背景类型")
    model_type: ModelType = Field(ModelType.YOLOV8, description="检测模型类型")


class DetectionResult(BaseModel):
    """检测结果"""
    detection_id: str
    image_id: str
    mode: str = Field(..., description="检测模式: single-slip 或 single-character")
    detections: List[BoundingBox]
    parameters: dict
    total_count: int
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.now)


class DetectionRequest(BaseModel):
    """检测请求。优先使用前端传来的图像 image_base64，若无则用 image_id 由后端加载。"""
    image_id: Optional[str] = Field(None, description="图像ID（与 image_base64 二选一，用于切割时关联原图）")
    image_base64: Optional[str] = Field(None, description="前端已加载图像 base64（data:image/xxx;base64,... 或纯 base64），与 image_id 二选一")
    mode: str = Field(..., description="检测模式: single-slip 或 single-character")
    parameters: Optional[DetectionParameters] = None

    @model_validator(mode="after")
    def require_image_source(self):
        if not self.image_base64 and not self.image_id:
            raise ValueError("请提供 image_id 或 image_base64 之一")
        return self


class SegmentationRequest(BaseModel):
    """切割请求"""
    image_id: str
    bounding_boxes: List[BoundingBox]
    output_format: str = Field("png", description="输出格式")
    add_padding: bool = Field(False, description="是否添加边距")
    padding_size: int = Field(10, ge=0, description="边距大小")
    # 对于“单支 -> 单字”切割，前端会传入上一层单支的 segment_id，
    # 用于在 Supabase 中建立 parent_segment_id / source_image_id 关系。
    parent_segment_id: Optional[str] = Field(
        default=None, description="父级切割结果 ID（单支切割时为空，单字切割时为单支的 segment_id）"
    )


class SegmentationResult(BaseModel):
    """切割结果"""
    segmentation_id: str
    image_id: str
    total_count: int
    results: List[dict]  # [{id, filename, path, width, height}]
    processing_time: float
    created_at: datetime = Field(default_factory=datetime.now)
