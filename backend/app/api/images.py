from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from datetime import datetime
from typing import List, Optional
import uuid
import os
from pathlib import Path

from app.models.image import ImageUploadResponse, ImageListItem
from app.models.response import ErrorResponse
from app.services.image_service import ImageService
from app.utils.file_utils import FileManager
from app.config import settings
from app.core.auth import get_current_user, get_current_user_optional
from app.services.supabase_service import (
    upload_segment_to_storage,
    build_public_url,
    list_storage_objects,
    insert_slip_metadata,
)

router = APIRouter(prefix="/api/images", tags=["images"])
image_service = ImageService()

# 分片上传配置
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB per chunk
UPLOAD_THRESHOLD = 10 * 1024 * 1024  # 10MB threshold for chunked upload


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    slip_number: Optional[str] = Form(None),
    user=Depends(get_current_user)
):
    """
    上传图像文件

    支持格式：JPG, PNG, TIFF, BMP
    最大文件大小：50MB
    可选参数：slip_number - 简牍编号(如"里耶秦简001号")
    """
    # 验证文件格式
    if not FileManager.is_valid_image_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_FORMAT",
                "error_message": "不支持的图像格式",
                "suggested_solution": "请上传 JPG、PNG、TIFF 或 BMP 格式的图像"
            }
        )

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 验证文件大小
    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "error_message": "文件大小超过限制",
                "suggested_solution": f"请上传小于 {settings.max_file_size // (1024*1024)}MB 的图像文件"
            }
        )

    # 生成图像ID
    image_id = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    try:
        # 保存文件并提取元数据
        image_info = await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )

        # 如果提供了编号,添加到返回信息中
        if slip_number:
            image_info.slip_number = slip_number

        # 将原图同步到 Supabase Storage（与切割结果同 bucket：segments）
        try:
            # 原图统一存储到每个用户的 img 文件夹下
            storage_key = f"{user.get('id', 'anonymous')}/img/{image_info.filename}"
            # 本地文件路径
            local_path = image_service.get_image_path(image_id)
            upload_segment_to_storage(local_path, storage_key)
            public_url = build_public_url(storage_key)
            image_info.storage_path = storage_key
            image_info.public_url = public_url

            # 如果提供了编号,存储到 slip_image_metadata 表
            if slip_number:
                try:
                    insert_slip_metadata(
                        image_id=image_id,
                        slip_number=slip_number,
                        user_id=user.get('id', 'anonymous')
                    )
                except Exception as e:
                    print(f"警告：简牍元数据存储失败: {e}")
        except Exception as e:
            # 不影响主流程，记录警告
            print(f"警告：原图上传到 Supabase 失败: {e}")

        return image_info

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "UPLOAD_FAILED",
                "error_message": f"图像上传失败: {str(e)}",
                "suggested_solution": "请检查图像文件是否损坏，然后重试"
            }
        )


@router.get("/{image_id}")
async def get_image(image_id: str, user=Depends(get_current_user_optional)):
    """
    获取图像文件。优先本地，若不存在且已登录则从 Supabase Storage 拉取并缓存。
    """
    try:
        user_id = user.get("id") if user else None
        image_service.load_image_with_supabase_fallback(image_id, user_id)
        file_path = image_service.get_image_path(image_id)
        file_size = file_path.stat().st_size
        print(f"[GET /api/images] image_id={image_id}, 发出文件大小={file_size}", flush=True)

        # 确定正确的 media_type
        ext = file_path.suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp'
        }
        media_type = media_type_map.get(ext, 'image/jpeg')
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=file_path.name,
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Expose-Headers': '*'
            }
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "IMAGE_NOT_FOUND",
                "error_message": f"图像不存在: {image_id}",
                "suggested_solution": "请检查图像ID是否正确"
            }
        )


@router.get("/", response_model=List[ImageListItem])
async def list_images(limit: int = 50, user=Depends(get_current_user)):
    """
    获取已上传的图像列表
    
    Args:
        limit: 返回的最大数量，默认50
    """
    try:
        # 只列出当前用户上传的原图（存储在 Supabase segments bucket 下的 {user_id}/img/）
        user_id = user.get("id") if isinstance(user, dict) else "anonymous"
        prefix = f"{user_id}/img/"

        objects = list_storage_objects(prefix=prefix, limit=limit, offset=0)

        images: List[ImageListItem] = []
        for obj in objects:
            name = obj.get("name")  # 文件名，如 img_...png
            if not name:
                continue

            storage_path = f"{prefix}{name}"
            public_url = build_public_url(storage_path)

            # 从文件名解析 image_id
            image_id = name.rsplit(".", 1)[0]

            # 尝试从本地获取宽高/大小（本地仍有缓存）
            width = height = 0
            file_size = obj.get("metadata", {}).get("size", 0) or obj.get("size", 0)
            try:
                local_path = image_service.get_image_path(image_id)
                image = image_service.image_processor.load_image(local_path)
                info = image_service.image_processor.get_image_info(image)
                width = info["width"]
                height = info["height"]
            except Exception:
                pass

            upload_time = datetime.fromisoformat(
                obj.get("created_at", datetime.now().isoformat()).replace("Z", "+00:00")
            )

            images.append(
                ImageListItem(
                    image_id=image_id,
                    filename=name,
                    width=width,
                    height=height,
                    format="UNKNOWN",
                    file_size=file_size,
                    upload_time=upload_time,
                    thumbnail_url=public_url,
                )
            )

        return images[:limit]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "LIST_FAILED",
                "error_message": f"获取图像列表失败: {str(e)}",
                "suggested_solution": "请稍后重试"
            }
        )

