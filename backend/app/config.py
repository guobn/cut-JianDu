from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    # 基础配置
    app_name: str = "基于云存储的简牍图片切割及管理系统的设计与实现"
    app_version: str = "1.0.0"
    debug: bool = True
    env: str = "dev"
    
    # 服务器配置
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    
    # 文件存储配置
    upload_dir: str = "./uploads"
    result_dir: str = "./results"
    temp_dir: str = "./temp"
    max_file_size: int = 52428800  # 50MB
    
    # 图像处理配置
    default_image_quality: int = 95
    thumbnail_size: int = 800
    
    # JWT配置（保留原有）
    jwt_secret_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    supabase_jwt_secret: Optional[str] = None

    # Supabase 配置（用于模块 2：切割结果与元数据上云）
    supabase_url: Optional[str] = None
    supabase_service_key: Optional[str] = None
    supabase_segments_bucket: str = "segments"

    # 单支简牍 YOLO 检测模型（可选，配置后优先使用 YOLOv8 检测单支）
    yolov8_slip_model_path: Optional[str] = None
    yolov8_slip_class_id: int = 0
    yolov8_slip_conf_threshold: float = 0.01  # 极低阈值，最大召回率

    # YOLOv11 微调模型路径（用于单支简牍检测，模型文件：models/bestSingle.pt）
    yolov11_finetuned_model_path: Optional[str] = "models/bestSingle.pt"
    yolov11_finetuned_conf_threshold: float = Field(default=0.4, ge=0, le=1)  # 用户 Jupyter 最佳参数: conf=0.4
    yolov11_finetuned_class_id: int = Field(default=0, ge=0)

    # 单字符区域识别 TorchScript 模型（可选，配置后优先使用，否则 OpenCV 连通域）
    # 例如自训练导出的 models/best.torchscript
    char_torchscript_model_path: Optional[str] = "models/best.torchscript"
    char_conf_threshold: float = 0.25

    # SAHI 切片推理配置（用于大图单字检测）
    sahi_slice_size: int = 640  # 切片大小（像素）
    sahi_overlap_ratio: float = 0.25  # 切片重叠比例
    sahi_nms_threshold: float = 0.35  # NMS IoU 阈值 (用户 Jupyter 最佳参数: iou=0.35)
    sahi_use_soft_nms: bool = True  # 是否使用 Soft-NMS

    # Celery 配置（异步任务队列）
    celery_broker_url: str = "redis://default:123456gbn@14.103.152.219:6379/0"
    celery_result_backend: str = "redis://default:123456gbn@14.103.152.219:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def ensure_directories(self):
        """确保必要的目录存在"""
        for directory in [self.upload_dir, self.result_dir, self.temp_dir]:
            os.makedirs(directory, exist_ok=True)


settings = Settings()
# 启动时创建必要的目录
settings.ensure_directories()
