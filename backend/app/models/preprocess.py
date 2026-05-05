from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PreprocessGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class PreprocessGroupResponse(BaseModel):
    id: str
    name: str
    kind: str
    preprocess_status: Optional[str] = None
    total_images: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PreprocessProgressResponse(BaseModel):
    stage: str
    total: int = 0
    done: int = 0
    percent: float = 0.0
    task_id: Optional[str] = None


class PreprocessAnglePatchRequest(BaseModel):
    rotation_angle: Optional[float] = None
    preprocess_skipped: Optional[bool] = None
    accepted: Optional[bool] = None


class PreprocessNormalizeRequest(BaseModel):
    target_size: int = Field(..., ge=256, le=4096)
    keep_ratio: bool = True
    interp: str = Field(..., pattern="^(nearest|linear|cubic|area|lanczos4)$")
    padding: str = Field(..., pattern="^(white|black|gray)$")


class PreprocessAngleItemResponse(BaseModel):
    image_id: str
    filename: str
    file_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    rotation_angle: Optional[float] = None
    rotation_confidence: Optional[float] = None
    preprocess_skipped: bool = False
    status: str
    review_state: str
