"""
图像组和缓存相关的 Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


# ============================================
# 图像组相关模型
# ============================================

class ImageGroupCreate(BaseModel):
    """创建图像组请求"""
    name: str = Field(..., min_length=1, max_length=255, description="组名称")
    description: Optional[str] = Field(None, max_length=1000, description="组描述")
    source_site: Optional[str] = Field(None, description="出土地点")
    period: Optional[str] = Field(None, description="时代断代")
    material: Optional[str] = Field(None, description="材质（竹/木）")
    collection: Optional[str] = Field(None, description="收藏机构")
    excavation_year: Optional[str] = Field(None, description="发掘年份")
    batch_no: Optional[str] = Field(None, description="批次编号")


class ImageGroupUpdate(BaseModel):
    """更新图像组请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_site: Optional[str] = None
    period: Optional[str] = None
    material: Optional[str] = None
    collection: Optional[str] = None
    excavation_year: Optional[str] = None
    batch_no: Optional[str] = None
    status: Optional[str] = Field(None, description="组状态")


class ImageGroupResponse(BaseModel):
    """图像组响应"""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    source_site: Optional[str]
    period: Optional[str]
    material: Optional[str]
    collection: Optional[str]
    excavation_year: Optional[str]
    batch_no: Optional[str]
    status: str
    total_images: int
    processed_images: int
    thumbnail_url: Optional[str]
    export_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# 缓存相关模型
# ============================================

class ProcessingCacheCreate(BaseModel):
    """创建缓存记录请求"""
    source_image_id: UUID
    cache_type: str = Field(..., description="缓存类型: thumbnail/normalized/slip_detect/char_detect")
    cache_url: str = Field(..., description="缓存文件URL")
    cache_meta: Optional[Dict[str, Any]] = Field(default_factory=dict, description="缓存元数据")


class ProcessingCacheResponse(BaseModel):
    """缓存记录响应"""
    id: UUID
    source_image_id: UUID
    cache_type: str
    cache_url: str
    cache_meta: Dict[str, Any]
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# 导出相关模型
# ============================================

class ExportRecordResponse(BaseModel):
    """导出记录响应"""
    id: UUID
    group_id: UUID
    user_id: UUID
    export_format: str
    status: str
    file_url: Optional[str]
    file_size_bytes: Optional[int]
    record_count: Dict[str, int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExportStatusResponse(BaseModel):
    """导出状态响应"""
    export_id: UUID
    status: str
    progress: float = Field(..., ge=0, le=1, description="进度 0-1")
    file_url: Optional[str]
    file_size: Optional[int]
    error_message: Optional[str]


# ============================================
# 批量处理配置模型
# ============================================

class PreprocessConfig(BaseModel):
    """预处理配置"""
    target_long_side: int = Field(default=2000, ge=500, le=4000, description="目标长边像素")
    keep_aspect_ratio: bool = Field(default=True, description="保持宽高比")
    auto_rotate: bool = Field(default=True, description="启用自动旋转检测")
    fixed_rotation_angle: Optional[float] = Field(None, ge=-180, le=180, description="固定旋转角度")
    grayscale: bool = Field(default=False, description="灰度化")
    clahe_enabled: bool = Field(default=True, description="对比度增强CLAHE")
    denoise_strength: int = Field(default=2, ge=0, le=5, description="去噪强度")
    output_format: str = Field(default="PNG", description="输出格式: PNG/JPEG")
    overwrite_original: bool = Field(default=False, description="覆盖原图")


class SegmentConfig(BaseModel):
    """切割配置"""
    model_type: str = Field(default="yolov11-finetuned", description="模型类型: yolov8/yolov11-finetuned/opencv/auto")
    sahi_slice_size: int = Field(default=640, ge=320, le=1280, description="SAHI切片大小")
    sahi_overlap_ratio: float = Field(default=0.2, ge=0, le=0.5, description="SAHI重叠比例")
    confidence_threshold: float = Field(default=0.4, ge=0.1, le=0.9, description="置信度阈值（yolov11-finetuned推荐0.4）")
    min_char_distance: Optional[int] = Field(None, description="最小字符间距像素")
    # 检测过滤参数（与 Segmentation 页面保持一致）
    min_width: int = Field(default=20, ge=1, description="最小宽度")
    min_height: int = Field(default=40, ge=1, description="最小高度")
    aspect_ratio_min: float = Field(default=0.05, ge=0, description="最小长宽比")
    aspect_ratio_max: float = Field(default=0.6, ge=0, description="最大长宽比")


class BatchMetadataUpdate(BaseModel):
    """批量元数据更新"""
    fields: Dict[str, Any] = Field(..., description="要更新的字段")
    target_level: str = Field(..., description="目标级别: slip/char")


# ============================================
# 源图像相关模型
# ============================================

class SourceImageResponse(BaseModel):
    """源图像响应"""
    id: Optional[UUID] = None
    group_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    filename: str
    file_url: str
    thumbnail_url: Optional[str]
    file_size: int
    width: int
    height: int
    format: str
    created_at: datetime

    class Config:
        from_attributes = True


class SourceImageListResponse(BaseModel):
    """源图像列表响应"""
    items: List[SourceImageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================
# 片段(segment)相关模型
# ============================================

class SegmentCreate(BaseModel):
    """手动创建片段请求"""
    source_image_id: str = Field(..., description="源图像ID")
    segment_type: str = Field(..., description="片段类型: slip/char")
    bbox_x: float = Field(..., description="边界框X坐标")
    bbox_y: float = Field(..., description="边界框Y坐标")
    bbox_width: float = Field(..., description="边界框宽度")
    bbox_height: float = Field(..., description="边界框高度")
    parent_segment_id: Optional[str] = Field(None, description="父片段ID（用于字符归属于单支）")
    validated: bool = Field(False, description="是否已验证")


class SegmentUpdate(BaseModel):
    """更新片段请求"""
    bbox_x: Optional[float] = Field(None, description="边界框X坐标")
    bbox_y: Optional[float] = Field(None, description="边界框Y坐标")
    bbox_width: Optional[float] = Field(None, description="边界框宽度")
    bbox_height: Optional[float] = Field(None, description="边界框高度")
    validated: Optional[bool] = Field(None, description="是否已验证")


class SegmentResponse(BaseModel):
    """片段响应"""
    id: str
    image_id: str
    source_image_id: Optional[str]
    segment_index: int
    segment_type: str
    storage_path: Optional[str]
    public_url: Optional[str]
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    width: Optional[int] = None
    height: Optional[int] = None
    validated: bool
    parent_segment_id: Optional[str]
    created_at: str


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    segment_ids: List[str] = Field(..., description="要删除的片段ID列表")


class ValidateSegmentsRequest(BaseModel):
    """验证片段请求（二选一）"""
    image_id: Optional[str] = Field(None, description="图像ID（验证该图像所有片段）")
    segment_ids: Optional[List[str]] = Field(None, description="片段ID列表")


class ValidationStatusResponse(BaseModel):
    """验证状态响应"""
    total_images: int
    validated_images: int
    slips_validated: int
    chars_validated: int


# ============================================
# 导出配置模型
# ============================================

class ExportConfig(BaseModel):
    """导出配置请求"""
    format: str = Field(default="msj", description="导出格式: msj/coco/both")
    include_images: bool = Field(default=False, description="是否包含图片文件")
