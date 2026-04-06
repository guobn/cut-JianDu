from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from datetime import datetime
from pathlib import Path
import time
import uuid
import logging
import json
import hashlib
import requests

from app.models.detection import (
    DetectionResult, DetectionParameters, ModelType,
    SegmentationRequest, SegmentationResult
)
from app.models.task import TaskStatus
from app.services.image_service import ImageService
from app.services.segmentation_service import SegmentationService
from app.services.celery_tasks import detect_single_slips_task, detect_single_characters_task
from app.utils.image_utils import ImageProcessor
from app.services.supabase_service import (
    build_public_url,
    build_segments_storage_key,
    insert_segment_record,
    upsert_image_record,
    upload_segment_to_storage,
    get_slip_metadata,
    _require_supabase_config,
    _base_url,
    _auth_headers,
)
from app.config import settings
from app.core.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/segmentation", tags=["segmentation"])
image_service = ImageService()
segmentation_service = SegmentationService()


# 响应模型：任务提交响应
class TaskSubmitResponse:
    """任务提交响应"""
    def __init__(self, task_id: str, status: str, message: str):
        self.task_id = task_id
        self.status = status
        self.message = message

    def model_dump(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "message": self.message
        }


@router.post("/detect")
async def detect_regions(
    file: UploadFile = File(..., description="前端上传的图像文件（与当前显示一致）"),
    image_id: str = Form(..., description="图像ID，切割时关联用"),
    mode: str = Form(..., description="single-slip 或 single-character"),
    parameters: Optional[str] = Form(None, description="JSON 字符串，检测参数可选"),
):
    """
    检测图像中的区域（异步任务）。
    前端必须传 multipart：file（图像）+ image_id + mode。
    返回 task_id，通过 /api/tasks/{task_id} 查询结果。
    """
    log = logging.getLogger(__name__)
    try:
        raw = await file.read()
        img_md5 = hashlib.md5(raw).hexdigest()
        image = ImageProcessor.load_image_from_bytes(raw)
        h, w = image.shape[:2]
        print(f"[detect] 收到图像: image_id={image_id}, 尺寸={w}x{h}, 字节={len(raw)}, md5={img_md5}, mode={mode}", flush=True)
        log.info("detect 收到图像: image_id=%s, 尺寸=%sx%s, 字节=%s, md5=%s", image_id, w, h, len(raw), img_md5)

        params_dict = None
        if parameters:
            try:
                params_dict = json.loads(parameters)
            except Exception:
                pass

        # 根据模式提交不同的异步任务
        if mode == "single-slip":
            task = detect_single_slips_task.delay(raw, image_id, params_dict)
        elif mode == "single-character":
            task = detect_single_characters_task.delay(raw, image_id, params_dict)
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_MODE",
                    "error_message": f"不支持的检测模式: {mode}",
                    "suggested_solution": "请使用 'single-slip' 或 'single-character'",
                },
            )

        log.info("detect 任务已提交: task_id=%s, mode=%s", task.id, mode)
        return {
            "task_id": task.id,
            "status": TaskStatus.PENDING.value,
            "message": "任务已提交，请通过 /api/tasks/{task_id} 查询结果"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_IMAGE_DATA",
                "error_message": str(e),
                "suggested_solution": "请上传有效图像文件",
            },
        )
    except Exception as e:
        log.exception("detect 失败")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DETECTION_FAILED",
                "error_message": str(e),
                "suggested_solution": "请检查图像质量和参数设置",
            },
        )


