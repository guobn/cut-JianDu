"""Celery 异步任务定义"""

import time
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import requests
from celery import group

from app.worker import celery_app
from app.models.detection import BoundingBox, DetectionParameters, DetectionResult
from app.models.rotation import RotationDetectionResult, RotationCorrectionResult
from app.services.segmentation_service import SegmentationService
from app.services.rotation_service import RotationService
from app.services.image_service import ImageService
from app.utils.image_utils import ImageProcessor
from app.utils.file_utils import FileManager
from app.config import settings
from pathlib import Path

log = logging.getLogger(__name__)

# 服务实例（在 worker 进程中复用）
_segmentation_service = None
_rotation_service = None
_image_service = None


def _get_segmentation_service() -> SegmentationService:
    """获取 SegmentationService 单例"""
    global _segmentation_service
    if _segmentation_service is None:
        _segmentation_service = SegmentationService()
    return _segmentation_service


def _get_rotation_service() -> RotationService:
    """获取 RotationService 单例"""
    global _rotation_service
    if _rotation_service is None:
        _rotation_service = RotationService()
    return _rotation_service


def _get_image_service() -> ImageService:
    """获取 ImageService 单例"""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service


@celery_app.task(bind=True, name="detect_single_slips_task")
def detect_single_slips_task(
    self,
    image_data: bytes,
    image_id: str,
    parameters: Optional[dict] = None
) -> dict:
    """
    异步检测单支简牍

    Args:
        self: Celery task 实例
        image_data: 图像字节数据
        image_id: 图像 ID
        parameters: 检测参数字典

    Returns:
        检测结果字典
    """
    try:
        # 更新状态：开始处理
        self.update_state(state="STARTED", meta={"progress": 0.1})

        # 解析参数
        params = DetectionParameters(**parameters) if parameters else DetectionParameters()

        # 加载图像
        image = ImageProcessor.load_image_from_bytes(image_data)
        h, w = image.shape[:2]
        log.info("detect_single_slips_task: image_id=%s, 尺寸=%sx%s", image_id, w, h)

        # 进度更新：加载模型 20%
        self.update_state(state="STARTED", meta={"progress": 0.2})

        # 执行检测
        start_time = time.time()
        segmentation_service = _get_segmentation_service()

        # 进度更新：开始检测 50%
        self.update_state(state="STARTED", meta={"progress": 0.5})

        bounding_boxes = segmentation_service.detect_single_slips(image, params)

        # 进度更新：处理结果 80%
        self.update_state(state="STARTED", meta={"progress": 0.8})

        processing_time = time.time() - start_time

        # 生成检测 ID
        detection_id = f"det_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 构建结果
        result = DetectionResult(
            detection_id=detection_id,
            image_id=image_id,
            mode="single-slip",
            detections=bounding_boxes,
            parameters=params.model_dump(),
            total_count=len(bounding_boxes),
            processing_time=processing_time,
            created_at=datetime.now(),
        )

        log.info("detect_single_slips_task 完成: total_count=%s", result.total_count)
        return result.model_dump()

    except Exception as e:
        log.exception("detect_single_slips_task 失败")
        raise


@celery_app.task(bind=True, name="detect_single_characters_task")
def detect_single_characters_task(
    self,
    image_data: bytes,
    image_id: str,
    parameters: Optional[dict] = None
) -> dict:
    """
    异步检测单字符

    Args:
        self: Celery task 实例
        image_data: 图像字节数据
        image_id: 图像 ID
        parameters: 检测参数字典

    Returns:
        检测结果字典
    """
    try:
        self.update_state(state="STARTED", meta={"progress": 0.1})

        params = DetectionParameters(**parameters) if parameters else DetectionParameters()

        image = ImageProcessor.load_image_from_bytes(image_data)
        h, w = image.shape[:2]
        log.info("detect_single_characters_task: image_id=%s, 尺寸=%sx%s", image_id, w, h)

        # 进度更新：加载模型 20%
        self.update_state(state="STARTED", meta={"progress": 0.2})

        start_time = time.time()
        segmentation_service = _get_segmentation_service()

        # 进度更新：开始检测 50%
        self.update_state(state="STARTED", meta={"progress": 0.5})

        bounding_boxes = segmentation_service.detect_single_characters(image, params)

        # 进度更新：处理结果 80%
        self.update_state(state="STARTED", meta={"progress": 0.8})

        processing_time = time.time() - start_time

        detection_id = f"det_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        result = DetectionResult(
            detection_id=detection_id,
            image_id=image_id,
            mode="single-character",
            detections=bounding_boxes,
            parameters=params.model_dump(),
            total_count=len(bounding_boxes),
            processing_time=processing_time,
            created_at=datetime.now(),
        )

        log.info("detect_single_characters_task 完成: total_count=%s", result.total_count)
        return result.model_dump()

    except Exception as e:
        log.exception("detect_single_characters_task 失败")
        raise


