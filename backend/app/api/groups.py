"""
图像组管理路由
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import requests
from pathlib import Path
from PIL import Image
import io
import os
import math

from celery.result import AsyncResult

from app.models.groups import (
    ImageGroupCreate, ImageGroupUpdate, ImageGroupResponse,
    ProcessingCacheCreate, ProcessingCacheResponse,
    ExportRecordResponse, ExportConfig, PreprocessConfig, SegmentConfig, BatchMetadataUpdate,
    SourceImageResponse, SourceImageListResponse,
    SegmentCreate, SegmentUpdate, SegmentResponse,
    BatchDeleteRequest, ValidateSegmentsRequest, ValidationStatusResponse
)
from app.core.auth import get_current_user
from app.config import settings
from app.worker import celery_app
from app.services.celery_tasks import batch_segment_slips_task, batch_segment_chars_task
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/groups", tags=["groups"])

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


def _auth_headers() -> Dict[str, str]:
    """
    Supabase REST 通用请求头（使用 service key）。
    """
    _require_supabase_config()
    return {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }


def _get_user_id(user: Any) -> str:
    """从用户对象提取 UUID 字符串，未登录返回默认匿名用户 UUID。"""
    ANONYMOUS_USER_ID = "1214995c-06c4-46b4-8f75-a1ab2ffe0546"
    if isinstance(user, dict):
        uid = user.get("id")
        if uid and isinstance(uid, UUID):
            return str(uid)
        return uid or ANONYMOUS_USER_ID
    return ANONYMOUS_USER_ID


def _parse_image_group_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """将数据库行转换为 ImageGroupResponse 兼容的字典。"""
    # 处理 UUID 类型转换
    def to_str(val: Any) -> Optional[str]:
        if val is None:
            return None
        if isinstance(val, UUID):
            return str(val)
        return str(val) if not isinstance(val, str) else val

    def to_datetime(val: Any) -> str:
        if val is None:
            return datetime.now().isoformat() + "Z"
        if isinstance(val, datetime):
            return val.isoformat() + "Z"
        if isinstance(val, str):
            # 处理 ISO 格式
            if val.endswith("Z"):
                return val
            return val.replace("+00:00", "Z") if "+00:00" in val else val + "Z"
        return datetime.now().isoformat() + "Z"

    return {
        "id": to_str(row.get("id")),
        "user_id": to_str(row.get("user_id")),
        "name": row.get("name", ""),
        "description": row.get("description"),
        "source_site": row.get("source_site"),
        "period": row.get("period"),
        "material": row.get("material"),
        "collection": row.get("collection"),
        "excavation_year": row.get("excavation_year"),
        "batch_no": row.get("batch_no"),
        "status": row.get("status", "created"),
        "total_images": row.get("total_images", 0) or 0,
        "processed_images": row.get("processed_images", 0) or 0,
        "thumbnail_url": row.get("thumbnail_url"),
        "export_url": row.get("export_url"),
        "created_at": to_datetime(row.get("created_at")),
        "updated_at": to_datetime(row.get("updated_at")),
    }


# ============================================
# 图像组 CRUD 操作
# ============================================

@router.post("", response_model=ImageGroupResponse)
async def create_group(
    data: ImageGroupCreate,
    user=Depends(get_current_user)
):
    """创建图像组"""
    _require_supabase_config()
    user_id = _get_user_id(user)

    row = {
        "user_id": user_id,
        "name": data.name,
        "description": data.description,
        "source_site": data.source_site,
        "period": data.period,
        "material": data.material,
        "collection": data.collection,
        "excavation_year": data.excavation_year,
        "batch_no": data.batch_no,
        "status": "created",
        "total_images": 0,
        "processed_images": 0,
    }

    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"

    resp = requests.post(url, headers=headers, json=row)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建图像组失败：{resp.status_code} {resp.text[:200]}"
        )

    result_data = resp.json()
    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建图像组失败，Supabase 返回数据为空"
        )

    return _parse_image_group_row(result_data[0])


@router.get("", response_model=List[ImageGroupResponse])
async def list_groups(user=Depends(get_current_user)):
    """获取所有图像组"""
    _require_supabase_config()
    user_id = _get_user_id(user)

    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    params = {
        "user_id": f"eq.{user_id}",
        "order": "created_at.desc"
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图像组列表失败：{resp.status_code} {resp.text[:200]}"
        )

    result_data = resp.json() or []
    return [_parse_image_group_row(row) for row in result_data]


@router.get("/{group_id}", response_model=ImageGroupResponse)
async def get_group(
    group_id: str,
    user=Depends(get_current_user)
):
    """获取单个图像组"""
    _require_supabase_config()
    user_id = _get_user_id(user)

    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    params = {
        "id": f"eq.{group_id}",
        "user_id": f"eq.{user_id}"  # 确保只能访问自己的组
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图像组失败：{resp.status_code} {resp.text[:200]}"
        )

    result_data = resp.json() or []
    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图像组不存在：{group_id}"
        )

    return _parse_image_group_row(result_data[0])


@router.put("/{group_id}", response_model=ImageGroupResponse)
async def update_group(
    group_id: str,
    data: ImageGroupUpdate,
    user=Depends(get_current_user)
):
    """更新图像组"""
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 构建更新数据（只包含非 None 字段）
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.source_site is not None:
        update_data["source_site"] = data.source_site
    if data.period is not None:
        update_data["period"] = data.period
    if data.material is not None:
        update_data["material"] = data.material
    if data.collection is not None:
        update_data["collection"] = data.collection
    if data.excavation_year is not None:
        update_data["excavation_year"] = data.excavation_year
    if data.batch_no is not None:
        update_data["batch_no"] = data.batch_no
    if data.status is not None:
        update_data["status"] = data.status

    if not update_data:
        # 没有实际更新内容，直接返回当前状态
        return await get_group(group_id, user)

    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"
    # 确保只更新自己的组
    params = {
        "id": f"eq.{group_id}",
        "user_id": f"eq.{user_id}"
    }

    resp = requests.patch(url, headers=headers, params=params, json=update_data)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新图像组失败：{resp.status_code} {resp.text[:200]}"
        )

    result_data = resp.json() or []
    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图像组不存在或无权更新：{group_id}"
        )

    return _parse_image_group_row(result_data[0])


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    user=Depends(get_current_user)
):
    """删除图像组"""
    _require_supabase_config()
    user_id = _get_user_id(user)

    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    # 确保只删除自己的组
    params = {
        "id": f"eq.{group_id}",
        "user_id": f"eq.{user_id}"
    }

    resp = requests.delete(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"删除图像组失败：{resp.status_code} {resp.text[:200]}"
        )

    return {"message": "Group deleted", "group_id": group_id}


# ============================================
# 批量处理操作
# ============================================

@router.post("/{group_id}/preprocess")
async def preprocess_group(
    group_id: str,
    config: PreprocessConfig,
    user=Depends(get_current_user)
):
    """批量预处理"""
    _require_supabase_config()
    user_id = _get_user_id(user)

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

    # 更新组状态为 preprocessing
    update_url = f"{_base_url()}/rest/v1/image_groups"
    update_params = {"id": f"eq.{group_id}"}
    requests.patch(
        update_url,
        headers=headers,
        params=update_params,
        json={"status": "preprocessing"}
    )

    # TODO: 触发实际的预处理异步任务（Celery）
    # 这里返回一个任务 ID，前端可以轮询进度
    task_id = f"preprocess_{group_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return {
        "task_id": task_id,
        "group_id": group_id,
        "status": "processing",
        "config": config.model_dump()
    }


@router.post("/{group_id}/segment/slips")
async def segment_slips(
    group_id: str,
    config: SegmentConfig,
    user=Depends(get_current_user)
):
    """批量切割单支"""
    _require_supabase_config()
    user_id = _get_user_id(user)

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

    # 更新组状态为 segmenting
    update_url = f"{_base_url()}/rest/v1/image_groups"
    update_params = {"id": f"eq.{group_id}"}
    requests.patch(
        update_url,
        headers=headers,
        params=update_params,
        json={"status": "segmenting"}
    )

    # 触发实际的单支切割异步任务（Celery）
    batch_task = batch_segment_slips_task.delay(group_id, config.model_dump())

    return {
        "batch_task_id": batch_task.id,
        "group_id": group_id,
        "total_images": total_images,
        "status": "processing",
        "config": config.model_dump()
    }


@router.post("/{group_id}/segment/chars")
async def segment_chars(
    group_id: str,
    config: SegmentConfig,
    user=Depends(get_current_user)
):
    """批量切割单字"""
    _require_supabase_config()
    user_id = _get_user_id(user)

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

    # 更新组状态为 segmenting
    update_url = f"{_base_url()}/rest/v1/image_groups"
    update_params = {"id": f"eq.{group_id}"}
    requests.patch(
        update_url,
        headers=headers,
        params=update_params,
        json={"status": "segmenting"}
    )

    # 触发实际的单字切割异步任务（Celery）
    batch_task = batch_segment_chars_task.delay(group_id, config.model_dump())

    return {
        "batch_task_id": batch_task.id,
        "group_id": group_id,
        "total_images": total_images,
        "status": "processing",
        "config": config.model_dump()
    }


@router.get("/{group_id}/batch-progress")
async def get_batch_progress(
    group_id: str,
    batch_task_id: str = Query(..., description="批次任务 ID"),
    user=Depends(get_current_user)
):
    """获取批次处理进度"""
    _require_supabase_config()
    user_id = _get_user_id(user)

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

    # 使用 AsyncResult 获取 Celery 任务状态
    batch_result = AsyncResult(batch_task_id, app=celery_app)

    # 获取任务状态和进度信息
    task_state = batch_result.state
    task_meta = batch_result.info if hasattr(batch_result, "info") else {}

    # 提取进度信息
    if isinstance(task_meta, dict):
        progress = task_meta.get("progress", 0.0)
        total = task_meta.get("total", 0)
        completed = task_meta.get("completed", 0)
        failed = task_meta.get("failed", 0)
        errors = task_meta.get("errors", [])
    else:
        progress = 0.0
        total = 0
        completed = 0
        failed = 0
        errors = []

    return {
        "batch_task_id": batch_task_id,
        "status": task_state,
        "progress": progress,
        "total": total,
        "completed": completed,
        "failed": failed,
        "errors": errors
    }


@router.get("/{group_id}/progress")
async def get_progress(
    group_id: str,
    user=Depends(get_current_user)
):
    """获取处理进度"""
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 从 image_groups 表获取组状态和进度
    url = f"{_base_url()}/rest/v1/image_groups"
    headers = _auth_headers()
    params = {"id": f"eq.{group_id}", "user_id": f"eq.{user_id}"}

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取进度失败：{resp.status_code} {resp.text[:200]}"
        )

    groups_data = resp.json() or []
    if not groups_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图像组不存在：{group_id}"
        )

    group = groups_data[0]
    total = group.get("total_images", 0) or 0
    completed = group.get("processed_images", 0) or 0
    status_str = group.get("status", "created")

    # 映射状态
    status_mapping = {
        "created": "pending",
        "preprocessing": "processing",
        "segmenting": "processing",
        "completed": "completed",
        "exported": "completed"
    }

    return {
        "total": total,
        "completed": completed,
        "progress": completed / total if total > 0 else 0.0,
        "status": status_mapping.get(status_str, status_str),
        "group_status": status_str
    }


@router.put("/{group_id}/batch-metadata")
async def batch_update_metadata(
    group_id: str,
    data: BatchMetadataUpdate,
    user=Depends(get_current_user)
):
    """批量更新元数据"""
    _require_supabase_config()
    user_id = _get_user_id(user)

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

    fields = data.fields
    target_level = data.target_level  # 'slip' 或 'char'

    if target_level == "slip":
        # 批量更新 slip_image_metadata 表
        # 先获取组内所有图像
        images_url = f"{_base_url()}/rest/v1/source_images"
        images_params = {"group_id": f"eq.{group_id}"}
        images_resp = requests.get(images_url, headers=headers, params=images_params)

        if images_resp.status_code < 400:
            images_data = images_resp.json() or []
            image_ids = [img["id"] for img in images_data]

            if image_ids:
                # 批量更新 slip_image_metadata
                for img_id in image_ids:
                    update_url = f"{_base_url()}/rest/v1/slip_image_metadata"
                    update_params = {"image_id": f"eq.{img_id}"}
                    requests.patch(
                        update_url,
                        headers=headers,
                        params=update_params,
                        json=fields
                    )

    elif target_level == "char":
        # 批量更新 segments 表（segment_type='char'）
        # 先获取组内所有图像
        images_url = f"{_base_url()}/rest/v1/source_images"
        images_params = {"group_id": f"eq.{group_id}"}
        images_resp = requests.get(images_url, headers=headers, params=images_params)

        if images_resp.status_code < 400:
            images_data = images_resp.json() or []
            image_ids = [img["id"] for img in images_data]

            if image_ids:
                # 批量更新 segments 表中对应字符记录
                for img_id in image_ids:
                    update_url = f"{_base_url()}/rest/v1/segments"
                    update_params = {
                        "image_id": f"eq.{img_id}",
                        "segment_type": f"eq.char"
                    }
                    requests.patch(
                        update_url,
                        headers=headers,
                        params=update_params,
                        json=fields
                    )

    return {
        "message": "Metadata updated",
        "group_id": group_id,
        "target_level": target_level,
        "updated_fields": fields
    }


@router.post("/{group_id}/export", response_model=ExportRecordResponse)
async def export_group(
    group_id: str,
    config: ExportConfig,
    user=Depends(get_current_user)
):
    """导出图像组数据（MSJ 或 COCO 格式）"""
    _require_supabase_config()
    user_id = _get_user_id(user)

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

    # 确定导出格式
    export_format = config.format  # "msj", "coco", or "both"

    # 创建初始导出记录（pending 状态）
    export_row = {
        "group_id": group_id,
        "user_id": user_id,
        "export_format": export_format,
        "status": "pending",
        "record_count": {"groups": 1, "source_images": 0, "slips": 0, "chars": 0}
    }

    export_url = f"{_base_url()}/rest/v1/export_records"
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"

    resp = requests.post(export_url, headers=headers, json=export_row)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建导出记录失败：{resp.status_code} {resp.text[:200]}"
        )

    export_data = resp.json()
    if not export_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建导出记录失败，Supabase 返回数据为空"
        )

    exp_row = export_data[0]

    # 使用 ExportService 执行导出
    export_service = ExportService()
    result = {"export_url": None, "record_count": {"groups": 0, "source_images": 0, "slips": 0, "chars": 0}, "file_size": 0}

    try:
        if export_format == "msj":
            result = export_service.export_group_as_msj(group_id, config.include_images)
        elif export_format == "coco":
            result = export_service.export_group_as_coco(group_id)
        elif export_format == "both":
            # 执行 MSJ 导出
            msj_result = export_service.export_group_as_msj(group_id, config.include_images)
            # 执行 COCO 导出
            coco_result = export_service.export_group_as_coco(group_id)
            result = {
                "export_url": msj_result["export_url"],  # 返回 MSJ URL 作为主要 URL
                "record_count": {
                    "groups": 1,
                    "source_images": msj_result["record_count"]["source_images"],
                    "slips": msj_result["record_count"]["slips"],
                    "chars": msj_result["record_count"]["chars"],
                },
                "file_size": msj_result["file_size"] + coco_result["file_size"],
            }
    except Exception as e:
        # 更新导出记录为失败状态
        update_url = f"{_base_url()}/rest/v1/export_records"
        update_params = {"id": f"eq.{exp_row.get('id')}"}
        requests.patch(
            update_url,
            headers=_auth_headers(),
            params=update_params,
            json={"status": "failed"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出失败：{str(e)}"
        )

    # 解析导出记录响应
    def to_str(val: Any) -> Optional[str]:
        if val is None:
            return None
        if isinstance(val, UUID):
            return str(val)
        return str(val) if not isinstance(val, str) else val

    def to_datetime(val: Any) -> datetime:
        if val is None:
            return datetime.now()
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                cleaned = val.strip()
                if cleaned.endswith("Z"):
                    cleaned = cleaned[:-1] + "+00:00"
                return datetime.fromisoformat(cleaned)
            except Exception:
                return datetime.now()
        return datetime.now()

    # 获取更新后的导出记录
    final_url = f"{_base_url()}/rest/v1/export_records"
    final_params = {"id": f"eq.{exp_row.get('id')}"}
    final_resp = requests.get(final_url, headers=_auth_headers(), params=final_params)
    final_data = final_resp.json() if final_resp.status_code == 200 else []
    final_row = final_data[0] if final_data else exp_row

    return {
        "id": to_str(final_row.get("id")),
        "group_id": to_str(final_row.get("group_id")),
        "user_id": to_str(final_row.get("user_id")),
        "export_format": final_row.get("export_format", export_format),
        "status": final_row.get("status", "completed"),
        "file_url": result.get("export_url") or final_row.get("file_url"),
        "file_size_bytes": result.get("file_size") or final_row.get("file_size_bytes"),
        "record_count": result.get("record_count") or final_row.get("record_count", {"groups": 0, "source_images": 0, "slips": 0, "chars": 0}),
        "created_at": to_datetime(final_row.get("created_at")),
        "completed_at": to_datetime(final_row.get("completed_at"))
    }


# ============================================
# 导出状态查询
# ============================================

@router.get("/exports/{export_id}/status")
async def get_export_status(
    export_id: str,
    user=Depends(get_current_user)
):
    """获取导出状态"""
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 从 export_records 表查询导出状态
    url = f"{_base_url()}/rest/v1/export_records"
    headers = _auth_headers()
    params = {
        "id": f"eq.{export_id}",
        "user_id": f"eq.{user_id}"  # 确保只能访问自己的导出记录
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取导出状态失败：{resp.status_code} {resp.text[:200]}"
        )

    export_data = resp.json() or []
    if not export_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"导出记录不存在：{export_id}"
        )

    exp_row = export_data[0]
    status_str = exp_row.get("status", "pending")
    record_count = exp_row.get("record_count", {})

    # 计算进度（基于记录数量）
    total_estimated = (
        (record_count.get("slips", 0) or 0) +
        (record_count.get("chars", 0) or 0)
    )
    if total_estimated > 0:
        progress = 1.0 if status_str == "completed" else 0.5
    else:
        progress = 0.0 if status_str == "pending" else (1.0 if status_str == "completed" else 0.5)

    return {
        "export_id": export_id,
        "status": status_str,
        "progress": progress,
        "file_url": exp_row.get("file_url"),
        "file_size": exp_row.get("file_size_bytes"),
        "error_message": None,
        "export_format": exp_row.get("export_format"),
        "record_count": record_count
    }


# ============================================
# 图像组图片管理
# ============================================

def _generate_thumbnail(image_bytes: bytes, max_size: int = 800) -> bytes:
    """
    生成缩略图

    Args:
        image_bytes: 原始图像字节数据
        max_size: 最大边长（宽度或高度）

    Returns:
        缩略图字节数据
    """
    img = Image.open(io.BytesIO(image_bytes))
    # 保持宽高比
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    img.save(output, format=img.format or "PNG")
    return output.getvalue()


def _ensure_group_exists_and_owned(group_id: str, user_id: str) -> Dict[str, Any]:
    """验证组存在且属于当前用户，返回组数据。"""
    _require_supabase_config()
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
    return groups_data[0]


def _parse_source_image_row(row: Dict[str, Any]) -> SourceImageResponse:
    """将 source_images 表行转换为 SourceImageResponse。"""
    def to_str(val: Any) -> Optional[str]:
        if val is None:
            return None
        if isinstance(val, UUID):
            return str(val)
        return str(val) if not isinstance(val, str) else val

    def to_datetime(val: Any) -> datetime:
        if val is None:
            return datetime.now()
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                cleaned = val.strip()
                if cleaned.endswith("Z"):
                    cleaned = cleaned[:-1] + "+00:00"
                return datetime.fromisoformat(cleaned)
            except Exception:
                return datetime.now()
        return datetime.now()

    row_group_id = to_str(row.get("group_id"))
    row_id = to_str(row.get("id"))
    return SourceImageResponse(
        id=row_id,
        group_id=row_group_id,
        user_id=to_str(row.get("user_id")),
        filename=row.get("filename", ""),
        file_url=row.get("storage_path", ""),
        thumbnail_url=row.get("thumbnail_url"),
        file_size=row.get("file_size", 0) or 0,
        width=row.get("width", 0) or 0,
        height=row.get("height", 0) or 0,
        format=row.get("format", "UNKNOWN"),
        created_at=to_datetime(row.get("created_at"))
    )


@router.post("/{group_id}/images")
async def upload_group_images(
    group_id: str,
    files: List[UploadFile] = File(...),
    user=Depends(get_current_user)
):
    """
    批量上传图片到图像组（multipart/form-data，field: files）
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    group = _ensure_group_exists_and_owned(group_id, user_id)

    upload_dir = Path(settings.upload_dir) / str(group_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    created_images: List[SourceImageResponse] = []
    errors: List[str] = []

    for file in files:
        try:
            # 读取文件内容
            content = await file.read()
            if not content:
                errors.append(f"{file.filename}: 空文件")
                continue

            # 生成唯一 ID
            image_id = str(uuid4())
            ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
            if ext not in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]:
                ext = ".jpg"

            # 保存原图
            filename = f"{image_id}{ext}"
            file_path = upload_dir / filename
            with open(file_path, "wb") as f:
                f.write(content)

            # 生成缩略图
            thumb_path = None
            try:
                thumb_bytes = _generate_thumbnail(content, max_size=settings.thumbnail_size)
                thumb_filename = f"{image_id}_thumb{ext}"
                thumb_path = upload_dir / thumb_filename
                with open(thumb_path, "wb") as f:
                    f.write(thumb_bytes)
            except Exception as thumb_err:
                pass  # 缩略图生成失败不影响主流程

            # 获取图像尺寸
            try:
                img = Image.open(io.BytesIO(content))
                width, height = img.size
                img_format = img.format or "UNKNOWN"
            except Exception:
                width, height = 0, 0
                img_format = "UNKNOWN"

            file_size = len(content)
            # 写入 source_images 表
            source_row = {
                "id": image_id,
                "group_id": group_id,
                "user_id": user_id,
                "filename": file.filename or filename,
                "storage_path": str(file_path),
                "thumbnail_url": str(thumb_path) if thumb_path else None,
                "file_size": file_size,
                "width": width,
                "height": height,
                "format": img_format,
            }
            insert_url = f"{_base_url()}/rest/v1/source_images"
            insert_headers = _auth_headers()
            insert_headers["Prefer"] = "return=representation"
            resp = requests.post(insert_url, headers=insert_headers, json=source_row)
            if resp.status_code >= 400:
                errors.append(f"{file.filename}: 写入数据库失败 {resp.status_code}")
                continue

            result_data = resp.json()
            if result_data:
                created_images.append(_parse_source_image_row(result_data[0]))
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    # 重新查询 source_images 表总数（比 +N 更可靠，防止并发偏差）
    count_result = requests.get(
        f"{_base_url()}/rest/v1/source_images",
        headers=_auth_headers(),
        params={"group_id": f"eq.{group_id}", "select": "id"}
    )
    total = len(count_result.json()) if count_result.status_code < 400 and count_result.json() else 0
    update_url = f"{_base_url()}/rest/v1/image_groups"
    update_params = {"id": f"eq.{group_id}"}
    requests.patch(
        update_url,
        headers=_auth_headers(),
        params=update_params,
        json={"total_images": total}
    )

    return {
        "uploaded": created_images,
        "errors": errors,
        "total_uploaded": len(created_images)
    }


