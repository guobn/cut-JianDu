"""
缓存管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.models.groups import ProcessingCacheCreate, ProcessingCacheResponse
from app.core.auth import get_current_user
from app.services.supabase_service import _base_url, _auth_headers

import requests

router = APIRouter(prefix="/api/cache", tags=["cache"])


def _get_current_user_id(user: Any) -> str:
    """从 user 对象中提取 user_id"""
    if hasattr(user, 'id'):
        return str(user.id)
    if isinstance(user, dict) and 'id' in user:
        return str(user['id'])
    return str(user)


@router.post("/save", response_model=ProcessingCacheResponse)
async def save_cache(
    data: ProcessingCacheCreate,
    user=Depends(get_current_user)
):
    """保存缓存记录

    将处理结果缓存到 Supabase processing_cache 表。
    如果已存在相同的 source_image_id 和 cache_type，则更新现有记录。
    """
    user_id = _get_current_user_id(user)

    # 构建缓存记录
    cache_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    row: Dict[str, Any] = {
        "id": str(cache_id),
        "source_image_id": str(data.source_image_id),
        "cache_type": data.cache_type,
        "cache_url": data.cache_url,
        "cache_meta": data.cache_meta or {},
        "expires_at": expires_at.isoformat(),
    }

    url = f"{_base_url()}/rest/v1/processing_cache"
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"

    # 使用 upsert 语义，如果存在则更新（基于 unique 约束）
    headers["Prefer"] = "return=representation,resolution=merge-duplicates"

    resp = requests.post(url, headers=headers, json=row)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CACHE_SAVE_FAILED",
                "error_message": f"保存缓存记录失败：{resp.status_code} {resp.text[:200]}",
                "suggested_solution": "请稍后重试"
            }
        )

    result_data = resp.json()
    if not result_data:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CACHE_SAVE_FAILED",
                "error_message": "保存缓存记录失败，Supabase 返回数据为空",
                "suggested_solution": "请稍后重试"
            }
        )

    saved_row = result_data[0]

    return {
        "id": saved_row["id"],
        "source_image_id": saved_row["source_image_id"],
        "cache_type": saved_row["cache_type"],
        "cache_url": saved_row["cache_url"],
        "cache_meta": saved_row.get("cache_meta", {}),
        "expires_at": saved_row["expires_at"],
        "created_at": saved_row["created_at"]
    }


@router.get("/{source_image_id}/{cache_type}", response_model=ProcessingCacheResponse)
async def get_cache(
    source_image_id: str,
    cache_type: str,
    user=Depends(get_current_user)
):
    """获取缓存

    从 Supabase processing_cache 表查询指定 source_image_id 和 cache_type 的缓存记录。
    同时检查 expires_at，如果已过期则返回 404。
    """
    url = f"{_base_url()}/rest/v1/processing_cache"
    headers = _auth_headers()

    # 查询条件：source_image_id 和 cache_type 匹配
    params = {
        "source_image_id": f"eq.{source_image_id}",
        "cache_type": f"eq.{cache_type}",
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CACHE_QUERY_FAILED",
                "error_message": f"查询缓存失败：{resp.status_code} {resp.text[:200]}",
                "suggested_solution": "请稍后重试"
            }
        )

    result_data = resp.json()
    if not result_data:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "CACHE_NOT_FOUND",
                "error_message": "缓存不存在",
                "suggested_solution": "请检查 source_image_id 和 cache_type 是否正确"
            }
        )

    cached_row = result_data[0]

    # 检查是否过期
    expires_at_str = cached_row.get("expires_at")
    if expires_at_str:
        # 处理 ISO 格式时间字符串
        expires_at_str = expires_at_str.replace('Z', '+00:00')
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
            # 兼容不同格式
            expires_at = datetime.strptime(expires_at_str[:19], "%Y-%m-%dT%H:%M:%S")
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "CACHE_EXPIRED",
                    "error_message": "缓存已过期",
                    "suggested_solution": "请重新生成缓存"
                }
            )

    return {
        "id": cached_row["id"],
        "source_image_id": cached_row["source_image_id"],
        "cache_type": cached_row["cache_type"],
        "cache_url": cached_row["cache_url"],
        "cache_meta": cached_row.get("cache_meta", {}),
        "expires_at": cached_row["expires_at"],
        "created_at": cached_row["created_at"]
    }


@router.delete("/{source_image_id}")
async def delete_cache(
    source_image_id: str,
    user=Depends(get_current_user)
):
    """删除缓存

    从 Supabase processing_cache 表删除指定 source_image_id 的所有缓存记录。
    返回删除的记录数量。
    """
    url = f"{_base_url()}/rest/v1/processing_cache"
    headers = _auth_headers()

    # 删除条件：source_image_id 匹配
    params = {
        "source_image_id": f"eq.{source_image_id}",
    }

    resp = requests.delete(url, headers=headers, params=params)
    if resp.status_code >= 400 and resp.status_code != 404:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CACHE_DELETE_FAILED",
                "error_message": f"删除缓存失败：{resp.status_code} {resp.text[:200]}",
                "suggested_solution": "请稍后重试"
            }
        )

    return {"message": f"Cache deleted for source_image_id: {source_image_id}"}
