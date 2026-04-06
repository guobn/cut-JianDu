from fastapi import APIRouter, Depends

from app.core.auth import get_current_user

router = APIRouter()


@router.get("/me")
def read_current_user(user=Depends(get_current_user)):
    return {
        "message": "鉴权成功",
        "user": user
    }