@router.get("/{group_id}/images", response_model=SourceImageListResponse)
async def list_group_images(
    group_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """
    列出图像组中的图片（支持分页）
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 查询总数
    count_url = f"{_base_url()}/rest/v1/source_images"
    count_params = {"group_id": f"eq.{group_id}", "select": "id"}
    count_resp = requests.get(count_url, headers=_auth_headers(), params=count_params)
    total = len(count_resp.json()) if count_resp.status_code < 400 and count_resp.json() else 0

    # 分页查询
    offset = (page - 1) * page_size
    select_cols = "id,group_id,user_id,filename,storage_path,thumbnail_url,file_size,width,height,format,created_at"
    list_url = f"{_base_url()}/rest/v1/source_images"
    list_params = {
        "group_id": f"eq.{group_id}",
        "select": select_cols,
        "order": "created_at.desc",
        "offset": str(offset),
        "limit": str(page_size)
    }
    resp = requests.get(list_url, headers=_auth_headers(), params=list_params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图片列表失败：{resp.status_code} {resp.text[:200]}"
        )

    rows = resp.json() or []
    items = [_parse_source_image_row(row) for row in rows]
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return SourceImageListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.delete("/{group_id}/images/{image_id}")
async def delete_group_image(
    group_id: str,
    image_id: str,
    user=Depends(get_current_user)
):
    """
    从图像组删除单张图片
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    group = _ensure_group_exists_and_owned(group_id, user_id)

    # 查询图片是否存在
    url = f"{_base_url()}/rest/v1/source_images"
    params = {"id": f"eq.{image_id}", "group_id": f"eq.{group_id}"}
    resp = requests.get(url, headers=_auth_headers(), params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询图片失败：{resp.status_code} {resp.text[:200]}"
        )
    rows = resp.json() or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图片不存在：{image_id}"
        )

    # 删除本地文件
    upload_dir = Path(settings.upload_dir) / str(group_id)
    for ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]:
        file_path = upload_dir / f"{image_id}{ext}"
        if file_path.exists():
            file_path.unlink()
        thumb_path = upload_dir / f"{image_id}_thumb{ext}"
        if thumb_path.exists():
            thumb_path.unlink()

    # 从数据库删除
    del_url = f"{_base_url()}/rest/v1/source_images"
    del_params = {"id": f"eq.{image_id}"}
    del_resp = requests.delete(del_url, headers=_auth_headers(), params=del_params)
    if del_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"删除图片记录失败：{del_resp.status_code} {del_resp.text[:200]}"
        )

    # 重新查询 source_images 表总数（防止并发偏差）
    count_result = requests.get(
        f"{_base_url()}/rest/v1/source_images",
        headers=_auth_headers(),
        params={"group_id": f"eq.{group_id}", "select": "id"}
    )
    total = len(count_result.json()) if count_result.status_code < 400 and count_result.json() else 0
    update_url = f"{_base_url()}/rest/v1/image_groups"
    update_params = {"id": f"eq.{group_id}"}
    requests.patch(
        update_url,
        headers=_auth_headers(),
        params=update_params,
        json={"total_images": total}
    )

    return {"message": "Image deleted", "image_id": image_id, "group_id": group_id}


