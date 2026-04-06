from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.supabase_service import _require_supabase_config, _base_url, _auth_headers, get_slip_metadata
from app.core.auth import get_current_user
import requests

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


class SegmentMetadataResponse(BaseModel):
    """切割结果元数据响应"""
    segment_id: str
    image_id: str
    segment_index: int
    segment_type: str
    storage_path: str
    public_url: str
    width: int
    height: int
    created_at: datetime
    metadata: Optional[dict] = None  # segment_metadata 表的内容（如果有）
    slip_number: Optional[str] = None  # 简牍编号（来自 slip_image_metadata 表）


class MetadataUpdateRequest(BaseModel):
    """元数据更新请求"""
    title: Optional[str] = None
    content_description: Optional[str] = None
    event_type: Optional[str] = None
    event_date: Optional[str] = None  # YYYY-MM-DD
    place: Optional[str] = None
    people: Optional[list] = None
    extra: Optional[dict] = None


@router.get("/segments", response_model=List[SegmentMetadataResponse])
async def list_segments(
    image_id: Optional[str] = None,
    segment_type: Optional[str] = None,
    parent_segment_id: Optional[str] = None,
    source_image_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_current_user),
):
    """
    查询切割结果列表（带元数据）

    Args:
        image_id: 过滤特定原图
        segment_type: 过滤类型 ('slip' 或 'char')
        limit: 返回数量
        offset: 偏移量
    """
    try:
        _require_supabase_config()

        # 构建查询 URL
        url = f"{_base_url()}/rest/v1/segments"
        params = {
            "limit": limit,
            "offset": offset,
            "order": "created_at.desc",
        }

        if image_id:
            params["image_id"] = f"eq.{image_id}"
        if segment_type:
            params["segment_type"] = f"eq.{segment_type}"
        if parent_segment_id:
            params["parent_segment_id"] = f"eq.{parent_segment_id}"
        if source_image_id:
            params["source_image_id"] = f"eq.{source_image_id}"

        user_id = user.get("id") if isinstance(user, dict) else "anonymous"
        # segments 表未单独存 user_id，这里按 storage_path 的命名规则 <user_id>/... 做过滤
        params["storage_path"] = f"like.{user_id}/%"

        headers = _auth_headers()
        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code >= 400:
            raise HTTPException(
                status_code=resp.status_code,
                detail={
                    "error_code": "SEGMENTS_QUERY_FAILED",
                    "error_message": f"查询 segments 失败：{resp.text}",
                    "suggested_solution": "请稍后重试"
                }
            )

        segments = resp.json()
        if not segments:
            return []

        # 批量查询元数据（使用 segment_id IN (...)
        segment_ids = [str(s["id"]) for s in segments]
        metadata_map = {}

        if segment_ids:
            metadata_url = f"{_base_url()}/rest/v1/segment_metadata"
            # PostgREST 的 in 查询格式：in.(id1,id2,id3)
            segment_ids_str = ",".join(segment_ids)
            metadata_params = {
                "segment_id": f"in.({segment_ids_str})"
            }
            metadata_resp = requests.get(metadata_url, headers=headers, params=metadata_params)

            if metadata_resp.status_code == 200:
                metadata_list = metadata_resp.json()
                for meta in metadata_list:
                    metadata_map[str(meta["segment_id"])] = meta

        # 组装返回数据（包含 public_url）
        from app.config import settings
        from app.services.supabase_service import build_public_url

        # 批量查询简牍编号
        image_ids = list(set(seg["image_id"] for seg in segments))
        slip_number_map = {}
        try:
            slip_meta_url = f"{_base_url()}/rest/v1/slip_image_metadata"
            slip_meta_params = {
                "image_id": f"in.({','.join(image_ids)})",
                "select": "image_id,slip_number",
            }
            slip_resp = requests.get(slip_meta_url, headers=headers, params=slip_meta_params)
            if slip_resp.status_code == 200:
                for item in slip_resp.json():
                    slip_number_map[item["image_id"]] = item.get("slip_number")
        except Exception:
            pass  # 查询失败不影响主流程

        results = []
        for seg in segments:
            public_url = build_public_url(seg["storage_path"])
            seg_id_str = str(seg["id"])
            metadata = metadata_map.get(seg_id_str)

            # 处理日期格式（Supabase 返回的可能是 ISO 字符串）
            created_at_str = seg.get("created_at", "")
            try:
                if isinstance(created_at_str, str):
                    # 处理各种可能的日期格式
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str.replace("Z", "+00:00")
                    created_at = datetime.fromisoformat(created_at_str)
                else:
                    created_at = datetime.now()
            except Exception:
                created_at = datetime.now()

            results.append(SegmentMetadataResponse(
                segment_id=seg_id_str,
                image_id=seg["image_id"],
                segment_index=seg["segment_index"],
                segment_type=seg["segment_type"],
                storage_path=seg["storage_path"],
                public_url=public_url,
                width=seg.get("width", 0),
                height=seg.get("height", 0),
                created_at=created_at,
                metadata=metadata,
                slip_number=slip_number_map.get(seg["image_id"]),
            ))

        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "SEGMENTS_QUERY_FAILED",
                "error_message": f"查询失败：{str(e)}",
                "suggested_solution": "请稍后重试"
            }
        )