@router.post("/detect-upload")
async def detect_upload(
    file: UploadFile = File(..., description="上传的图像文件"),
    mode: str = Form("single-slip", description="single-slip 或 single-character"),
    parameters: Optional[str] = Form(None, description="JSON 字符串，检测参数可选"),
):
    """
    后端测试用：上传图像并异步检测，无需 image_id/鉴权。
    返回 task_id，通过 /api/tasks/{task_id} 查询结果。
    示例：curl -X POST http://127.0.0.1:8000/api/segmentation/detect-upload -F "file=@/path/to/image.png" -F "mode=single-slip"
    """
    log = logging.getLogger(__name__)
    image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    try:
        raw = await file.read()
        img_md5 = hashlib.md5(raw).hexdigest()
        image = ImageProcessor.load_image_from_bytes(raw)
        h, w = image.shape[:2]
        print(f"[detect-upload] 图像: image_id={image_id}, 尺寸={w}x{h}, 字节={len(raw)}, md5={img_md5}, mode={mode}", flush=True)
        log.info("detect-upload 收到图像: image_id=%s, 尺寸=%sx%s, 字节=%s, md5=%s", image_id, w, h, len(raw), img_md5)

        params_dict = None
        if parameters:
            try:
                params_dict = json.loads(parameters)
            except Exception:
                pass

        # 根据模式提交不同的异步任务
        if mode == "single-slip":
            task = detect_single_slips_task.delay(raw, image_id, params_dict)
        elif mode == "single-character":
            task = detect_single_characters_task.delay(raw, image_id, params_dict)
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_MODE",
                    "error_message": f"不支持的检测模式: {mode}",
                    "suggested_solution": "请使用 'single-slip' 或 'single-character'",
                },
            )

        log.info("detect-upload 任务已提交: task_id=%s, mode=%s", task.id, mode)
        return {
            "task_id": task.id,
            "status": TaskStatus.PENDING.value,
            "message": "任务已提交，请通过 /api/tasks/{task_id} 查询结果"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_IMAGE_DATA",
                "error_message": str(e),
                "suggested_solution": "请上传有效图像文件",
            },
        )
    except Exception as e:
        log.exception("detect-upload 失败")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DETECTION_FAILED",
                "error_message": str(e),
                "suggested_solution": "请检查图像质量和参数设置",
            },
        )


@router.post("/detect-fast")
async def detect_fast(
    file: UploadFile = File(..., description="前端上传的图像文件"),
    image_id: str = Form(..., description="图像ID"),
    mode: str = Form(..., description="single-slip 或 single-character"),
    parameters: Optional[str] = Form(None, description="JSON 字符串，检测参数可选"),
):
    """
    快速检测（同步）：直接返回检测结果，不使用 Celery 异步任务。
    适用于需要快速验证前端的场景。
    """
    log = logging.getLogger(__name__)
    try:
        raw = await file.read()
        img_md5 = hashlib.md5(raw).hexdigest()
        image = ImageProcessor.load_image_from_bytes(raw)
        h, w = image.shape[:2]
        print(f"[detect-fast] 收到图像: image_id={image_id}, 尺寸={w}x{h}, 字节={len(raw)}, md5={img_md5}, mode={mode}", flush=True)
        log.info("detect-fast 收到图像: image_id=%s, 尺寸=%sx%s, 字节=%s, md5=%s", image_id, w, h, len(raw), img_md5)

        # 解析参数
        params_dict = None
        if parameters:
            try:
                params_dict = json.loads(parameters)
            except Exception:
                pass
        print(f">>> received model_type: {params_dict.get('model_type')}")

        # 构建检测参数
        params = DetectionParameters(**(params_dict or {}))

        # 同步执行检测
        start_time = time.time()
        if mode == "single-slip":
            result = segmentation_service.detect_single_slips(image, params)
        elif mode == "single-character":
            result = segmentation_service.detect_single_characters(image, params)
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_MODE",
                    "error_message": f"不支持的检测模式: {mode}",
                    "suggested_solution": "请使用 'single-slip' 或 'single-character'",
                },
            )

        processing_time = time.time() - start_time

        log.info("detect-fast 完成: image_id=%s, mode=%s, 检测到 %d 个区域, 耗时 %.2fs",
                 image_id, mode, len(result), processing_time)

        # 返回检测结果
        return {
            "status": "success",
            "image_id": image_id,
            "mode": mode,
            "bounding_boxes": [bbox.model_dump() for bbox in result],
            "total_count": len(result),
            "processing_time": processing_time,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_IMAGE_DATA",
                "error_message": str(e),
                "suggested_solution": "请上传有效图像文件",
            },
        )
    except Exception as e:
        log.exception("detect-fast 失败")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DETECTION_FAILED",
                "error_message": str(e),
                "suggested_solution": "请检查图像质量和参数设置",
            },
        )