@router.get("/{group_id}/images/{image_id}/file")
async def get_group_image_file(
    group_id: str,
    image_id: str,
    user=Depends(get_current_user)
):
    """
    获取图像组图片文件
    """
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 查询图片信息获取格式
    url = f"{_base_url()}/rest/v1/source_images"
    params = {"id": f"eq.{image_id}", "group_id": f"eq.{group_id}"}
    resp = requests.get(url, headers=_auth_headers(), params=params)
    if resp.status_code >= 400 or not resp.json():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图片不存在：{image_id}"
        )
    row = resp.json()[0]
    img_format = row.get("format", "PNG").lower()
    ext_map = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "bmp": "bmp", "tiff": "tiff", "tif": "tiff"}
    ext = ext_map.get(img_format, "png")

    # 查找本地文件
    upload_dir = Path(settings.upload_dir) / str(group_id)
    file_path = upload_dir / f"{image_id}.{ext}"
    if not file_path.exists():
        # 尝试其他扩展名
        for try_ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]:
            file_path = upload_dir / f"{image_id}{try_ext}"
            if file_path.exists():
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"图片文件不存在：{image_id}"
            )

    return FileResponse(path=str(file_path), media_type=f"image/{ext}")


@router.get("/{group_id}/images/{image_id}/thumbnail")
async def get_group_image_thumbnail(
    group_id: str,
    image_id: str,
    user=Depends(get_current_user)
):
    """
    获取图像组图片缩略图
    """
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 查询图片信息获取格式
    url = f"{_base_url()}/rest/v1/source_images"
    params = {"id": f"eq.{image_id}", "group_id": f"eq.{group_id}"}
    resp = requests.get(url, headers=_auth_headers(), params=params)
    if resp.status_code >= 400 or not resp.json():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"图片不存在：{image_id}"
        )
    row = resp.json()[0]
    img_format = row.get("format", "PNG").lower()
    ext_map = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "bmp": "bmp", "tiff": "tiff", "tif": "tiff"}
    ext = ext_map.get(img_format, "png")

    # 查找缩略图文件
    upload_dir = Path(settings.upload_dir) / str(group_id)
    thumb_path = upload_dir / f"{image_id}_thumb.{ext}"
    if not thumb_path.exists():
        # 尝试其他扩展名
        for try_ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]:
            thumb_path = upload_dir / f"{image_id}_thumb{try_ext}"
            if thumb_path.exists():
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"缩略图文件不存在：{image_id}"
            )

    return FileResponse(path=str(thumb_path), media_type=f"image/{ext}")


