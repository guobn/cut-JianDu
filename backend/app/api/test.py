"""
Test API routes without authentication, used for local verification.
"""
from datetime import datetime
from pathlib import Path
import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.models.detection import BoundingBox, DetectionParameters, DetectionResult, ModelType
from app.models.image import ImageUploadResponse
from app.models.normalization import NormalizationResult
from app.models.rotation import RotationCorrectionResult, RotationDetectionResult
from app.services.image_service import ImageService
from app.services.normalization_service import NormalizationService
from app.services.rotation_service import RotationService
from app.services.segmentation_service import SegmentationService
from app.utils.file_utils import FileManager
from app.utils.image_utils import ImageProcessor

router = APIRouter(prefix="/api/test", tags=["test"])

image_service = ImageService()
segmentation_service = SegmentationService()
rotation_service = RotationService()
normalization_service = NormalizationService()


def _build_detection_params(mode: str, model_type: Optional[str]) -> DetectionParameters:
    if mode == "single-character":
        params = DetectionParameters(
            min_width=20,
            min_height=20,
            max_width=150,
            max_height=150,
            aspect_ratio_min=0.3,
            aspect_ratio_max=3.0,
        )
    else:
        params = DetectionParameters()

    if model_type:
        try:
            params.model_type = ModelType(model_type)
        except ValueError:
            pass

    return params


@router.post("/upload", response_model=ImageUploadResponse)
async def test_upload_image(file: UploadFile = File(...)):
    if not FileManager.is_valid_image_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_FORMAT",
                "error_message": "Unsupported image format",
                "suggested_solution": "Please upload JPG, PNG, TIFF, or BMP files",
            },
        )

    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "error_message": "File size exceeds limit",
                "suggested_solution": f"Please upload files smaller than {settings.max_file_size // (1024 * 1024)} MB",
            },
        )

    image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    try:
        return await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "UPLOAD_FAILED",
                "error_message": f"Image upload failed: {exc}",
                "suggested_solution": "Please check the input file and retry",
            },
        ) from exc


@router.post("/detect", response_model=DetectionResult)
async def test_detect(
    file: UploadFile = File(...),
    mode: str = Form("single-slip"),
    model_type: Optional[str] = Form(None),
):
    try:
        content = await file.read()
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )

        image = image_service.load_image(image_id)
        params = _build_detection_params(mode, model_type)
        start_time = time.time()

        if mode == "single-slip":
            detections = segmentation_service.detect_single_slips(image=image, params=params)
        else:
            detections = segmentation_service.detect_single_characters(image=image, params=params)

        return DetectionResult(
            detection_id=f"det_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
            image_id=image_id,
            mode=mode,
            detections=detections,
            parameters=params.model_dump(mode="json"),
            total_count=len(detections),
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DETECTION_FAILED",
                "error_message": f"Detection failed: {exc}",
                "suggested_solution": "Please check image quality and model configuration",
            },
        ) from exc


@router.post("/cut")
async def test_cut(
    image_id: str = Form(...),
    bounding_boxes: str = Form(...),
    segment_type: str = Form("slip"),
):
    try:
        box_dicts = json.loads(bounding_boxes)
        parsed_boxes = [BoundingBox(**box) for box in box_dicts]
        image = image_service.load_image(image_id)

        regions = segmentation_service.extract_regions(
            image=image,
            bounding_boxes=parsed_boxes,
            add_padding=False,
            padding_size=10,
        )
        output_dir = Path(settings.result_dir) / f"test_{segment_type}" / image_id
        results = await segmentation_service.save_segmented_regions(
            regions=regions,
            bounding_boxes=parsed_boxes,
            output_dir=output_dir,
            output_format="png",
            prefix=image_id,
        )

        return {
            "success": True,
            "message": f"Successfully cut {len(results)} regions",
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CUT_FAILED",
                "error_message": f"Cut failed: {exc}",
                "suggested_solution": "Please check bounding box parameters",
            },
        ) from exc


@router.post("/rotation/detect", response_model=RotationDetectionResult)
async def test_detect_rotation(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )

        image = image_service.load_image(image_id)
        start_time = time.time()
        detected_angle, confidence = rotation_service.detect_rotation_angle(image)

        return RotationDetectionResult(
            image_id=image_id,
            detected_angle=detected_angle,
            confidence=confidence,
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "ROTATION_DETECT_FAILED",
                "error_message": f"Rotation detection failed: {exc}",
                "suggested_solution": "Please check the input image",
            },
        ) from exc


@router.post("/rotation/correct", response_model=RotationCorrectionResult)
async def test_correct_rotation(
    file: UploadFile = File(...),
    angle: Optional[float] = Form(None),
    auto_crop: bool = Form(True),
):
    try:
        content = await file.read()
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )

        image = image_service.load_image(image_id)
        start_time = time.time()
        if angle is None:
            angle, _ = rotation_service.detect_rotation_angle(image)

        corrected_image, corrected_angle = rotation_service.correct_rotation(
            image=image,
            auto_detect=False,
            angle=angle,
            auto_crop=auto_crop,
        )

        correction_id = f"rot_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        output_dir = Path(settings.result_dir) / "rotations"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{correction_id}.png"
        ImageProcessor.save_image(corrected_image, output_path)

        return RotationCorrectionResult(
            correction_id=correction_id,
            image_id=image_id,
            original_angle=angle,
            corrected_angle=corrected_angle,
            output_path=str(output_path),
            width=corrected_image.shape[1],
            height=corrected_image.shape[0],
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "ROTATION_CORRECT_FAILED",
                "error_message": f"Rotation correction failed: {exc}",
                "suggested_solution": "Please check the input parameters",
            },
        ) from exc


@router.post("/normalization/normalize", response_model=NormalizationResult)
async def test_normalize(
    file: UploadFile = File(...),
    target_width: int = Form(800),
    target_height: int = Form(1200),
    keep_aspect_ratio: bool = Form(True),
    padding_color: str = Form("white"),
):
    try:
        content = await file.read()
        image_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        await image_service.save_image(
            image_id=image_id,
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )

        image = image_service.load_image(image_id)
        start_time = time.time()
        normalized_image = normalization_service.normalize_size(
            image=image,
            target_width=target_width,
            target_height=target_height,
            keep_aspect_ratio=keep_aspect_ratio,
            padding_color=padding_color,
        )

        normalization_id = f"norm_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        output_dir = Path(settings.result_dir) / "normalized"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{normalization_id}.png"
        ImageProcessor.save_image(normalized_image, output_path)

        return NormalizationResult(
            normalization_id=normalization_id,
            image_id=image_id,
            original_width=image.shape[1],
            original_height=image.shape[0],
            target_width=target_width,
            target_height=target_height,
            output_path=str(output_path),
            processing_time=time.time() - start_time,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "NORMALIZATION_FAILED",
                "error_message": f"Normalization failed: {exc}",
                "suggested_solution": "Please check the input parameters",
            },
        ) from exc


@router.get("/image/{image_id}")
async def test_get_image(image_id: str):
    try:
        file_path = image_service.get_image_path(image_id)
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".bmp": "image/bmp",
        }
        return FileResponse(
            path=file_path,
            media_type=media_type_map.get(file_path.suffix.lower(), "image/jpeg"),
            filename=file_path.name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "IMAGE_NOT_FOUND",
                "error_message": f"Image not found: {image_id}",
                "suggested_solution": "Please check whether the image_id is correct",
            },
        ) from exc


@router.get("/health")
async def test_health():
    return {
        "status": "ok",
        "message": "Test API is running normally",
        "timestamp": datetime.now().isoformat(),
    }