@router.get("/segments/{segment_id}", response_model=SegmentMetadataResponse)
async def get_segment(segment_id: str):
    """获取单个切割结果及其元数据"""
    try:
        _require_supabase_config()

        # 查询 segment
        url = f"{_base_url()}/rest/v1/segments"
        params = {"id": f"eq.{segment_id}"}
        headers = _auth_headers()

        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code >= 400 or not resp.json():
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "SEGMENT_NOT_FOUND",
                    "error_message": "切割结果不存在",
                    "suggested_solution": "请检查 segment_id 是否正确"
                }
            )

        seg = resp.json()[0]

        # 查询元数据
        metadata_url = f"{_base_url()}/rest/v1/segment_metadata"
        metadata_params = {"segment_id": f"eq.{segment_id}"}
        metadata_resp = requests.get(metadata_url, headers=headers, params=metadata_params)

        metadata = None
        if metadata_resp.status_code == 200 and metadata_resp.json():
            metadata = metadata_resp.json()[0]

        from app.services.supabase_service import build_public_url
        public_url = build_public_url(seg["storage_path"])

        # 查询简牍编号
        slip_number = None
        try:
            slip_meta = get_slip_metadata(seg["image_id"])
            if slip_meta:
                slip_number = slip_meta.get("slip_number")
        except Exception:
            pass

        # 处理日期格式
        created_at_str = seg.get("created_at", "")
        try:
            if isinstance(created_at_str, str):
                if created_at_str.endswith("Z"):
                    created_at_str = created_at_str.replace("Z", "+00:00")
                created_at = datetime.fromisoformat(created_at_str)
            else:
                created_at = datetime.now()
        except Exception:
            created_at = datetime.now()

        return SegmentMetadataResponse(
            segment_id=str(seg["id"]),
            image_id=seg["image_id"],
            segment_index=seg["segment_index"],
            segment_type=seg["segment_type"],
            storage_path=seg["storage_path"],
            public_url=public_url,
            width=seg.get("width", 0),
            height=seg.get("height", 0),
            created_at=created_at,
            metadata=metadata,
            slip_number=slip_number,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "SEGMENT_QUERY_FAILED",
                "error_message": f"查询失败：{str(e)}",
                "suggested_solution": "请稍后重试"
            }
        )


@router.post("/segments/{segment_id}/metadata")
async def upsert_metadata(segment_id: str, request: MetadataUpdateRequest):
    """
    创建或更新切割结果的元数据
    """
    try:
        _require_supabase_config()

        # 先检查 segment 是否存在
        seg_url = f"{_base_url()}/rest/v1/segments"
        seg_params = {"id": f"eq.{segment_id}"}
        headers = _auth_headers()

        seg_resp = requests.get(seg_url, headers=headers, params=seg_params)
        if seg_resp.status_code >= 400 or not seg_resp.json():
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "SEGMENT_NOT_FOUND",
                    "error_message": "切割结果不存在",
                    "suggested_solution": "请检查 segment_id 是否正确"
                }
            )

        # 准备元数据字段
        metadata_row = {
            "segment_id": segment_id,
            "title": request.title,
            "content_description": request.content_description,
            "event_type": request.event_type,
            "event_date": request.event_date,
            "place": request.place,
            "people": request.people,
            "extra": request.extra,
            "updated_at": datetime.now().isoformat()
        }

        # 移除 None 值
        metadata_row = {k: v for k, v in metadata_row.items() if v is not None}

        # 检查是否已存在元数据
        meta_url = f"{_base_url()}/rest/v1/segment_metadata"
        meta_params = {"segment_id": f"eq.{segment_id}"}
        meta_resp = requests.get(meta_url, headers=headers, params=meta_params)

        if meta_resp.status_code == 200 and meta_resp.json():
            # 更新
            meta_id = meta_resp.json()[0]["id"]
            update_url = f"{_base_url()}/rest/v1/segment_metadata"
            update_params = {"id": f"eq.{meta_id}"}
            headers["Prefer"] = "return=representation"

            update_resp = requests.patch(update_url, headers=headers, params=update_params, json=metadata_row)
            if update_resp.status_code >= 400:
                raise HTTPException(
                    status_code=update_resp.status_code,
                    detail={
                        "error_code": "METADATA_UPDATE_FAILED",
                        "error_message": f"更新失败：{update_resp.text}",
                        "suggested_solution": "请稍后重试"
                    }
                )

            return {"message": "元数据已更新", "metadata": update_resp.json()[0] if update_resp.json() else None}
        else:
            # 新建
            headers["Prefer"] = "return=representation"
            create_resp = requests.post(meta_url, headers=headers, json=metadata_row)
            if create_resp.status_code >= 400:
                raise HTTPException(
                    status_code=create_resp.status_code,
                    detail={
                        "error_code": "METADATA_CREATE_FAILED",
                        "error_message": f"创建失败：{create_resp.text}",
                        "suggested_solution": "请稍后重试"
                    }
                )

            return {"message": "元数据已创建", "metadata": create_resp.json()[0] if create_resp.json() else None}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "METADATA_OPERATION_FAILED",
                "error_message": f"操作失败：{str(e)}",
                "suggested_solution": "请稍后重试"
            }
        )


