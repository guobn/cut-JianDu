import io
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import requests
from PIL import Image
from celery.result import AsyncResult
from fastapi import HTTPException, UploadFile, status
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.models.preprocess import (
    PreprocessAngleItemResponse,
    PreprocessNormalizeRequest,
    PreprocessProgressResponse,
)
from app.utils.image_utils import ImageProcessor
from app.worker import celery_app


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}
PREPROCESS_KIND = "preprocessing"
REGULAR_KIND = "regular"
PREPROCESS_STAGES = {"draft", "angle_detected", "rotated", "normalized"}


def create_requests_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.verify = True
    return session


_http_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global _http_session
    if _http_session is None:
        _http_session = create_requests_session()
    return _http_session


def _require_supabase_config() -> None:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Supabase config is missing")


def _base_url() -> str:
    _require_supabase_config()
    return settings.supabase_url.rstrip("/")


def _auth_headers() -> Dict[str, str]:
    _require_supabase_config()
    return {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }


def _to_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    return value if isinstance(value, str) else str(value)


def _to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None
    return None


def _ensure_preprocess_group(group_id: str, user_id: str) -> Dict[str, Any]:
    params = {
        "id": f"eq.{group_id}",
        "user_id": f"eq.{user_id}",
        "kind": f"eq.{PREPROCESS_KIND}",
    }
    response = get_session().get(
        f"{_base_url()}/rest/v1/image_groups",
        headers=_auth_headers(),
        params=params,
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query preprocess group: {response.status_code}",
        )
    rows = response.json() or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preprocess group not found: {group_id}",
        )
    return rows[0]


def _update_group(group_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"
    response = get_session().patch(
        f"{_base_url()}/rest/v1/image_groups",
        headers=headers,
        params={"id": f"eq.{group_id}"},
        json=payload,
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update preprocess group: {response.status_code}",
        )
    rows = response.json() or []
    return rows[0] if rows else payload


def _merge_group_preprocess_params(group: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    current = group.get("preprocess_params") or {}
    if isinstance(current, str):
        try:
            current = json.loads(current)
        except json.JSONDecodeError:
            current = {}
    merged = dict(current)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def _parse_group_response(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _to_str(row.get("id")),
        "name": row.get("name", ""),
        "kind": row.get("kind", REGULAR_KIND),
        "preprocess_status": row.get("preprocess_status"),
        "total_images": row.get("total_images", 0) or 0,
        "created_at": _to_datetime(row.get("created_at")),
        "updated_at": _to_datetime(row.get("updated_at")),
    }


def _parse_source_image_row(row: Dict[str, Any]) -> Dict[str, Any]:
    image_id = _to_str(row.get("id"))
    group_id = _to_str(row.get("group_id")) or ""
    return {
        "id": image_id,
        "group_id": group_id,
        "filename": row.get("filename", ""),
        "file_url": f"/api/groups/{group_id}/images/{image_id}/file",
        "thumbnail_url": f"/api/groups/{group_id}/images/{image_id}/thumbnail",
        "storage_path": row.get("storage_path"),
        "width": row.get("width", 0) or 0,
        "height": row.get("height", 0) or 0,
        "format": row.get("format", "UNKNOWN"),
        "rotation_angle": row.get("rotation_angle"),
        "rotation_confidence": row.get("rotation_confidence"),
        "preprocess_skipped": bool(row.get("preprocess_skipped", False)),
        "created_at": _to_datetime(row.get("created_at")),
    }


def _generate_thumbnail(image_bytes: bytes, max_size: int = 800) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format=image.format or "PNG")
    return output.getvalue()


def _list_group_images(group_id: str) -> List[Dict[str, Any]]:
    response = get_session().get(
        f"{_base_url()}/rest/v1/source_images",
        headers=_auth_headers(),
        params={
            "group_id": f"eq.{group_id}",
            "select": "id,group_id,filename,storage_path,width,height,format,rotation_angle,rotation_confidence,preprocess_skipped,created_at",
            "order": "created_at.asc",
        },
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list images: {response.status_code}",
        )
    return [_parse_source_image_row(row) for row in (response.json() or [])]


def _update_group_total_images(group_id: str) -> int:
    rows = _list_group_images(group_id)
    total = len(rows)
    _update_group(group_id, {"total_images": total})
    return total


def _update_source_image(image_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"
    response = get_session().patch(
        f"{_base_url()}/rest/v1/source_images",
        headers=headers,
        params={"id": f"eq.{image_id}"},
        json=payload,
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update source image: {response.status_code}",
        )
    rows = response.json() or []
    return rows[0] if rows else payload


def _get_image_row(group_id: str, image_id: str) -> Dict[str, Any]:
    response = get_session().get(
        f"{_base_url()}/rest/v1/source_images",
        headers=_auth_headers(),
        params={"id": f"eq.{image_id}", "group_id": f"eq.{group_id}"},
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query image: {response.status_code}",
        )
    rows = response.json() or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {image_id}",
        )
    return rows[0]


def _resolve_local_image_path(group_id: str, image_row: Dict[str, Any]) -> Path:
    storage_path = image_row.get("storage_path")
    if storage_path and Path(storage_path).exists():
        return Path(storage_path)

    image_id = _to_str(image_row.get("id"))
    filename = image_row.get("filename", "")
    ext = Path(filename).suffix.lower()
    group_dir = Path(settings.upload_dir) / str(group_id)
    if ext:
        direct = group_dir / f"{image_id}{ext}"
        if direct.exists():
            return direct
    for candidate in ALLOWED_EXTENSIONS:
        path = group_dir / f"{image_id}{candidate}"
        if path.exists():
            return path
    raise FileNotFoundError(f"Local image file not found for {image_id}")


def _accepted_ids(group: Dict[str, Any]) -> List[str]:
    params = group.get("preprocess_params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}
    accepted = params.get("accepted_image_ids") or []
    return [str(item) for item in accepted]


def _build_angle_status(confidence: Optional[float]) -> str:
    confidence = float(confidence or 0.0)
    if confidence >= 0.7:
        return "auto_pass"
    if confidence >= 0.3:
        return "review_required"
    return "low_confidence"


def _build_review_state(image: Dict[str, Any], accepted_ids: List[str]) -> str:
    image_id = image["id"]
    if image.get("preprocess_skipped"):
        return "skipped"
    if image_id in accepted_ids:
        return "accepted"
    return "pending_review" if _build_angle_status(image.get("rotation_confidence")) != "auto_pass" else "pending"


def create_preprocess_group(name: str, user_id: str) -> Dict[str, Any]:
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"
    response = get_session().post(
        f"{_base_url()}/rest/v1/image_groups",
        headers=headers,
        json={
            "user_id": user_id,
            "name": name,
            "status": "created",
            "kind": PREPROCESS_KIND,
            "preprocess_status": "draft",
            "total_images": 0,
            "processed_images": 0,
            "preprocess_params": {"accepted_image_ids": []},
        },
    )
    if response.status_code >= 400:
        detail = response.text.strip() or response.reason or str(response.status_code)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create preprocess group: {response.status_code} {detail}",
        )
    rows = response.json() or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase returned an empty response while creating the preprocess group",
        )
    return _parse_group_response(rows[0])


