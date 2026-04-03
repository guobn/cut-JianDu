from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ImageInfo(BaseModel):
    """图像基本信息"""
    image_id: str = Field(..., description="图像唯一标识")
    filename: str = Field(..., description="文件名")
    width: int = Field(..., gt=0, description="图像宽度")
    height: int = Field(..., gt=0, description="图像高度")
    format: str = Field(..., description="图像格式 (JPEG/PNG/TIFF)")
    file_size: int = Field(..., gt=0, description="文件大小（字节）")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")
    storage_path: str = Field(..., description="存储路径")


class ImageUploadResponse(BaseModel):
    """图像上传响应"""
    image_id: str
    filename: str
    width: int
    height: int
    format: str
    file_size: int
    upload_time: datetime
    storage_path: Optional[str] = None
    public_url: Optional[str] = None
    slip_number: Optional[str] = None
    message: str = "图像上传成功"


class ImageListItem(BaseModel):
    """图像列表项"""
    image_id: str
    filename: str
    width: int
    height: int
    format: str
    file_size: int
    upload_time: datetime
    thumbnail_url: Optional[str] = None