@router.delete("/segments/{segment_id}")
async def delete_segment(segment_id: str):
    """
    删除切割结果（包括 Storage 文件和数据库记录）
    """
    try:
        _require_supabase_config()
        headers = _auth_headers()

        # 1. 查询 segment 信息（获取 storage_path）
        seg_url = f"{_base_url()}/rest/v1/segments"
        seg_params = {"id": f"eq.{segment_id}"}
        seg_resp = requests.get(seg_url, headers=headers, params=seg_params)

        if seg_resp.status_code >= 400 or not seg_resp.json():
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "SEGMENT_NOT_FOUND",
                    "error_message": "切割结果不存在",
                    "suggested_solution": "请检查 segment_id 是否正确"
                }
            )

        seg = seg_resp.json()[0]
        storage_path = seg.get("storage_path")

        # 2. 删除 Supabase Storage 中的文件
        if storage_path:
            from app.services.supabase_service import delete_segment_from_storage
            try:
                delete_segment_from_storage(storage_path)
            except Exception as e:
                # 文件删除失败不影响数据库删除（可能文件已不存在）
                print(f"警告：删除 Storage 文件失败：{e}")

        # 3. 删除 segment_metadata 记录（如果存在）
        meta_url = f"{_base_url()}/rest/v1/segment_metadata"
        meta_params = {"segment_id": f"eq.{segment_id}"}
        meta_resp = requests.get(meta_url, headers=headers, params=meta_params)

        if meta_resp.status_code == 200 and meta_resp.json():
            meta_id = meta_resp.json()[0]["id"]
            delete_meta_url = f"{_base_url()}/rest/v1/segment_metadata"
            delete_meta_params = {"id": f"eq.{meta_id}"}
            requests.delete(delete_meta_url, headers=headers, params=delete_meta_params)

        # 4. 删除 segments 记录
        delete_seg_url = f"{_base_url()}/rest/v1/segments"
        delete_seg_params = {"id": f"eq.{segment_id}"}
        delete_seg_resp = requests.delete(delete_seg_url, headers=headers, params=delete_seg_params)

        if delete_seg_resp.status_code >= 400:
            raise HTTPException(
                status_code=delete_seg_resp.status_code,
                detail={
                    "error_code": "SEGMENT_DELETE_FAILED",
                    "error_message": f"删除失败：{delete_seg_resp.text}",
                    "suggested_solution": "请稍后重试"
                }
            )

        return {"message": "切割结果已删除", "segment_id": segment_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "SEGMENT_DELETE_FAILED",
                "error_message": f"删除失败：{str(e)}",
                "suggested_solution": "请稍后重试"
            }
        )


@router.post("/segments/batch-delete")
async def delete_segments(segment_ids: List[str]):
    """
    批量删除切割结果

    请求体：["segment_id1", "segment_id2", ...]
    """
    results = []
    errors = []

    for segment_id in segment_ids:
        try:
            # 调用单个删除函数
            await delete_segment(segment_id)
            results.append({"segment_id": segment_id, "status": "success"})
        except HTTPException as e:
            errors.append({"segment_id": segment_id, "error": e.detail})
        except Exception as e:
            errors.append({"segment_id": segment_id, "error": str(e)})

    return {
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors
    }