@router.post("/cut", response_model=SegmentationResult)
async def cut_image(request: SegmentationRequest, user=Depends(get_current_user)):
    """
    执行图像切割
    
    Args:
        request: 切割请求
            - image_id: 图像ID
            - bounding_boxes: 边界框列表
            - output_format: 输出格式（默认png）
            - add_padding: 是否添加边距（默认False）
            - padding_size: 边距大小（默认10）
    """
    try:
        user_id = user.get("id") if isinstance(user, dict) else None
        image = image_service.load_image_with_supabase_fallback(request.image_id, user_id)
        image_path = image_service.get_image_path(request.image_id)

        # 查询原图的简牍编号
        slip_number = None
        try:
            slip_meta = get_slip_metadata(request.image_id)
            if slip_meta:
                slip_number = slip_meta.get("slip_number")
        except Exception:
            pass  # 查询失败不影响主流程

        # 开始计时
        start_time = time.time()
        
        # 提取区域
        regions = segmentation_service.extract_regions(
            image,
            request.bounding_boxes,
            add_padding=request.add_padding,
            padding_size=request.padding_size,
        )
        
        # 生成切割ID
        segmentation_id = f"seg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 创建输出目录
        output_dir = Path(settings.result_dir) / segmentation_id
        
        # 保存切割结果到本地
        results = await segmentation_service.save_segmented_regions(
            regions,
            request.bounding_boxes,
            output_dir,
            output_format=request.output_format,
            prefix=request.image_id,
            slip_number=slip_number,
        )

        # === 模块 2：将切割结果同步到 Supabase（Storage + Postgres） ===
        # 1) 确保 images 表中存在对应原图记录
        try:
            upsert_image_record(
                image_id=request.image_id,
                image_path=image_path,
                width=image.shape[1],
                height=image.shape[0],
            )
        except Exception as e:
            # 不影响主流程，记录在日志中（此处简单抛出可供调试，后续可改为 logging）
            raise HTTPException(
                status_code=500,
                detail={
                    "error_code": "SUPABASE_IMAGE_UPSERT_FAILED",
                    "error_message": f"写入原图记录到 Supabase 失败: {str(e)}",
                },
            )

        enhanced_results = []

        # 准备层级关系所需的上下文：
        # - parent_segment_id: 若为“单支 -> 单字”切割，则前端会传入对应单支的 segment_id
        # - source_image_id: 始终指向最初的原图 id
        parent_segment_id = getattr(request, "parent_segment_id", None)
        source_image_id = request.image_id
        dataset_id = "default"

        # 如果存在父级 segment（说明当前是“单支 -> 单字”切割），
        # 则从 Supabase 的 segments 表中查询父级记录，用它的 source_image_id
        # 作为本次切割结果的 source_image_id，从而建立“原图 -> 单支 -> 单字”的链路。
        if parent_segment_id:
            try:
                _require_supabase_config()
                url = f"{_base_url()}/rest/v1/segments"
                headers = _auth_headers()
                params = {"id": f"eq.{parent_segment_id}"}
                resp = requests.get(url, headers=headers, params=params, timeout=20)
                if resp.status_code >= 400 or not resp.json():
                    raise RuntimeError(f"父级切割结果不存在: {parent_segment_id}")
                parent_seg = resp.json()[0]
                # 旧数据可能没有 source_image_id 字段，回退到 image_id
                source_image_id = parent_seg.get("source_image_id") or parent_seg.get("image_id")
                dataset_id = parent_seg.get("dataset_id") or "default"
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error_code": "SUPABASE_PARENT_SEGMENT_FETCH_FAILED",
                        "error_message": f"获取父级切割结果失败: {str(e)}",
                    },
                )
        else:
            # 原图 -> 单支 的情况，原图本身就是链路的起点
            source_image_id = request.image_id
            dataset_id = "default"

        user_id = user.get("id") if isinstance(user, dict) else "anonymous"

        # 2) 针对每个切割结果：上传到 Storage，并在 segments 表插入记录
        try:
            for result_item, bbox in zip(results, request.bounding_boxes):
                local_path = Path(result_item["path"])
                segment_index = result_item.get("order", 0) or 0

                # 通过 bbox.id 前缀区分类型：char_ 开头为单字，否则视为简牍
                segment_type = "char" if bbox.id.startswith("char_") else "slip"

                storage_key = build_segments_storage_key(
                    image_id=request.image_id,
                    segment_type=segment_type,
                    segment_index=segment_index or 0,
                    output_format=request.output_format,
                    user_id=user_id,
                    slip_number=slip_number,
                )

                # 上传切割后的图像到 Supabase Storage
                upload_segment_to_storage(local_path, storage_key)

                # 在数据库 segments 表中插入记录
                segment_row = insert_segment_record(
                    image_id=request.image_id,
                    bbox=bbox,
                    segment_index=segment_index or 0,
                    segment_type=segment_type,
                    storage_key=storage_key,
                    region_width=result_item["width"],
                    region_height=result_item["height"],
                    dataset_id=dataset_id,
                    user_id=user_id,
                    source_image_id=source_image_id,
                    parent_segment_id=parent_segment_id if segment_type == "char" else None,
                )

                public_url = build_public_url(storage_key)

                # 在原有结果基础上附加 Supabase 相关信息
                enhanced_item = {
                    **result_item,
                    "segment_id": segment_row["id"],
                    "segment_type": segment_type,
                    "storage_path": storage_key,
                    "public_url": public_url,
                }
                enhanced_results.append(enhanced_item)

        except HTTPException:
            # 已经封装为 HTTPException，直接抛出
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error_code": "SUPABASE_SYNC_FAILED",
                    "error_message": f"切割结果同步到 Supabase 失败: {str(e)}",
                },
            )
        
        # 计算处理时间
        processing_time = time.time() - start_time

        # 创建结果（返回带 Supabase 字段的 enhanced_results）
        result = SegmentationResult(
            segmentation_id=segmentation_id,
            image_id=request.image_id,
            total_count=len(enhanced_results),
            results=enhanced_results,
            processing_time=processing_time,
            created_at=datetime.now(),
        )

        return result
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "IMAGE_NOT_FOUND",
                "error_message": f"图像不存在: {request.image_id}",
                "suggested_solution": "请检查图像ID是否正确"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "SEGMENTATION_FAILED",
                "error_message": f"切割失败: {str(e)}",
                "suggested_solution": "请检查边界框参数是否正确"
            }
        )