# ============================================
# 片段(segment)管理路由
# ============================================

def _parse_segment_row(row: Dict[str, Any]) -> SegmentResponse:
    """将 segments 表行转换为 SegmentResponse。"""
    from app.services.supabase_service import build_public_url

    def to_str(val: Any) -> Optional[str]:
        if val is None:
            return None
        if isinstance(val, UUID):
            return str(val)
        return str(val) if not isinstance(val, str) else val

    storage_path = row.get("storage_path")
    public_url = build_public_url(storage_path) if storage_path else None

    return SegmentResponse(
        id=to_str(row.get("id")),
        image_id=to_str(row.get("image_id")),
        source_image_id=to_str(row.get("source_image_id")),
        segment_index=row.get("segment_index", 0),
        segment_type=row.get("segment_type", ""),
        storage_path=storage_path,
        public_url=public_url,
        bbox_x=row.get("bbox_x", 0.0),
        bbox_y=row.get("bbox_y", 0.0),
        bbox_width=row.get("bbox_width", 0.0),
        bbox_height=row.get("bbox_height", 0.0),
        width=row.get("width", 0),
        height=row.get("height", 0),
        validated=row.get("validated", False),
        parent_segment_id=to_str(row.get("parent_segment_id")),
        created_at=row.get("created_at", datetime.now().isoformat() + "Z")
    )