def list_preprocess_groups(user_id: str) -> List[Dict[str, Any]]:
    response = get_session().get(
        f"{_base_url()}/rest/v1/image_groups",
        headers=_auth_headers(),
        params={
            "user_id": f"eq.{user_id}",
            "kind": f"eq.{PREPROCESS_KIND}",
            "order": "created_at.desc",
        },
    )
    if response.status_code >= 400:
        detail = response.text.strip() or response.reason or str(response.status_code)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list preprocess groups: {response.status_code} {detail}",
        )
    return [_parse_group_response(row) for row in (response.json() or [])]


async def upload_preprocess_images(group_id: str, user_id: str, files: List[UploadFile]) -> Dict[str, Any]:
    _ensure_preprocess_group(group_id, user_id)
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")
    if len(files) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At most 10 files are allowed")
    existing_images = _list_group_images(group_id)
    if len(existing_images) + len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A preprocess group can contain at most 10 images",
        )

    group_dir = Path(settings.upload_dir) / str(group_id)
    group_dir.mkdir(parents=True, exist_ok=True)

    uploaded_ids: List[str] = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Encountered a file without a filename")
        ext = Path(file.filename).suffix.lower() or ".jpg"
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.filename}",
            )

        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Empty file uploaded: {file.filename}",
            )

        image_id = str(uuid4())
        file_path = group_dir / f"{image_id}{ext}"
        file_path.write_bytes(content)

        thumb_path = None
        try:
            thumb_bytes = _generate_thumbnail(content, max_size=settings.thumbnail_size)
            thumb_path = group_dir / f"{image_id}_thumb{ext}"
            thumb_path.write_bytes(thumb_bytes)
        except Exception:
            thumb_path = None

        width = height = 0
        image_format = "UNKNOWN"
        try:
            image = Image.open(io.BytesIO(content))
            width, height = image.size
            image_format = image.format or "UNKNOWN"
        except Exception:
            pass

        headers = _auth_headers()
        headers["Prefer"] = "return=representation"
        response = get_session().post(
            f"{_base_url()}/rest/v1/source_images",
            headers=headers,
            json={
                "id": image_id,
                "group_id": group_id,
                "user_id": user_id,
                "filename": file.filename,
                "storage_path": str(file_path),
                "thumbnail_url": str(thumb_path) if thumb_path else None,
                "file_size": len(content),
                "width": width,
                "height": height,
                "format": image_format,
                "rotation_angle": None,
                "rotation_confidence": None,
                "preprocess_skipped": False,
            },
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to save image metadata: {response.status_code}",
            )
        uploaded_ids.append(image_id)

    total = _update_group_total_images(group_id)
    return {"uploaded": uploaded_ids, "total": total}


