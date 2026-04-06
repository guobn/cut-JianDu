"""Celery Worker 配置"""

from celery import Celery
from app.config import settings

# 创建 Celery 实例
celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区设置
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 结果过期时间（秒）
    result_expires=3600,
    # 任务追踪
    task_track_started=True,
    # 使用 solo pool 避免 billiard 兼容性问题
    worker_pool="solo",
    # Redis 连接重试配置
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # 结果后端配置
    result_backend_transport_options={
        "master_name": "mymaster",
        "connection_pool": True,
    },
)

# 自动发现任务模块
celery_app.autodiscover_tasks(["app.services.celery_tasks"])