@celery_app.task(bind=True, name="detect_rotation_angle_task")
def detect_rotation_angle_task(
    self,
    image_id: str,
    user_id: Optional[str] = None
) -> dict:
    """
    异步检测图像倾斜角度

    Args:
        self: Celery task 实例
        image_id: 图像 ID
        user_id: 用户 ID（用于 Supabase 回退）

    Returns:
        角度检测结果字典
    """
    try:
        self.update_state(state="STARTED", meta={"progress": 0.1})

        # 加载图像（优先本地，不存在且已登录则从 Supabase 拉取）
        image_service = _get_image_service()
        image = image_service.load_image_with_supabase_fallback(image_id, user_id)

        # 进度更新：读取图像 30%
        self.update_state(state="STARTED", meta={"progress": 0.3})

        start_time = time.time()
        rotation_service = _get_rotation_service()

        # 进度更新：计算角度 60%
        self.update_state(state="STARTED", meta={"progress": 0.6})

        angle, confidence = rotation_service.detect_rotation_angle(image)
        processing_time = time.time() - start_time

        # 进度更新：完成 100%
        self.update_state(state="STARTED", meta={"progress": 1.0})

        result = RotationDetectionResult(
            image_id=image_id,
            detected_angle=angle,
            confidence=confidence,
            processing_time=processing_time,
            created_at=datetime.now()
        )

        log.info("detect_rotation_angle_task 完成: angle=%.2f, confidence=%.2f", angle, confidence)
        return result.model_dump()

    except Exception as e:
        log.exception("detect_rotation_angle_task 失败")
        raise


@celery_app.task(bind=True, name="correct_rotation_task")
def correct_rotation_task(
    self,
    image_id: str,
    angle: Optional[float] = None,
    auto_crop: bool = True,
    user_id: Optional[str] = None
) -> dict:
    """
    异步执行旋转校正

    Args:
        self: Celery task 实例
        image_id: 图像 ID
        angle: 指定的旋转角度（None 则自动检测）
        auto_crop: 是否自动裁剪黑边
        user_id: 用户 ID（用于 Supabase 回退）

    Returns:
        旋转校正结果字典
    """
    try:
        self.update_state(state="STARTED", meta={"progress": 0.1})

        # 加载图像
        image_service = _get_image_service()
        image = image_service.load_image_with_supabase_fallback(image_id, user_id)
        image_path = image_service.get_image_path(image_id)

        # 进度更新：读取图像 30%
        self.update_state(state="STARTED", meta={"progress": 0.3})

        start_time = time.time()
        rotation_service = _get_rotation_service()

        # 进度更新：计算角度 60%
        self.update_state(state="STARTED", meta={"progress": 0.6})

        # 执行旋转校正
        auto_detect = angle is None
        corrected_image, rotation_angle = rotation_service.correct_rotation(
            image,
            auto_detect=auto_detect,
            angle=angle,
            auto_crop=auto_crop
        )

        # 进度更新：写入结果 90%
        self.update_state(state="STARTED", meta={"progress": 0.9})

        # 生成校正 ID
        correction_id = f"rot_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 保存校正后的图像
        output_dir = Path(settings.result_dir) / "rotations"
        output_dir.mkdir(parents=True, exist_ok=True)

        ext = image_path.suffix
        output_filename = f"{correction_id}{ext}"
        output_path = output_dir / output_filename

        ImageProcessor.save_image(corrected_image, output_path)

        processing_time = time.time() - start_time

        # 获取图像尺寸
        height, width = corrected_image.shape[:2]

        # 进度更新：完成 100%
        self.update_state(state="STARTED", meta={"progress": 1.0})

        result = RotationCorrectionResult(
            correction_id=correction_id,
            image_id=image_id,
            original_angle=rotation_angle,
            corrected_angle=0.0,
            output_path=str(output_path),
            width=width,
            height=height,
            processing_time=processing_time,
            created_at=datetime.now()
        )

        log.info("correct_rotation_task 完成: correction_id=%s", correction_id)
        return result.model_dump()

    except Exception as e:
        log.exception("correct_rotation_task 失败")
        raise


