"""
测试 API 路由 - 无需鉴权，用于快速测试核心功能
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.image import ImageUploadResponse
from app.models.detection import DetectionRequest, DetectionResult
from app.models.rotation import RotationDetectionResult, RotationCorrectionResult
from app.models.normalization import NormalizationRequest, NormalizationResult
from app.services.image_service import ImageService
from app.services.segmentation_service import SegmentationService
from app.services.rotation_service import RotationService
from app.services.normalization_service import NormalizationService
from app.utils.file_utils import FileManager
from app.config import settings

router = APIRouter(prefix="/api/test", tags=["test"])

image_service = ImageService()
segmentation_service = SegmentationService()
rotation_service = RotationService()
normalization_service = NormalizationService()


@router.post("/upload", response_model=ImageUploadResponse)
async def test_upload_image(file: UploadFile = File(...)):
    """
    测试图像上传（无需鉴权）
    """
    if not FileManager.is_valid_image_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_FORMAT",
                "error_message": "不支持的图像格式",
                "suggested_solution": "请上传 JPG、PNG、TIFF 或 BMP 格式的图像"
            }
        )

    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "error_message": "文件大小超过限制",
                "suggested_solution": f"请上传小于 {settings.max_file_size // (1024*1024)}MB 的图像文件"
            }
        )

    image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    try:
        image_info = await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )
        return image_info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "UPLOAD_FAILED",
                "error_message": f"图像上传失败：{str(e)}",
                "suggested_solution": "请检查图像文件是否损坏，然后重试"
            }
        )


@router.post("/detect", response_model=DetectionResult)
async def test_detect(
    file: UploadFile = File(...),
    mode: str = Form("single-slip"),
    model_type: Optional[str] = Form(None),
):
    """
    测试检测功能（无需鉴权）

    mode: 'single-slip' 或 'single-character'
    model_type: 模型类型（可选）
    """
    try:
        content = await file.read()

        # 保存临时图像
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )

        # 执行检测
        image = image_service.load_image(image_id)

        if mode == "single-slip":
            result = segmentation_service.detect_single_slips(
                image=image,
                image_id=image_id,
                model_type=model_type
            )
        else:
            result = segmentation_service.detect_single_characters(
                image=image,
                image_id=image_id,
                model_type=model_type
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DETECTION_FAILED",
                "error_message": f"检测失败：{str(e)}",
                "suggested_solution": "请检查图像质量和参数设置"
            }
        )


@router.post("/cut")
async def test_cut(
    image_id: str = Form(...),
    bounding_boxes: str = Form(...),
    segment_type: str = Form("slip"),
):
    """
    测试切割功能（无需鉴权）

    bounding_boxes: JSON 字符串，格式 [{"x":0,"y":0,"width":100,"height":100,"confidence":0.9}]
    segment_type: 'slip' 或 'char'
    """
    try:
        import json
        boxes = json.loads(bounding_boxes)

        # 加载图像
        image = image_service.load_image(image_id)

        # 执行切割
        results = segmentation_service.cut_image_regions(
            image=image,
            image_id=image_id,
            bounding_boxes=boxes,
            segment_type=segment_type,
            output_format="png",
            user_id="test_user"
        )

        return {
            "success": True,
            "message": f"成功切割 {len(results)} 个区域",
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CUT_FAILED",
                "error_message": f"切割失败：{str(e)}",
                "suggested_solution": "请检查边界框参数是否正确"
            }
        )


@router.post("/rotation/detect", response_model=RotationDetectionResult)
async def test_detect_rotation(file: UploadFile = File(...)):
    """
    测试旋转角度检测（无需鉴权）
    """
    try:
        content = await file.read()

        # 保存临时图像
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )

        # 检测旋转角度
        image = image_service.load_image(image_id)
        result = rotation_service.detect_rotation_angle(image)

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "ROTATION_DETECT_FAILED",
                "error_message": f"检测失败：{str(e)}",
                "suggested_solution": "请检查图像质量"
            }
        )


@router.post("/rotation/correct", response_model=RotationCorrectionResult)
async def test_correct_rotation(
    file: UploadFile = File(...),
    angle: Optional[float] = Form(None),
    auto_crop: bool = Form(True),
):
    """
    测试旋转校正（无需鉴权）
    """
    try:
        content = await file.read()

        # 保存临时图像
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )

        # 执行旋转校正
        image = image_service.load_image(image_id)

        if angle is None:
            # 自动检测角度
            detection_result = rotation_service.detect_rotation_angle(image)
            angle = detection_result.angle

        result = rotation_service.correct_rotation(
            image=image,
            angle=angle,
            auto_crop=auto_crop
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "ROTATION_CORRECT_FAILED",
                "error_message": f"校正失败：{str(e)}",
                "suggested_solution": "请检查参数设置"
            }
        )


@router.post("/normalization/normalize", response_model=NormalizationResult)
async def test_normalize(
    file: UploadFile = File(...),
    target_width: int = Form(800),
    target_height: int = Form(1200),
    keep_aspect_ratio: bool = Form(True),
    padding_color: str = Form("white"),
):
    """
    测试尺寸归一化（无需鉴权）
    """
    try:
        content = await file.read()

        # 保存临时图像
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )

        # 执行归一化
        image = image_service.load_image(image_id)

        result = normalization_service.normalize_size(
            image=image,
            target_width=target_width,
            target_height=target_height,
            keep_aspect_ratio=keep_aspect_ratio,
            padding_color=padding_color
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "NORMALIZATION_FAILED",
                "error_message": f"归一化失败：{str(e)}",
                "suggested_solution": "请检查参数设置"
            }
        )


@router.get("/image/{image_id}")
async def test_get_image(image_id: str):
    """
    获取测试图像（无需鉴权）
    """
    try:
        file_path = image_service.get_image_path(image_id)

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
            filename=file_path.name
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "IMAGE_NOT_FOUND",
                "error_message": f"图像不存在：{image_id}",
                "suggested_solution": "请检查图像 ID 是否正确"
            }
        )


@router.get("/health")
async def test_health():
    """
    健康检查
    """
    return {
        "status": "ok",
        "message": "测试 API 运行正常",
        "timestamp": datetime.now().isoformat()
    }