def enqueue_angle_detection(group_id: str, user_id: str) -> Dict[str, str]:
    group = _ensure_preprocess_group(group_id, user_id)
    images = _list_group_images(group_id)
    if not images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload images before detecting angles")

    try:
        async_result = celery_app.send_task("preprocess.detect_angles_batch", kwargs={"group_id": group_id})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to dispatch the Celery task: {exc}",
        ) from exc

    params = _merge_group_preprocess_params(
        group,
        {"detect_task_id": async_result.id, "accepted_image_ids": []},
    )
    _update_group(group_id, {"preprocess_status": "draft", "preprocess_params": params})
    return {"task_id": async_result.id}


def get_preprocess_progress(group_id: str, user_id: str) -> PreprocessProgressResponse:
    group = _ensure_preprocess_group(group_id, user_id)
    params = group.get("preprocess_params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}

    stage = group.get("preprocess_status") or "draft"
    task_id = params.get("detect_task_id")
    total_images = group.get("total_images", 0) or 0

    if task_id:
        result = AsyncResult(task_id, app=celery_app)
        if result.state == "PROGRESS":
            meta = result.info or {}
            total = int(meta.get("total", total_images) or total_images)
            done = int(meta.get("done", 0) or 0)
            percent = (done / total * 100.0) if total else 0.0
            return PreprocessProgressResponse(
                stage="detecting_angles",
                total=total,
                done=done,
                percent=percent,
                task_id=task_id,
            )
        if result.state == "FAILURE":
            return PreprocessProgressResponse(
                stage="failed",
                total=total_images,
                done=0,
                percent=0.0,
                task_id=task_id,
            )

    percent_map = {
        "draft": 0.0,
        "angle_detected": 100.0,
        "rotated": 100.0,
        "normalized": 100.0,
    }
    return PreprocessProgressResponse(
        stage=stage,
        total=total_images,
        done=total_images if stage in {"angle_detected", "rotated", "normalized"} else 0,
        percent=percent_map.get(stage, 0.0),
        task_id=task_id,
    )


def list_preprocess_angles(group_id: str, user_id: str) -> List[PreprocessAngleItemResponse]:
    group = _ensure_preprocess_group(group_id, user_id)
    accepted_ids = _accepted_ids(group)
    items: List[PreprocessAngleItemResponse] = []
    for image in _list_group_images(group_id):
        items.append(
            PreprocessAngleItemResponse(
                image_id=image["id"],
                filename=image["filename"],
                file_url=image["file_url"],
                thumbnail_url=image["thumbnail_url"],
                rotation_angle=image.get("rotation_angle"),
                rotation_confidence=image.get("rotation_confidence"),
                preprocess_skipped=bool(image.get("preprocess_skipped")),
                status=_build_angle_status(image.get("rotation_confidence")),
                review_state=_build_review_state(image, accepted_ids),
            )
        )
    return items


def patch_preprocess_angle(
    group_id: str,
    image_id: str,
    user_id: str,
    rotation_angle: Optional[float],
    preprocess_skipped: Optional[bool],
    accepted: Optional[bool],
) -> Dict[str, Any]:
    group = _ensure_preprocess_group(group_id, user_id)
    _get_image_row(group_id, image_id)

    payload: Dict[str, Any] = {}
    if rotation_angle is not None:
        payload["rotation_angle"] = float(rotation_angle)
    if preprocess_skipped is not None:
        payload["preprocess_skipped"] = bool(preprocess_skipped)
    if payload:
        _update_source_image(image_id, payload)

    accepted_ids = set(_accepted_ids(group))
    if preprocess_skipped:
        accepted_ids.discard(image_id)
    elif accepted is True or rotation_angle is not None:
        accepted_ids.add(image_id)
    elif accepted is False:
        accepted_ids.discard(image_id)

    merged = _merge_group_preprocess_params(group, {"accepted_image_ids": sorted(accepted_ids)})
    _update_group(group_id, {"preprocess_params": merged})
    refreshed = _parse_source_image_row(_get_image_row(group_id, image_id))
    return {
        "image_id": refreshed["id"],
        "rotation_angle": refreshed.get("rotation_angle"),
        "preprocess_skipped": refreshed.get("preprocess_skipped"),
        "status": _build_angle_status(refreshed.get("rotation_confidence")),
        "review_state": _build_review_state(refreshed, sorted(accepted_ids)),
    }


def apply_group_rotation(group_id: str, user_id: str) -> Dict[str, int]:
    from app.services.rotation_service import RotationService

    group = _ensure_preprocess_group(group_id, user_id)
    images = _list_group_images(group_id)
    accepted_ids = set(_accepted_ids(group))
    rotation_service = RotationService()
    rotated = 0
    skipped = 0

    for image in images:
        image_id = image["id"]
        if image.get("preprocess_skipped"):
            skipped += 1
            continue
        confidence_status = _build_angle_status(image.get("rotation_confidence"))
        if confidence_status != "auto_pass" and image_id not in accepted_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image {image['filename']} still requires review",
            )
        angle = float(image.get("rotation_angle") or 0.0)
        local_path = _resolve_local_image_path(group_id, _get_image_row(group_id, image_id))
        source = ImageProcessor.load_image(local_path)
        corrected = rotation_service.rotate_image(source, -angle)
        ImageProcessor.save_image(corrected, local_path)
        rotated += 1

    merged = _merge_group_preprocess_params(group, {"accepted_image_ids": None, "detect_task_id": None})
    _update_group(group_id, {"preprocess_status": "rotated", "preprocess_params": merged})
    return {"rotated": rotated, "skipped": skipped}