@router.get("/{group_id}/segments", response_model=List[SegmentResponse])
async def list_group_segments(
    group_id: str,
    type: Optional[str] = Query(None, description="片段类型过滤: slip/char"),
    validated: Optional[bool] = Query(None, description="验证状态过滤"),
    source_image_id: Optional[str] = Query(None, description="源图像ID过滤"),
    user=Depends(get_current_user)
):
    """
    列出图像组中的片段（通过 source_images 表连接过滤）

    Query params:
    - type: 片段类型过滤 (slip/char)
    - validated: 验证状态过滤 (true/false)
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 首先获取组内所有源图像ID
    images_url = f"{_base_url()}/rest/v1/source_images"
    images_params = {"group_id": f"eq.{group_id}", "select": "id"}
    images_resp = requests.get(images_url, headers=_auth_headers(), params=images_params)
    if images_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取组内图像失败：{images_resp.status_code} {images_resp.text[:200]}"
        )
    image_ids = [img["id"] for img in images_resp.json() or []]
    if not image_ids:
        return []

    # 构建 segments 查询（通过 source_image_id IN (...) 连接）
    segments_url = f"{_base_url()}/rest/v1/segments"
    segment_ids_str = ",".join(image_ids)
    segments_params: Dict[str, Any] = {
        "source_image_id": f"in.({segment_ids_str})",
        "order": "created_at.desc"
    }

    # 添加类型过滤
    if type:
        segments_params["segment_type"] = f"eq.{type}"

    # 添加验证状态过滤
    if validated is not None:
        segments_params["validated"] = f"eq.{str(validated).lower()}"

    # 添加源图像ID过滤
    if source_image_id:
        segments_params["source_image_id"] = f"eq.{source_image_id}"

    segments_resp = requests.get(segments_url, headers=_auth_headers(), params=segments_params)
    if segments_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取片段列表失败：{segments_resp.status_code} {segments_resp.text[:200]}"
        )

    rows = segments_resp.json() or []
    return [_parse_segment_row(row) for row in rows]


@router.post("/{group_id}/segments", response_model=SegmentResponse)
async def create_group_segment(
    group_id: str,
    data: SegmentCreate,
    user=Depends(get_current_user)
):
    """
    手动创建片段（通常为单字归属于某单支）

    Body:
    - source_image_id: 源图像ID
    - segment_type: slip 或 char
    - bbox_x, bbox_y, bbox_width, bbox_height: 边界框
    - parent_segment_id: 父片段ID（可选，用于字符归属于单支）
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 验证 source_image_id 属于该组
    source_img_url = f"{_base_url()}/rest/v1/source_images"
    source_img_params = {"id": f"eq.{data.source_image_id}", "group_id": f"eq.{group_id}"}
    source_img_resp = requests.get(source_img_url, headers=_auth_headers(), params=source_img_params)
    if source_img_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证源图像失败：{source_img_resp.status_code} {source_img_resp.text[:200]}"
        )
    source_img_data = source_img_resp.json() or []
    if not source_img_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"源图像不存在或不属于该组：{data.source_image_id}"
        )

    # 获取该图像同类型的最大 segment_index
    max_index_url = f"{_base_url()}/rest/v1/segments"
    max_index_params = {
        "source_image_id": f"eq.{data.source_image_id}",
        "segment_type": f"eq.{data.segment_type}",
        "select": "segment_index",
        "order": "segment_index.desc",
        "limit": "1"
    }
    max_index_resp = requests.get(max_index_url, headers=_auth_headers(), params=max_index_params)
    next_index = 0
    if max_index_resp.status_code == 200 and max_index_resp.json():
        next_index = (max_index_resp.json()[0].get("segment_index", 0) or 0) + 1

    # 创建片段记录（不涉及 Storage，因为是手动标注）
    segment_row = {
        "source_image_id": data.source_image_id,
        "image_id": data.source_image_id,  # 对于简牍图像，image_id 同 source_image_id
        "segment_type": data.segment_type,
        "segment_index": next_index,
        "bbox_x": data.bbox_x,
        "bbox_y": data.bbox_y,
        "bbox_width": data.bbox_width,
        "bbox_height": data.bbox_height,
        "validated": False,
    }
    if data.parent_segment_id:
        segment_row["parent_segment_id"] = data.parent_segment_id

    insert_url = f"{_base_url()}/rest/v1/segments"
    insert_headers = _auth_headers()
    insert_headers["Prefer"] = "return=representation"

    resp = requests.post(insert_url, headers=insert_headers, json=segment_row)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建片段失败：{resp.status_code} {resp.text[:200]}"
        )

    result = resp.json()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建片段失败，Supabase 返回数据为空"
        )

    return _parse_segment_row(result[0])