@router.get("/models")
async def list_models():
    """
    列出所有可用的检测模型及其状态
    
    Returns:
        模型状态字典，包含每个模型的 available, path, loaded 信息
    """
    from app.services.model_factory import get_model_factory
    
    factory = get_model_factory()
    models = {}
    
    for model_type in ModelType:
        info = factory.get_model_info(model_type)
        models[model_type.value] = info
    
    return {
        "models": models,
        "default_fallback_order": ["deconv-yolo", "aps-yolo", "yolov8"]
    }


@router.post("/models/{model_type}/load")
async def load_model(model_type: str):
    """
    预加载指定模型到缓存
    
    Args:
        model_type: 模型类型 (yolov8, aps-yolo, deconv-yolo, rga-crnn)
    
    Returns:
        加载状态：{"status": "loaded"|"unavailable", "model_type": str}
    """
    from app.services.model_factory import get_model_factory
    
    try:
        mt = ModelType(model_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_MODEL_TYPE",
                "error_message": f"无效的模型类型：{model_type}",
                "suggested_solution": f"请使用以下之一：{[m.value for m in ModelType]}"
            }
        )
    
    factory = get_model_factory()
    model = factory.get_model(mt, use_fallback=False)
    
    if model is None:
        return {"status": "unavailable", "model_type": model_type, "message": "模型文件未找到或加载失败"}
    
    return {"status": "loaded", "model_type": model_type, "message": f"模型 {model_type} 已成功加载到缓存"}
