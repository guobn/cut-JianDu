from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.config import settings
from app.models.detection import BoundingBox
from app.models.response import error_response


class SupabaseError(Exception):
    """Supabase 服务基础异常类"""
    def __init__(self, message: str, error_code: str = "SUPABASE_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def to_error_response(self) -> Dict[str, Any]:
        """转换为标准错误响应"""
        return error_response(
            error_code=self.error_code,
            error_message=self.message,
            suggested_solution="请检查 Supabase 配置和网络连接"
        )


class SupabaseStorageError(SupabaseError):
    """Supabase Storage 操作异常"""
    def __init__(self, message: str, error_code: str = "SUPABASE_STORAGE_ERROR"):
        super().__init__(message, error_code)

    def to_error_response(self) -> Dict[str, Any]:
        return error_response(
            error_code=self.error_code,
            error_message=self.message,
            suggested_solution="请检查 Storage bucket 配置和文件路径"
        )


class SupabaseDatabaseError(SupabaseError):
    """Supabase 数据库操作异常"""
    def __init__(self, message: str, error_code: str = "SUPABASE_DATABASE_ERROR"):
        super().__init__(message, error_code)

    def to_error_response(self) -> Dict[str, Any]:
        return error_response(
            error_code=self.error_code,
            error_message=self.message,
            suggested_solution="请检查数据库表结构和权限配置"
        )


class SupabaseConfigError(SupabaseError):
    """Supabase 配置异常"""
    def __init__(self, message: str, error_code: str = "SUPABASE_CONFIG_ERROR"):
        super().__init__(message, error_code)

    def to_error_response(self) -> Dict[str, Any]:
        return error_response(
            error_code=self.error_code,
            error_message=self.message,
            suggested_solution="请在后端 .env 中正确配置 SUPABASE_URL 和 SUPABASE_SERVICE_KEY"
        )


def _require_supabase_config() -> None:
    """确保 Supabase 相关配置存在。"""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise SupabaseConfigError("Supabase 配置缺失，请在后端 .env 中设置 SUPABASE_URL 与 SUPABASE_SERVICE_KEY")


def _base_url() -> str:
    return settings.supabase_url.rstrip("/")


def _auth_headers() -> Dict[str, str]:
    """
    Supabase REST / Storage 通用请求头（使用 service key）。
    """
    _require_supabase_config()
    return {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }


def build_segments_storage_key(
    image_id: str,
    segment_type: str,
    segment_index: int,
    output_format: str = "png",
    dataset_id: str = "default",
    user_id: str = "anonymous",
    slip_number: Optional[str] = None,
) -> str:
    """
    生成切割结果在 Supabase Storage 中的 key（不含 bucket 名）。
    严格按类型划分三个子目录：
        - 原图：   {user_id}/img/...
        - 单支：   {user_id}/slip/...
        - 单字：   {user_id}/char/...

    此函数用于「切割结果」上传，因此这里只区分 slip / char 两类：
        slip: {user_id}/slip/{slip_number}_slip_{index:04d}.{ext}
        char: {user_id}/char/{slip_number}_char_{index:04d}.{ext}
    当 slip_number 为空时回退到原有命名方式。
    """
    safe_segment_type = "char" if segment_type == "char" else "slip"
    if slip_number:
        filename = f"{slip_number}_{safe_segment_type}_{segment_index:04d}.{output_format}"
    else:
        filename = f"{safe_segment_type}_{image_id}_{segment_index:04d}.{output_format}"
    key = f"{user_id}/{safe_segment_type}/{filename}"
    return key


def build_public_url(storage_key: str) -> str:
    """
    构造公开访问 URL（与 Supabase 控制台展示形式一致）。
    """
    base = settings.supabase_url.rstrip("/")
    bucket = settings.supabase_segments_bucket
    return f"{base}/storage/v1/object/public/{bucket}/{storage_key}"


def upload_segment_to_storage(
    local_path: Path,
    storage_key: str,
    enable_rollback: bool = True
) -> None:
    """
    将本地切割结果上传到 Supabase Storage 的 segments bucket。

    Args:
        local_path: 本地文件路径
        storage_key: Storage 中的对象 key
        enable_rollback: 是否启用上传失败时的本地文件回滚（删除临时文件）

    Raises:
        SupabaseStorageError: 上传失败时抛出，包含标准错误响应
    """
    _require_supabase_config()
    bucket = settings.supabase_segments_bucket
    url = f"{_base_url()}/storage/v1/object/{bucket}/{storage_key}"

    for attempt in range(3):
        try:
            with local_path.open("rb") as f:
                headers = _auth_headers()
                headers.pop("Content-Type", None)
                headers["x-upsert"] = "true"

                resp = requests.post(url, headers=headers, data=f, timeout=120)
                if resp.status_code >= 400:
                    raise SupabaseStorageError(
                        f"上传文件到 Supabase Storage 失败：{resp.status_code} {resp.text}",
                        "SUPABASE_STORAGE_UPLOAD_FAILED"
                    )
                return
        except SupabaseStorageError:
            raise
        except Exception as e:
            if attempt == 2:
                if enable_rollback and local_path.exists():
                    try:
                        os.remove(local_path)
                    except OSError as remove_err:
                        pass
                raise SupabaseStorageError(
                    f"上传文件失败 (已重试 3 次): {str(e)}",
                    "SUPABASE_STORAGE_UPLOAD_FAILED"
                )
            import time
            time.sleep(1.5)


def download_file_from_storage(storage_key: str) -> Optional[bytes]:
    """
    从 Supabase Storage 下载文件内容。
    先试 authenticated 端点（service key 可绕过 RLS），404 时再试 public URL（公开 bucket）。

    Returns:
        文件内容的 bytes，如果文件不存在返回 None

    Raises:
        SupabaseStorageError: 其他错误时抛出
    """
    try:
        _require_supabase_config()
        bucket = settings.supabase_segments_bucket
        headers = _auth_headers()
        headers.pop("Content-Type", None)

        url_auth = f"{_base_url()}/storage/v1/object/authenticated/{bucket}/{storage_key}"
        resp = requests.get(url_auth, headers=headers, timeout=60)

        if resp.status_code == 200:
            return resp.content
        if resp.status_code != 404:
            raise SupabaseStorageError(
                f"从 Supabase 下载文件失败：{resp.status_code} {resp.text[:200]}",
                "SUPABASE_STORAGE_DOWNLOAD_FAILED"
            )

        url_public = f"{_base_url()}/storage/v1/object/public/{bucket}/{storage_key}"
        resp_public = requests.get(url_public, timeout=60)

        if resp_public.status_code == 200:
            return resp_public.content
        if resp_public.status_code == 404:
            return None

        raise SupabaseStorageError(
            f"从 Supabase 下载文件失败：{resp_public.status_code} {resp_public.text[:200]}",
            "SUPABASE_STORAGE_DOWNLOAD_FAILED"
        )
    except SupabaseStorageError:
        raise
    except Exception as e:
        raise SupabaseStorageError(
            f"下载文件时发生异常：{str(e)}",
            "SUPABASE_STORAGE_DOWNLOAD_FAILED"
        )


def delete_segment_from_storage(storage_key: str) -> None:
    """
    从 Supabase Storage 删除切割结果文件。

    Raises:
        SupabaseStorageError: 删除失败时抛出
    """
    try:
        _require_supabase_config()
        bucket = settings.supabase_segments_bucket

        url = f"{_base_url()}/storage/v1/object/{bucket}/{storage_key}"
        headers = _auth_headers()
        headers.pop("Content-Type", None)

        resp = requests.delete(url, headers=headers)
        if resp.status_code >= 400 and resp.status_code != 404:
            raise SupabaseStorageError(
                f"删除文件失败：{resp.status_code} {resp.text}",
                "SUPABASE_STORAGE_DELETE_FAILED"
            )
    except SupabaseStorageError:
        raise
    except Exception as e:
        raise SupabaseStorageError(
            f"删除文件时发生异常：{str(e)}",
            "SUPABASE_STORAGE_DELETE_FAILED"
        )


def list_storage_objects(prefix: str, limit: int = 50, offset: int = 0) -> list:
    """
    列出 Supabase Storage 中指定前缀的对象。

    Raises:
        SupabaseStorageError: 列出失败时抛出
    """
    try:
        _require_supabase_config()
        bucket = settings.supabase_segments_bucket

        url = f"{_base_url()}/storage/v1/object/list/{bucket}"
        headers = _auth_headers()
        body = {
            "prefix": prefix,
            "limit": limit,
            "offset": offset,
            "sortBy": {"column": "created_at", "order": "desc"},
        }

        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code >= 400:
            raise SupabaseStorageError(
                f"列出 Storage 对象失败：{resp.status_code} {resp.text}",
                "SUPABASE_STORAGE_LIST_FAILED"
            )

        return resp.json() or []
    except SupabaseStorageError:
        raise
    except Exception as e:
        raise SupabaseStorageError(
            f"列出 Storage 对象时发生异常：{str(e)}",
            "SUPABASE_STORAGE_LIST_FAILED"
        )


def upsert_image_record(
    image_id: str,
    image_path: Path,
    width: Optional[int],
    height: Optional[int],
    dataset_id: str = "default",
) -> None:
    """
    确保 images 表中存在对应的原始图像记录。

    Raises:
        SupabaseDatabaseError: 写入失败时抛出
    """
    try:
        _require_supabase_config()

        row: Dict[str, Any] = {
            "id": image_id,
            "dataset_id": dataset_id,
            "filename": image_path.name,
            "storage_path": str(image_path),
            "width": width,
            "height": height,
        }

        url = f"{_base_url()}/rest/v1/images"
        headers = _auth_headers()
        headers["Prefer"] = "resolution=merge-duplicates"

        resp = requests.post(url, headers=headers, json=row)
        if resp.status_code >= 400:
            raise SupabaseDatabaseError(
                f"写入 images 记录失败：{resp.status_code} {resp.text}",
                "SUPABASE_DATABASE_UPSERT_FAILED"
            )
    except SupabaseDatabaseError:
        raise
    except Exception as e:
        raise SupabaseDatabaseError(
            f"写入 images 记录时发生异常：{str(e)}",
            "SUPABASE_DATABASE_UPSERT_FAILED"
        )


def insert_segment_record(
    *,
    image_id: str,
    bbox: BoundingBox,
    segment_index: int,
    segment_type: str,
    storage_key: str,
    region_width: int,
    region_height: int,
    dataset_id: str = "default",
    user_id: Optional[str] = None,
    source_image_id: Optional[str] = None,
    parent_segment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    在 segments 表中插入一条切割结果记录，返回插入后的行数据。

    Raises:
        SupabaseDatabaseError: 插入失败时抛出
    """
    try:
        _require_supabase_config()

        row: Dict[str, Any] = {
            "image_id": image_id,
            "dataset_id": dataset_id,
            "segment_index": segment_index,
            "segment_type": segment_type,
            "storage_path": storage_key,
            "bbox_x": bbox.x,
            "bbox_y": bbox.y,
            "bbox_width": bbox.width,
            "bbox_height": bbox.height,
            "width": region_width,
            "height": region_height,
        }

        if user_id is not None:
            row["user_id"] = user_id
        if source_image_id is not None:
            row["source_image_id"] = source_image_id
        if parent_segment_id is not None:
            row["parent_segment_id"] = parent_segment_id

        url = f"{_base_url()}/rest/v1/segments"
        headers = _auth_headers()
        headers["Prefer"] = "return=representation"

        resp = requests.post(url, headers=headers, json=row)
        if resp.status_code >= 400:
            raise SupabaseDatabaseError(
                f"插入 segments 记录失败：{resp.status_code} {resp.text}",
                "SUPABASE_DATABASE_INSERT_FAILED"
            )

        data = resp.json()
        if not data:
            raise SupabaseDatabaseError(
                "插入 segments 记录失败，Supabase 返回数据为空",
                "SUPABASE_DATABASE_INSERT_FAILED"
            )

        return data[0]
    except SupabaseDatabaseError:
        raise
    except Exception as e:
        raise SupabaseDatabaseError(
            f"插入 segments 记录时发生异常：{str(e)}",
            "SUPABASE_DATABASE_INSERT_FAILED"
        )


def insert_slip_metadata(
    *,
    image_id: str,
    slip_number: str,
    user_id: str,
    material: Optional[str] = None,
    dimensions: Optional[str] = None,
    preservation_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    在 slip_image_metadata 表中插入简牍元数据记录。

    Raises:
        SupabaseDatabaseError: 插入失败时抛出
    """
    try:
        _require_supabase_config()

        row: Dict[str, Any] = {
            "image_id": image_id,
            "slip_number": slip_number,
            "user_id": user_id,
        }

        if material is not None:
            row["material"] = material
        if dimensions is not None:
            row["dimensions"] = dimensions
        if preservation_state is not None:
            row["preservation_state"] = preservation_state

        url = f"{_base_url()}/rest/v1/slip_image_metadata"
        headers = _auth_headers()
        headers["Prefer"] = "return=representation"

        resp = requests.post(url, headers=headers, json=row)
        if resp.status_code >= 400:
            raise SupabaseDatabaseError(
                f"插入 slip_image_metadata 记录失败：{resp.status_code} {resp.text}",
                "SUPABASE_DATABASE_INSERT_FAILED"
            )

        data = resp.json()
        if not data:
            raise SupabaseDatabaseError(
                "插入 slip_image_metadata 记录失败，Supabase 返回数据为空",
                "SUPABASE_DATABASE_INSERT_FAILED"
            )

        return data[0]
    except SupabaseDatabaseError:
        raise
    except Exception as e:
        raise SupabaseDatabaseError(
            f"插入 slip_image_metadata 记录时发生异常：{str(e)}",
            "SUPABASE_DATABASE_INSERT_FAILED"
        )


def get_slip_metadata(image_id: str) -> Optional[Dict[str, Any]]:
    """
    查询指定图像的简牍元数据。

    Raises:
        SupabaseDatabaseError: 查询失败时抛出
    """
    try:
        _require_supabase_config()

        url = f"{_base_url()}/rest/v1/slip_image_metadata"
        headers = _auth_headers()
        params = {"image_id": f"eq.{image_id}"}

        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code >= 400:
            raise SupabaseDatabaseError(
                f"查询 slip_image_metadata 失败：{resp.status_code} {resp.text}",
                "SUPABASE_DATABASE_QUERY_FAILED"
            )

        data = resp.json()
        return data[0] if data else None
    except SupabaseDatabaseError:
        raise
    except Exception as e:
        raise SupabaseDatabaseError(
            f"查询 slip_image_metadata 时发生异常：{str(e)}",
            "SUPABASE_DATABASE_QUERY_FAILED"
        )