# ============================================
# 批量切割任务（使用 celery.group 并行）
# ============================================

def _get_source_images_from_supabase(group_id: str) -> List[dict]:
    """
    从 Supabase 获取组内所有源图像

    Args:
        group_id: 图像组 ID

    Returns:
        源图像列表
    """
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    url = f"{base_url}/rest/v1/source_images"
    params = {"group_id": f"eq.{group_id}"}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        log.error("获取源图像失败: %s %s", resp.status_code, resp.text[:200])
        return []
    return resp.json() or []


def _write_segment_to_supabase(segment_data: dict) -> Optional[dict]:
    """
    将片段结果写入 Supabase segments 表

    Args:
        segment_data: 片段数据字典

    Returns:
        插入后的片段记录
    """
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Prefer": "return=representation",
    }
    url = f"{base_url}/rest/v1/segments"
    resp = requests.post(url, headers=headers, json=segment_data)
    if resp.status_code >= 400:
        log.error("写入片段失败: %s %s", resp.status_code, resp.text[:200])
        return None
    return resp.json()[0] if resp.json() else None


def _update_group_processed_count(group_id: str, increment: int = 1) -> None:
    """
    更新图像组的 processed_images 计数

    Args:
        group_id: 图像组 ID
        increment: 增量（可为负数）
    """
    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    url = f"{base_url}/rest/v1/image_groups"
    params = {"id": f"eq.{group_id}"}
    # 使用 RPC 或直接更新，这里使用数学操作
    resp = requests.patch(
        url,
        headers=headers,
        params=params,
        json={"processed_images": {"increment": increment}}
    )
    if resp.status_code >= 400:
        log.error("更新 processed_images 失败: %s %s", resp.status_code, resp.text[:200])


def _load_image_bytes(group_id: str, filename: str) -> Optional[bytes]:
    """
    从本地存储加载图像字节数据

    Args:
        group_id: 图像组 ID
        filename: 文件名

    Returns:
        图像字节数据，失败返回 None
    """
    try:
        image_path = Path(settings.upload_dir) / group_id / filename
        if not image_path.exists():
            log.error("图像文件不存在: %s", image_path)
            return None
        with open(image_path, "rb") as f:
            return f.read()
    except Exception as e:
        log.exception("加载图像失败: %s", image_path)
        return None