@router.put("/{group_id}/segments/{segment_id}", response_model=SegmentResponse)
async def update_group_segment(
    group_id: str,
    segment_id: str,
    data: SegmentUpdate,
    user=Depends(get_current_user)
):
    """
    更新片段的边界框或验证状态

    Body (all optional):
    - bbox_x, bbox_y, bbox_width, bbox_height: 边界框坐标
    - validated: 是否已验证
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 验证 segment 属于该组（通过 source_images 连接）
    seg_url = f"{_base_url()}/rest/v1/segments"
    seg_params = {"id": f"eq.{segment_id}"}
    seg_resp = requests.get(seg_url, headers=_auth_headers(), params=seg_params)
    if seg_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询片段失败：{seg_resp.status_code} {seg_resp.text[:200]}"
        )
    seg_data = seg_resp.json() or []
    if not seg_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"片段不存在：{segment_id}"
        )

    seg_row = seg_data[0]
    source_image_id = seg_row.get("source_image_id")

    # 验证 source_image 属于该组
    img_url = f"{_base_url()}/rest/v1/source_images"
    img_params = {"id": f"eq.{source_image_id}", "group_id": f"eq.{group_id}"}
    img_resp = requests.get(img_url, headers=_auth_headers(), params=img_params)
    if img_resp.status_code >= 400 or not img_resp.json():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"片段不属于该图像组：{segment_id}"
        )

    # 构建更新数据
    update_data = {}
    if data.bbox_x is not None:
        update_data["bbox_x"] = data.bbox_x
    if data.bbox_y is not None:
        update_data["bbox_y"] = data.bbox_y
    if data.bbox_width is not None:
        update_data["bbox_width"] = data.bbox_width
    if data.bbox_height is not None:
        update_data["bbox_height"] = data.bbox_height
    if data.validated is not None:
        update_data["validated"] = data.validated

    if not update_data:
        return _parse_segment_row(seg_row)

    # 执行更新
    update_url = f"{_base_url()}/rest/v1/segments"
    update_headers = _auth_headers()
    update_headers["Prefer"] = "return=representation"
    update_params = {"id": f"eq.{segment_id}"}

    update_resp = requests.patch(update_url, headers=update_headers, params=update_params, json=update_data)
    if update_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新片段失败：{update_resp.status_code} {update_resp.text[:200]}"
        )

    result = update_resp.json()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新片段失败，Supabase 返回数据为空"
        )

    return _parse_segment_row(result[0])


@router.delete("/{group_id}/segments/{segment_id}")
async def delete_group_segment(
    group_id: str,
    segment_id: str,
    user=Depends(get_current_user)
):
    """
    删除片段
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 验证 segment 属于该组
    seg_url = f"{_base_url()}/rest/v1/segments"
    seg_params = {"id": f"eq.{segment_id}"}
    seg_resp = requests.get(seg_url, headers=_auth_headers(), params=seg_params)
    if seg_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询片段失败：{seg_resp.status_code} {seg_resp.text[:200]}"
        )
    seg_data = seg_resp.json() or []
    if not seg_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"片段不存在：{segment_id}"
        )

    seg_row = seg_data[0]
    source_image_id = seg_row.get("source_image_id")

    # 验证 source_image 属于该组
    img_url = f"{_base_url()}/rest/v1/source_images"
    img_params = {"id": f"eq.{source_image_id}", "group_id": f"eq.{group_id}"}
    img_resp = requests.get(img_url, headers=_auth_headers(), params=img_params)
    if img_resp.status_code >= 400 or not img_resp.json():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"片段不属于该图像组：{segment_id}"
        )

    # 删除片段记录
    del_url = f"{_base_url()}/rest/v1/segments"
    del_params = {"id": f"eq.{segment_id}"}
    del_resp = requests.delete(del_url, headers=_auth_headers(), params=del_params)
    if del_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"删除片段失败：{del_resp.status_code} {del_resp.text[:200]}"
        )

    return {"message": "Segment deleted", "segment_id": segment_id, "group_id": group_id}


