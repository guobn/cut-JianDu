from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from pathlib import Path
import time
import uuid

from app.core.auth import get_current_user_optional
from app.models.normalization import NormalizationRequest, NormalizationResult
from app.services.image_service import ImageService
from app.services.normalization_service import NormalizationService
from app.config import settings

router = APIRouter(prefix="/api/normalization", tags=["normalization"])
image_service = ImageService()
normalization_service = NormalizationService()


@router.post("/normalize", response_model=NormalizationResult)
async def normalize_image(request: NormalizationRequest, user=Depends(get_current_user_optional)):
    """执行图像尺寸归一化。图像优先本地，不存在且已登录则从 Supabase 拉取。"""
    try:
        user_id = user.get("id") if user else None
        image = image_service.load_image_with_supabase_fallback(request.image_id, user_id)
        
        # 记录原始尺寸
        original_height, original_width = image.shape[:2]
        
        # 开始计时
        start_time = time.time()
        
        # 执行归一化
        normalized_image = normalization_service.normalize_size(
            image,
            target_width=request.target_width,
            target_height=request.target_height,
            keep_aspect_ratio=request.keep_aspect_ratio,
            padding_color=request.padding_color,
            interpolation=request.interpolation
        )
        
        # 生成归一化ID
        normalization_id = f"norm_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 保存归一化后的图像
        output_dir = Path(settings.result_dir) / "normalized"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        ext = image_service.get_image_path(request.image_id).suffix
        output_filename = f"{normalization_id}{ext}"
        output_path = output_dir / output_filename
        
        from app.utils.image_utils import ImageProcessor
        ImageProcessor.save_image(normalized_image, output_path)
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        # 创建结果
        result = NormalizationResult(
            normalization_id=normalization_id,
            image_id=request.image_id,
            original_width=original_width,
            original_height=original_height,
            target_width=request.target_width,
            target_height=request.target_height,
            output_path=str(output_path),
            processing_time=processing_time,
            created_at=datetime.now()
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
                "error_code": "NORMALIZATION_FAILED",
                "error_message": f"归一化失败: {str(e)}",
                "suggested_solution": "请检查参数设置"
            }
        )