@celery_app.task(bind=True, name="batch_segment_slips_task")
def batch_segment_slips_task(
    self,
    group_id: str,
    config: dict
) -> dict:
    """
    批量检测单支简牍任务

    Args:
        self: Celery task 实例
        group_id: 图像组 ID
        config: 检测配置字典

    Returns:
        { total, completed, failed, errors: [...] }
    """
    try:
        # 更新状态：开始处理
        self.update_state(state="STARTED", meta={"progress": 0.0, "total": 0, "completed": 0, "failed": 0})

        # 1. 获取组内所有源图像
        source_images = _get_source_images_from_supabase(group_id)
        total = len(source_images)

        if total == 0:
            return {"total": 0, "completed": 0, "failed": 0, "errors": ["组内无图像"]}

        log.info("batch_segment_slips_task: group_id=%s, 总图像数=%s", group_id, total)

        # 2. 构建并行任务组
        subtasks = []
        for img in source_images:
            image_id = img["id"]
            filename = img["filename"]
            # 加载图像字节
            image_data = _load_image_bytes(group_id, filename)
            if image_data is None:
                # 如果加载失败，创建失败任务
                subtasks.append(
                    _failed_slips_subtask.s(image_id, "图像加载失败")
                )
            else:
                # 创建检测子任务
                subtasks.append(
                    _process_single_slips.s(image_data, image_id, config)
                )

        # 3. 使用 celery.group() 并行执行
        self.update_state(state="STARTED", meta={"progress": 0.1, "total": total, "completed": 0, "failed": 0})

        # 执行组任务
        job = group(subtasks)
        results = job.apply_async()

        # 4. 等待所有子任务完成并收集结果
        completed = 0
        failed = 0
        errors = []

        for i, result in enumerate(results.results):
            try:
                if result is None or isinstance(result, Exception):
                    failed += 1
                    errors.append(str(result) if result else "未知错误")
                else:
                    # result 格式: { success: bool, image_id: str, segments_count: int, error: str }
                    if result.get("success"):
                        completed += 1
                    else:
                        failed += 1
                        errors.append(f"{result.get('image_id')}: {result.get('error')}")
            except Exception as e:
                failed += 1
                errors.append(str(e))

            # 更新进度
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": (i + 1) / total,
                    "total": total,
                    "completed": completed,
                    "failed": failed
                }
            )

        log.info("batch_segment_slips_task 完成: total=%s, completed=%s, failed=%s", total, completed, failed)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "errors": errors
        }

    except Exception as e:
        log.exception("batch_segment_slips_task 失败")
        raise


@celery_app.task(bind=True, name="batch_segment_chars_task")
def batch_segment_chars_task(
    self,
    group_id: str,
    config: dict
) -> dict:
    """
    批量检测单字符任务

    Args:
        self: Celery task 实例
        group_id: 图像组 ID
        config: 检测配置字典

    Returns:
        { total, completed, failed, errors: [...] }
    """
    try:
        # 更新状态：开始处理
        self.update_state(state="STARTED", meta={"progress": 0.0, "total": 0, "completed": 0, "failed": 0})

        # 1. 获取组内所有源图像
        source_images = _get_source_images_from_supabase(group_id)
        total = len(source_images)

        if total == 0:
            return {"total": 0, "completed": 0, "failed": 0, "errors": ["组内无图像"]}

        log.info("batch_segment_chars_task: group_id=%s, 总图像数=%s", group_id, total)

        # 2. 构建并行任务组
        subtasks = []
        for img in source_images:
            image_id = img["id"]
            filename = img["filename"]
            # 加载图像字节
            image_data = _load_image_bytes(group_id, filename)
            if image_data is None:
                # 如果加载失败，创建失败任务
                subtasks.append(
                    _failed_chars_subtask.s(image_id, "图像加载失败")
                )
            else:
                # 创建检测子任务
                subtasks.append(
                    _process_single_chars.s(image_data, image_id, config)
                )

        # 3. 使用 celery.group() 并行执行
        self.update_state(state="STARTED", meta={"progress": 0.1, "total": total, "completed": 0, "failed": 0})

        # 执行组任务
        job = group(subtasks)
        results = job.apply_async()

        # 4. 等待所有子任务完成并收集结果
        completed = 0
        failed = 0
        errors = []

        for i, result in enumerate(results.results):
            try:
                if result is None or isinstance(result, Exception):
                    failed += 1
                    errors.append(str(result) if result else "未知错误")
                else:
                    # result 格式: { success: bool, image_id: str, segments_count: int, error: str }
                    if result.get("success"):
                        completed += 1
                    else:
                        failed += 1
                        errors.append(f"{result.get('image_id')}: {result.get('error')}")
            except Exception as e:
                failed += 1
                errors.append(str(e))

            # 更新进度
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": (i + 1) / total,
                    "total": total,
                    "completed": completed,
                    "failed": failed
                }
            )

        log.info("batch_segment_chars_task 完成: total=%s, completed=%s, failed=%s", total, completed, failed)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "errors": errors
        }

    except Exception as e:
        log.exception("batch_segment_chars_task 失败")
        raise


