from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.auth import get_current_user
from app.models.preprocess import (
    PreprocessAngleItemResponse,
    PreprocessAnglePatchRequest,
    PreprocessGroupCreate,
    PreprocessGroupResponse,
    PreprocessNormalizeRequest,
    PreprocessProgressResponse,
)
from app.services.preprocess_service import (
    apply_group_rotation,
    convert_preprocess_group,
    create_preprocess_group,
    delete_preprocess_group,
    enqueue_angle_detection,
    get_preprocess_progress,
    list_preprocess_angles,
    list_preprocess_groups,
    normalize_group_images,
    patch_preprocess_angle,
    upload_preprocess_images,
)

router = APIRouter(prefix="/api/preprocess", tags=["preprocess"])


def _user_id(user) -> str:
    user_id = user.get("id") if isinstance(user, dict) else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")
    return str(user_id)


@router.post("/groups", response_model=PreprocessGroupResponse)
async def create_group(payload: PreprocessGroupCreate, user=Depends(get_current_user)):
    try:
        return create_preprocess_group(payload.name, _user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create preprocess group: {exc}") from exc


@router.get("/groups", response_model=list[PreprocessGroupResponse])
async def list_groups(user=Depends(get_current_user)):
    try:
        return list_preprocess_groups(_user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list preprocess groups: {exc}") from exc


@router.post("/groups/{group_id}/upload")
async def upload_group_images(group_id: str, files: list[UploadFile] = File(...), user=Depends(get_current_user)):
    try:
        return await upload_preprocess_images(group_id, _user_id(user), files)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload images: {exc}") from exc


@router.post("/groups/{group_id}/detect-angles")
async def detect_angles(group_id: str, user=Depends(get_current_user)):
    try:
        return enqueue_angle_detection(group_id, _user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to detect angles: {exc}") from exc


@router.get("/groups/{group_id}/progress", response_model=PreprocessProgressResponse)
async def get_progress(group_id: str, user=Depends(get_current_user)):
    try:
        return get_preprocess_progress(group_id, _user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch progress: {exc}") from exc


@router.get("/groups/{group_id}/angles", response_model=list[PreprocessAngleItemResponse])
async def get_angles(group_id: str, user=Depends(get_current_user)):
    try:
        return list_preprocess_angles(group_id, _user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch angles: {exc}") from exc


@router.patch("/groups/{group_id}/angles/{image_id}")
async def patch_angle(group_id: str, image_id: str, payload: PreprocessAnglePatchRequest, user=Depends(get_current_user)):
    try:
        return patch_preprocess_angle(
            group_id=group_id,
            image_id=image_id,
            user_id=_user_id(user),
            rotation_angle=payload.rotation_angle,
            preprocess_skipped=payload.preprocess_skipped,
            accepted=payload.accepted,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update angle: {exc}") from exc


@router.post("/groups/{group_id}/apply-rotation")
async def apply_rotation(group_id: str, user=Depends(get_current_user)):
    try:
        return apply_group_rotation(group_id, _user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to apply rotation: {exc}") from exc


@router.post("/groups/{group_id}/normalize")
async def normalize(group_id: str, payload: PreprocessNormalizeRequest, user=Depends(get_current_user)):
    try:
        return normalize_group_images(group_id, _user_id(user), payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to normalize images: {exc}") from exc


@router.post("/groups/{group_id}/convert")
async def convert(group_id: str, user=Depends(get_current_user)):
    try:
        return convert_preprocess_group(group_id, _user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to convert preprocess group: {exc}") from exc


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str, user=Depends(get_current_user)):
    try:
        return delete_preprocess_group(group_id, _user_id(user))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete preprocess group: {exc}") from exc