@router.post("/{group_id}/segments/batch-delete")
async def batch_delete_group_segments(
    group_id: str,
    request: BatchDeleteRequest,
    user=Depends(get_current_user)
):
    """
    批量删除片段

    Body:
    - segment_ids: 要删除的片段ID列表
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    results = []
    errors = []

    for segment_id in request.segment_ids:
        try:
            # 验证 segment 属于该组
            seg_url = f"{_base_url()}/rest/v1/segments"
            seg_params = {"id": f"eq.{segment_id}"}
            seg_resp = requests.get(seg_url, headers=_auth_headers(), params=seg_params)
            if seg_resp.status_code >= 400:
                errors.append({"segment_id": segment_id, "error": f"查询失败：{seg_resp.status_code}"})
                continue

            seg_data = seg_resp.json() or []
            if not seg_data:
                errors.append({"segment_id": segment_id, "error": "片段不存在"})
                continue

            source_image_id = seg_data[0].get("source_image_id")

            # 验证 source_image 属于该组
            img_url = f"{_base_url()}/rest/v1/source_images"
            img_params = {"id": f"eq.{source_image_id}", "group_id": f"eq.{group_id}"}
            img_resp = requests.get(img_url, headers=_auth_headers(), params=img_params)
            if img_resp.status_code >= 400 or not img_resp.json():
                errors.append({"segment_id": segment_id, "error": "片段不属于该图像组"})
                continue

            # 删除片段记录
            del_url = f"{_base_url()}/rest/v1/segments"
            del_params = {"id": f"eq.{segment_id}"}
            del_resp = requests.delete(del_url, headers=_auth_headers(), params=del_params)
            if del_resp.status_code >= 400:
                errors.append({"segment_id": segment_id, "error": f"删除失败：{del_resp.status_code}"})
            else:
                results.append({"segment_id": segment_id, "status": "success"})
        except Exception as e:
            errors.append({"segment_id": segment_id, "error": str(e)})

    return {
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors
    }


@router.put("/{group_id}/segments/validate")
async def validate_group_segments(
    group_id: str,
    request: ValidateSegmentsRequest,
    user=Depends(get_current_user)
):
    """
    标记片段为已验证

    Body (二选一):
    - image_id: 图像ID（验证该图像所有片段）
    - segment_ids: 片段ID列表
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    if not request.image_id and not request.segment_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供 image_id 或 segment_ids 之一"
        )

    updated_count = 0

    if request.image_id:
        # 验证 image_id 属于该组
        img_url = f"{_base_url()}/rest/v1/source_images"
        img_params = {"id": f"eq.{request.image_id}", "group_id": f"eq.{group_id}"}
        img_resp = requests.get(img_url, headers=_auth_headers(), params=img_params)
        if img_resp.status_code >= 400 or not img_resp.json():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"图像不存在或不属于该组：{request.image_id}"
            )

        # 验证该图像所有片段
        seg_url = f"{_base_url()}/rest/v1/segments"
        seg_params = {"source_image_id": f"eq.{request.image_id}"}
        seg_resp = requests.get(seg_url, headers=_auth_headers(), params=seg_params)
        if seg_resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询片段失败：{seg_resp.status_code} {seg_resp.text[:200]}"
            )

        segment_ids = [seg["id"] for seg in seg_resp.json() or []]
        if not segment_ids:
            return {"message": "No segments to validate", "updated_count": 0}

        # 批量更新
        update_url = f"{_base_url()}/rest/v1/segments"
        update_headers = _auth_headers()
        update_headers["Prefer"] = "return=representation"

        for sid in segment_ids:
            update_params = {"id": f"eq.{sid}"}
            upd_resp = requests.patch(update_url, headers=update_headers, params=update_params, json={"validated": True})
            if upd_resp.status_code < 400:
                updated_count += 1

    elif request.segment_ids:
        # 逐个验证 segment 属于该组
        for segment_id in request.segment_ids:
            seg_url = f"{_base_url()}/rest/v1/segments"
            seg_params = {"id": f"eq.{segment_id}"}
            seg_resp = requests.get(seg_url, headers=_auth_headers(), params=seg_params)
            if seg_resp.status_code >= 400 or not seg_resp.json():
                continue

            seg_row = seg_resp.json()[0]
            source_image_id = seg_row.get("source_image_id")

            # 验证 source_image 属于该组
            img_url = f"{_base_url()}/rest/v1/source_images"
            img_params = {"id": f"eq.{source_image_id}", "group_id": f"eq.{group_id}"}
            img_resp = requests.get(img_url, headers=_auth_headers(), params=img_params)
            if img_resp.status_code >= 400 or not img_resp.json():
                continue

            # 更新验证状态
            update_url = f"{_base_url()}/rest/v1/segments"
            update_params = {"id": f"eq.{segment_id}"}
            upd_resp = requests.patch(update_url, headers=_auth_headers(), params=update_params, json={"validated": True})
            if upd_resp.status_code < 400:
                updated_count += 1

    return {"message": "Segments validated", "updated_count": updated_count}


