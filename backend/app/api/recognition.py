"""
recognition 批量检测接口
提供基于图像组的批量单支/单字检测功能
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Any
import requests

from app.core.auth import get_current_user
from app.config import settings
from app.services.celery_tasks import batch_segment_slips_task, batch_segment_chars_task

router = APIRouter(prefix="/api/recognition", tags=["recognition"])


# ============================================
# Supabase 辅助函数
# ============================================

def _require_supabase_config() -> None:
    """确保 Supabase 相关配置存在。"""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Supabase 配置缺失，请在后端 .env 中设置 SUPABASE_URL 与 SUPABASE_SERVICE_KEY")


def _base_url() -> str:
    """获取 Supabase REST API 基础 URL。"""
    return settings.supabase_url.rstrip("/")


def _auth_headers() -> dict:
    """获取认证请求头。"""
    return {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json"
    }


def _get_user_id(user) -> str:
    """从用户对象获取 user_id。"""
    if hasattr(user, 'id'):
        return str(user.id)
    return str(user)


# ============================================
# 请求/响应模型
# ============================================

class BatchDetectRequest(BaseModel):
    """批量检测请求"""
    group_id: str = Field(..., description="图像组ID")


class BatchDetectResponse(BaseModel):
    """批量检测响应"""
    task_id: str = Field(..., description="Celery 任务ID")
    group_id: str = Field(..., description="图像组ID")
    total_images: int = Field(..., description="图像组内图片总数")
    status: str = Field(..., description="任务状态: processing")


# ============================================
# 批量检测接口
# ============================================

@router.post("/batch-detect-slips", response_model=BatchDetectResponse)
async def batch_detect_slips(
    request: BatchDetectRequest,
    user=Depends(get_current_user)
):
    """
    批量检测单支简牍

    行为：
    1. 从 source_images 取出该组所有图片
    2. 逐张调用现有单张单支检测逻辑
    3. 检测结果写入 segments 表（segment_type='slip'，source_image_id 关联）
    4. 返回 { task_id, total_images, status }
    """
    _require_supabase_config()
    user_id = _get_user_id(user)
    group_id = request.group_id

    # 验证组是否存在且属于当前用户
    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    params = {"id": f"eq.{group_id}", "user_id": f"eq.{user_id}"}

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证图像组失败：{resp.status_code} {resp.text[:200]}"
        )

    groups_data = resp.json() or []
    if not groups_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图像组不存在：{group_id}"
        )

    # 获取组内图像总数
    images_url = f"{_base_url()}/rest/v1/source_images"
    images_params = {"group_id": f"eq.{group_id}"}
    images_resp = requests.get(images_url, headers=headers, params=images_params)
    total_images = len(images_resp.json()) if images_resp.status_code == 200 else 0

    if total_images == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图像组内没有图片：{group_id}"
        )

    # 更新组状态为 segmenting
    update_url = f"{_base_url()}/rest/v1/image_groups"
    update_params = {"id": f"eq.{group_id}"}
    requests.patch(
        update_url,
        headers=headers,
        params=update_params,
        json={"status": "segmenting"}
    )

    # 使用默认配置触发异步任务
    config = {
        "model_type": "auto",
        "sahi_slice_size": 640,
        "sahi_overlap_ratio": 0.2,
        "confidence_threshold": 0.5,
        "min_char_distance": None
    }

    # 触发实际的单支切割异步任务（Celery）
    batch_task = batch_segment_slips_task.delay(group_id, config)

    return BatchDetectResponse(
        task_id=batch_task.id,
        group_id=group_id,
        total_images=total_images,
        status="processing"
    )


@router.post("/batch-detect-chars", response_model=BatchDetectResponse)
async def batch_detect_chars(
    request: BatchDetectRequest,
    user=Depends(get_current_user)
):
    """
    批量检测单字符

    行为：
    1. 从 source_images 取出该组所有图片
    2. 逐张调用现有单张单字符检测逻辑
    3. 检测结果写入 segments 表（segment_type='char'，source_image_id 关联）
    4. 返回 { task_id, total_images, status }
    """
    _require_supabase_config()
    user_id = _get_user_id(user)
    group_id = request.group_id

    # 验证组是否存在且属于当前用户
    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    params = {"id": f"eq.{group_id}", "user_id": f"eq.{user_id}"}

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证图像组失败：{resp.status_code} {resp.text[:200]}"
        )

    groups_data = resp.json() or []
    if not groups_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图像组不存在：{group_id}"
        )

    # 获取组内图像总数
    images_url = f"{_base_url()}/rest/v1/source_images"
    images_params = {"group_id": f"eq.{group_id}"}
    images_resp = requests.get(images_url, headers=headers, params=images_params)
    total_images = len(images_resp.json()) if images_resp.status_code == 200 else 0

    if total_images == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图像组内没有图片：{group_id}"
        )

    # 更新组状态为 segmenting
    update_url = f"{_base_url()}/rest/v1/image_groups"
    update_params = {"id": f"eq.{group_id}"}
    requests.patch(
        update_url,
        headers=headers,
        params=update_params,
        json={"status": "segmenting"}
    )

    # 使用默认配置触发异步任务
    config = {
        "model_type": "auto",
        "sahi_slice_size": 640,
        "sahi_overlap_ratio": 0.2,
        "confidence_threshold": 0.5,
        "min_char_distance": None
    }

    # 触发实际的单字切割异步任务（Celery）
    batch_task = batch_segment_chars_task.delay(group_id, config)

    return BatchDetectResponse(
        task_id=batch_task.id,
        group_id=group_id,
        total_images=total_images,
        status="processing"
    )
