from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/ping")
def ping():
    return {"ok": True, "message": "pong"}
