from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.ping import router as ping_router
from app.api.routes import user
from app.api import images, segmentation, rotation, normalization, metadata, tasks, test, groups, cache, recognition
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    description="提供图像切割、旋转校正、尺寸归一化等功能",
    version=settings.app_version
)


# allow_credentials=True 时不能使用 allow_origins=["*"]，用正则匹配本机任意端口
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# 注册原有路由
app.include_router(ping_router)
app.include_router(user.router, prefix="/api")

# 注册图像处理路由
app.include_router(images.router)
app.include_router(segmentation.router)
app.include_router(rotation.router)
app.include_router(normalization.router)
app.include_router(metadata.router)

# 注册图像组和缓存路由
app.include_router(groups.router)
app.include_router(cache.router)

# 注册 recognition 批量检测路由
app.include_router(recognition.router)

# 注册任务查询路由
app.include_router(tasks.router)

# 注册测试路由（无需鉴权）
app.include_router(test.router)

# 挂载结果图像静态文件目录，便于前端直接访问处理后的图片
# 例如：/results/normalized/xxx.png 或 /results/rotations/xxx.png
app.mount("/results", StaticFiles(directory=settings.result_dir), name="results")


@app.get("/")
def read_root():
    return {
        "message": "古文字简牍图像处理 API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.app_version
    }