def normalize_group_images(group_id: str, user_id: str, params: PreprocessNormalizeRequest) -> Dict[str, int]:
    from app.services.preprocess_normalization import normalize_to_square

    _ensure_preprocess_group(group_id, user_id)
    normalized = 0

    for image_row in _list_group_images(group_id):
        local_path = _resolve_local_image_path(group_id, _get_image_row(group_id, image_row["id"]))
        image = ImageProcessor.load_image(local_path)
        normalized_image = normalize_to_square(
            image=image,
            target_size=params.target_size,
            keep_ratio=params.keep_ratio,
            interpolation=params.interp,
            padding=params.padding,
        )
        ImageProcessor.save_image(normalized_image, local_path)
        normalized += 1

    _update_group(
        group_id,
        {
            "preprocess_status": "normalized",
            "preprocess_params": {
                "target_size": params.target_size,
                "keep_ratio": params.keep_ratio,
                "interp": params.interp,
                "padding": params.padding,
            },
        },
    )
    return {"normalized": normalized}


def convert_preprocess_group(group_id: str, user_id: str) -> Dict[str, Any]:
    _ensure_preprocess_group(group_id, user_id)
    headers = _auth_headers()
    headers["Prefer"] = "return=representation"
    response = get_session().patch(
        f"{_base_url()}/rest/v1/image_groups",
        headers=headers,
        params={
            "id": f"eq.{group_id}",
            "user_id": f"eq.{user_id}",
            "kind": f"eq.{PREPROCESS_KIND}",
            "preprocess_status": "eq.normalized",
        },
        json={"kind": REGULAR_KIND, "preprocess_status": None},
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to convert preprocess group: {response.status_code}",
        )
    rows = response.json() or []
    return {"converted": bool(rows), "group_id": group_id}


def delete_preprocess_group(group_id: str, user_id: str) -> Dict[str, Any]:
    _ensure_preprocess_group(group_id, user_id)
    images = _list_group_images(group_id)
    group_dir = Path(settings.upload_dir) / str(group_id)
    result_dir = Path(settings.result_dir) / str(group_id)

    for image in images:
        get_session().delete(
            f"{_base_url()}/rest/v1/source_images",
            headers=_auth_headers(),
            params={"id": f"eq.{image['id']}"},
        )

    get_session().delete(
        f"{_base_url()}/rest/v1/image_groups",
        headers=_auth_headers(),
        params={"id": f"eq.{group_id}", "user_id": f"eq.{user_id}"},
    )

    if group_dir.exists():
        shutil.rmtree(group_dir, ignore_errors=True)
    if result_dir.exists():
        shutil.rmtree(result_dir, ignore_errors=True)

    return {"deleted": True, "group_id": group_id}


def list_images_for_task(group_id: str) -> List[Dict[str, Any]]:
    return _list_group_images(group_id)


def update_image_angle(image_id: str, angle: float, confidence: float) -> None:
    _update_source_image(
        image_id,
        {
            "rotation_angle": float(angle),
            "rotation_confidence": float(confidence),
            "preprocess_skipped": False,
        },
    )


def set_group_status(group_id: str, stage: str) -> None:
    if stage not in PREPROCESS_STAGES:
        raise ValueError(f"Unsupported preprocess stage: {stage}")
    response = get_session().get(
        f"{_base_url()}/rest/v1/image_groups",
        headers=_auth_headers(),
        params={"id": f"eq.{group_id}", "select": "preprocess_params"},
    )
    rows = response.json() if response.status_code < 400 else []
    current = rows[0] if rows else {}
    params = _merge_group_preprocess_params(current, {"detect_task_id": None})
    _update_group(group_id, {"preprocess_status": stage, "preprocess_params": params})