# 分片上传临时存储目录
CHUNK_TEMP_DIR = Path(settings.temp_dir) / "chunks"
CHUNK_TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload-chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...),
    user=Depends(get_current_user_optional)
):
    """
    上传文件分片

    Args:
        chunk: 分片文件
        upload_id: 上传任务 ID
        chunk_index: 分片索引（从 0 开始）
        total_chunks: 总分片数
        filename: 原始文件名
    """
    try:
        # 创建用户临时目录
        user_id = user.get("id", "anonymous") if user else "anonymous"
        upload_dir = CHUNK_TEMP_DIR / user_id / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 保存分片
        chunk_path = upload_dir / f"chunk_{chunk_index:05d}"
        content = await chunk.read()

        with open(chunk_path, "wb") as f:
            f.write(content)

        # 保存上传元数据 - 为每个分片创建单独的标记文件以避免并发冲突
        metadata_path = upload_dir / "_metadata"
        chunk_marker_path = upload_dir / f"_chunk_{chunk_index:05d}.done"

        import json

        # 创建分片完成标记文件（原子操作）
        chunk_marker_path.touch(exist_ok=True)

        # 更新主元数据文件
        try:
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "upload_id": upload_id,
                    "filename": filename,
                    "total_chunks": total_chunks,
                    "uploaded_chunks": [],
                    "user_id": user_id
                }

            # 添加当前分片索引（避免重复）
            if chunk_index not in metadata["uploaded_chunks"]:
                metadata["uploaded_chunks"].append(chunk_index)
                metadata["uploaded_chunks"].sort()

            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
        except Exception:
            # 元数据更新失败不影响分片上传成功
            pass

        return {
            "success": True,
            "chunk_index": chunk_index,
            "upload_id": upload_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CHUNK_UPLOAD_FAILED",
                "error_message": f"分片上传失败：{str(e)}",
                "suggested_solution": "请检查网络连接后重试"
            }
        )


@router.post("/merge-chunks")
async def merge_chunks(
    upload_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    slip_number: Optional[str] = Form(None),
    user=Depends(get_current_user)
):
    """
    合并已上传的分片

    Args:
        upload_id: 上传任务 ID
        filename: 原始文件名
        total_chunks: 总分片数
        slip_number: 简牍编号（可选）
    """
    try:
        import json

        user_id = user.get("id", "anonymous")
        upload_dir = CHUNK_TEMP_DIR / user_id / upload_id
        metadata_path = upload_dir / "_metadata"

        # 验证元数据
        if not metadata_path.exists():
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "METADATA_NOT_FOUND",
                    "error_message": "未找到上传元数据",
                    "suggested_solution": "请重新上传所有分片"
                }
            )

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # 验证所有分片是否已上传 - 使用标记文件验证更可靠
        uploaded_chunks = set()
        for i in range(total_chunks):
            marker_path = upload_dir / f"_chunk_{i:05d}.done"
            if marker_path.exists():
                uploaded_chunks.add(i)

        # 同时检查元数据文件中的记录
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                metadata_chunks = set(metadata.get("uploaded_chunks", []))
                # 取标记文件和元数据的并集
                uploaded_chunks = uploaded_chunks.union(metadata_chunks)
            except Exception:
                pass

        expected_chunks = set(range(total_chunks))
        missing_chunks = expected_chunks - uploaded_chunks

        if missing_chunks:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INCOMPLETE_UPLOAD",
                    "error_message": f"缺少分片：{sorted(missing_chunks)}",
                    "suggested_solution": "请重新上传缺失的分片"
                }
            )

        # 生成图像 ID
        image_id = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 合并分片
        merged_path = upload_dir / filename
        with open(merged_path, "wb") as f:
            for i in range(total_chunks):
                chunk_path = upload_dir / f"chunk_{i:05d}"
                with open(chunk_path, "rb") as cf:
                    f.write(cf.read())

        # 读取合并后的文件
        with open(merged_path, "rb") as f:
            content = f.read()

        # 保存文件并提取元数据
        image_info = await image_service.save_image(
            image_id=image_id,
            filename=filename,
            content=content,
            content_type="image/jpeg"  # 默认类型
        )

        # 如果提供了编号，添加到返回信息中
        if slip_number:
            image_info.slip_number = slip_number

        # 同步到 Supabase Storage
        try:
            storage_key = f"{user_id}/img/{image_info.filename}"
            upload_segment_to_storage(str(merged_path), storage_key)
            public_url = build_public_url(storage_key)
            image_info.storage_path = storage_key
            image_info.public_url = public_url

            if slip_number:
                try:
                    insert_slip_metadata(
                        image_id=image_id,
                        slip_number=slip_number,
                        user_id=user_id
                    )
                except Exception as e:
                    print(f"警告：简牍元数据存储失败：{e}")
        except Exception as e:
            print(f"警告：原图上传到 Supabase 失败：{e}")

        # 清理临时文件
        import shutil
        shutil.rmtree(upload_dir)

        return image_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "MERGE_FAILED",
                "error_message": f"合并分片失败：{str(e)}",
                "suggested_solution": "请重新上传所有分片"
            }
        )


@router.delete("/abort-upload/{upload_id}")
async def abort_upload(upload_id: str, user=Depends(get_current_user_optional)):
    """
    取消上传，清理临时文件

    Args:
        upload_id: 上传任务 ID
    """
    try:
        import shutil

        user_id = user.get("id", "anonymous") if user else "anonymous"
        upload_dir = CHUNK_TEMP_DIR / user_id / upload_id

        if upload_dir.exists():
            shutil.rmtree(upload_dir)

        return {"success": True, "message": "已清理临时文件"}

    except Exception as e:
        # 即使失败也不抛出异常，避免影响前端错误处理
        print(f"清理临时文件失败：{e}")
        return {"success": False, "error": str(e)}