# ============================================
# 子任务：处理单张图像的检测和结果写入
# ============================================

@celery_app.task(bind=True, name="_process_single_slips")
def _process_single_slips(
    self,
    image_data: bytes,
    image_id: str,
    config: dict
) -> dict:
    """
    处理单张图像的单支检测并写入结果

    Args:
        self: Celery task 实例
        image_data: 图像字节数据
        image_id: 图像 ID
        config: 检测配置

    Returns:
        { success: bool, image_id: str, segments_count: int, error: str }
    """
    try:
        # 调用检测任务
        detection_result = detect_single_slips_task.s(image_data, image_id, config).apply()

        if detection_result is None or isinstance(detection_result, Exception):
            return {"success": False, "image_id": image_id, "segments_count": 0, "error": str(detection_result)}

        # detection_result 是检测结果字典，包含 detections 列表
        detections = detection_result.get("detections", [])
        segments_count = 0

        # 将检测结果写入 segments 表
        for i, bbox in enumerate(detections):
            segment_data = {
                "source_image_id": image_id,
                "image_id": image_id,
                "segment_type": "slip",
                "segment_index": i,
                "bbox_x": bbox.x,
                "bbox_y": bbox.y,
                "bbox_width": bbox.width,
                "bbox_height": bbox.height,
                "validated": False,
            }
            if _write_segment_to_supabase(segment_data):
                segments_count += 1

        # 更新组的已处理图像计数
        _update_group_processed_count(image_id.split("-")[0] if "-" in image_id else "", 1)

        return {"success": True, "image_id": image_id, "segments_count": segments_count, "error": ""}

    except Exception as e:
        log.exception("_process_single_slips 失败: image_id=%s", image_id)
        return {"success": False, "image_id": image_id, "segments_count": 0, "error": str(e)}


@celery_app.task(bind=True, name="_process_single_chars")
def _process_single_chars(
    self,
    image_data: bytes,
    image_id: str,
    config: dict
) -> dict:
    """
    处理单张图像的单字符检测并写入结果

    Args:
        self: Celery task 实例
        image_data: 图像字节数据
        image_id: 图像 ID
        config: 检测配置

    Returns:
        { success: bool, image_id: str, segments_count: int, error: str }
    """
    try:
        # 调用检测任务
        detection_result = detect_single_characters_task.s(image_data, image_id, config).apply()

        if detection_result is None or isinstance(detection_result, Exception):
            return {"success": False, "image_id": image_id, "segments_count": 0, "error": str(detection_result)}

        # detection_result 是检测结果字典，包含 detections 列表
        detections = detection_result.get("detections", [])
        segments_count = 0

        # 将检测结果写入 segments 表
        for i, bbox in enumerate(detections):
            segment_data = {
                "source_image_id": image_id,
                "image_id": image_id,
                "segment_type": "char",
                "segment_index": i,
                "bbox_x": bbox.x,
                "bbox_y": bbox.y,
                "bbox_width": bbox.width,
                "bbox_height": bbox.height,
                "validated": False,
            }
            if _write_segment_to_supabase(segment_data):
                segments_count += 1

        # 更新组的已处理图像计数
        _update_group_processed_count(image_id.split("-")[0] if "-" in image_id else "", 1)

        return {"success": True, "image_id": image_id, "segments_count": segments_count, "error": ""}

    except Exception as e:
        log.exception("_process_single_chars 失败: image_id=%s", image_id)
        return {"success": False, "image_id": image_id, "segments_count": 0, "error": str(e)}


@celery_app.task(bind=True, name="_failed_slips_subtask")
def _failed_slips_subtask(self, image_id: str, error: str) -> dict:
    """处理单支检测失败的情况"""
    return {"success": False, "image_id": image_id, "segments_count": 0, "error": error}


@celery_app.task(bind=True, name="_failed_chars_subtask")
def _failed_chars_subtask(self, image_id: str, error: str) -> dict:
    """处理单字符检测失败的情况"""
    return {"success": False, "image_id": image_id, "segments_count": 0, "error": error}