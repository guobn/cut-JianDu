from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from pathlib import Path
import time
import uuid

from app.core.auth import get_current_user_optional
from app.models.rotation import (
    RotationDetectionResult,
    RotationCorrectionRequest,
    RotationCorrectionResult
)
from app.models.task import TaskStatus
from app.services.image_service import ImageService
from app.services.rotation_service import RotationService
from app.services.celery_tasks import detect_rotation_angle_task, correct_rotation_task
from app.config import settings

router = APIRouter(prefix="/api/rotation", tags=["rotation"])
image_service = ImageService()
rotation_service = RotationService()


@router.post("/detect-angle")
async def detect_rotation_angle(image_id: str, user=Depends(get_current_user_optional)):
    """
    异步检测图像倾斜角度。
    返回 task_id，通过 /api/tasks/{task_id} 查询结果。
    图像优先本地，不存在且已登录则从 Supabase 拉取。
    """
    try:
        user_id = user.get("id") if user else None

        # 提交异步任务
        task = detect_rotation_angle_task.delay(image_id, user_id)

        return {
            "task_id": task.id,
            "status": TaskStatus.PENDING.value,
            "message": "任务已提交，请通过 /api/tasks/{task_id} 查询结果"
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "IMAGE_NOT_FOUND",
                "error_message": f"图像不存在: {image_id}",
                "suggested_solution": "请检查图像ID是否正确"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DETECTION_FAILED",
                "error_message": f"角度检测任务提交失败: {str(e)}",
                "suggested_solution": "请检查图像质量"
            }
        )


@router.post("/correct")
async def correct_rotation(request: RotationCorrectionRequest, user=Depends(get_current_user_optional)):
    """
    异步执行旋转校正。
    返回 task_id，通过 /api/tasks/{task_id} 查询结果。
    图像优先本地，不存在且已登录则从 Supabase 拉取。
    """
    try:
        user_id = user.get("id") if user else None

        # 提交异步任务
        task = correct_rotation_task.delay(
            request.image_id,
            angle=request.angle,
            auto_crop=request.auto_crop,
            user_id=user_id
        )

        return {
            "task_id": task.id,
            "status": TaskStatus.PENDING.value,
            "message": "任务已提交，请通过 /api/tasks/{task_id} 查询结果"
        }

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
                "error_code": "CORRECTION_FAILED",
                "error_message": f"旋转校正任务提交失败: {str(e)}",
                "suggested_solution": "请检查参数设置"
            }
        )


@router.post("/detect-angle-fast")
async def detect_rotation_angle_fast(image_id: str, user=Depends(get_current_user_optional)):
    """
    快速检测图像倾斜角度（同步）。
    直接返回检测结果，不使用 Celery 异步任务。
    """
    try:
        user_id = user.get("id") if user else None

        # 加载图像
        image = image_service.load_image_with_supabase_fallback(image_id, user_id)

        # 同步执行角度检测
        start_time = time.time()
        angle = rotation_service.detect_rotation_angle(image)
        processing_time = time.time() - start_time

        return {
            "status": "success",
            "image_id": image_id,
            "angle": angle,
            "processing_time": processing_time,
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "IMAGE_NOT_FOUND",
                "error_message": f"图像不存在: {image_id}",
                "suggested_solution": "请检查图像ID是否正确"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DETECTION_FAILED",
                "error_message": f"角度检测失败: {str(e)}",
                "suggested_solution": "请检查图像质量"
            }
        )


@router.post("/correct-fast")
async def correct_rotation_fast(request: RotationCorrectionRequest, user=Depends(get_current_user_optional)):
    """
    快速执行旋转校正（同步）。
    直接返回校正结果，不使用 Celery 异步任务。
    """
    try:
        user_id = user.get("id") if user else None

        # 加载图像
        image = image_service.load_image_with_supabase_fallback(request.image_id, user_id)

        # 同步执行旋转校正
        start_time = time.time()
        corrected_image = rotation_service.correct_rotation(
            image,
            angle=request.angle,
            auto_crop=request.auto_crop
        )
        processing_time = time.time() - start_time

        # 生成新的图像ID
        corrected_id = f"{request.image_id}_corrected_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 保存校正后的图像
        output_path = Path(settings.result_dir) / f"{corrected_id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image_service.save_image(corrected_image, str(output_path))

        return {
            "status": "success",
            "image_id": corrected_id,
            "original_image_id": request.image_id,
            "angle": request.angle,
            "auto_crop": request.auto_crop,
            "width": corrected_image.shape[1],
            "height": corrected_image.shape[0],
            "processing_time": processing_time,
            "path": str(output_path),
        }

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
                "error_code": "CORRECTION_FAILED",
                "error_message": f"旋转校正失败: {str(e)}",
                "suggested_solution": "请检查参数设置"
            }
        )