@router.get("/{group_id}/validation-status", response_model=ValidationStatusResponse)
async def get_validation_status(
    group_id: str,
    user=Depends(get_current_user)
):
    """
    获取图像组的验证进度

    Returns:
    - total_images: 组内总图像数
    - validated_images: 已验证的图像数（所有片段都验证的图像）
    - slips_validated: 已验证的单支数
    - chars_validated: 已验证的字数
    """
    _require_supabase_config()
    user_id = _get_user_id(user)

    # 验证组存在且属于当前用户
    _ensure_group_exists_and_owned(group_id, user_id)

    # 获取组内所有源图像
    images_url = f"{_base_url()}/rest/v1/source_images"
    images_params = {"group_id": f"eq.{group_id}", "select": "id"}
    images_resp = requests.get(images_url, headers=_auth_headers(), params=images_params)
    if images_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取组内图像失败：{images_resp.status_code} {images_resp.text[:200]}"
        )
    image_ids = [img["id"] for img in images_resp.json() or []]
    total_images = len(image_ids)

    if not image_ids:
        return ValidationStatusResponse(
            total_images=0,
            validated_images=0,
            slips_validated=0,
            chars_validated=0
        )

    # 获取所有片段的验证状态
    segment_ids_str = ",".join(image_ids)
    seg_url = f"{_base_url()}/rest/v1/segments"
    seg_params = {"source_image_id": f"in.({segment_ids_str})"}
    seg_resp = requests.get(seg_url, headers=_auth_headers(), params=seg_params)
    if seg_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取片段列表失败：{seg_resp.status_code} {seg_resp.text[:200]}"
        )

    segments = seg_resp.json() or []

    # 统计已验证的单支和字符
    slips_validated = 0
    chars_validated = 0
    validated_images_set = set()

    for seg in segments:
        if seg.get("validated", False):
            if seg.get("segment_type") == "slip":
                slips_validated += 1
                validated_images_set.add(seg.get("source_image_id"))
            elif seg.get("segment_type") == "char":
                chars_validated += 1

    # 验证图像：所有片段都验证的图像
    # 对于每个图像，检查它的所有片段是否都已验证
    validated_images = 0
    for img_id in image_ids:
        img_segments = [s for s in segments if s.get("source_image_id") == img_id]
        if img_segments and all(s.get("validated", False) for s in img_segments):
            validated_images += 1

    return ValidationStatusResponse(
        total_images=total_images,
        validated_images=validated_images,
        slips_validated=slips_validated,
        chars_validated=chars_validated
    )
