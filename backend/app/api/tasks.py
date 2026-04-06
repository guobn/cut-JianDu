"""任务状态查询接口"""

from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult

from app.models.task import TaskResult, TaskStatus
from app.worker import celery_app

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskResult)
async def get_task_status(task_id: str):
    """
    查询任务状态和结果

    Args:
        task_id: 任务 ID

    Returns:
        任务状态和结果
    """
    try:
        # 获取任务结果
        task_result = AsyncResult(task_id, app=celery_app)

        # 映射 Celery 状态到 TaskStatus
        status_map = {
            "PENDING": TaskStatus.PENDING,
            "STARTED": TaskStatus.STARTED,
            "SUCCESS": TaskStatus.SUCCESS,
            "FAILURE": TaskStatus.FAILURE,
            "RETRY": TaskStatus.PENDING,
            "REVOKED": TaskStatus.FAILURE,
        }

        celery_status = task_result.status
        status = status_map.get(celery_status, TaskStatus.PENDING)

        # 构建响应
        result = TaskResult(
            task_id=task_id,
            status=status,
        )

        # 如果任务成功，添加结果
        if status == TaskStatus.SUCCESS:
            result.result = task_result.result

        # 如果任务失败，添加错误信息
        elif status == TaskStatus.FAILURE:
            error_info = task_result.result
            if isinstance(error_info, Exception):
                result.error = str(error_info)
            elif isinstance(error_info, dict):
                result.error = error_info.get("error_message", str(error_info))
            else:
                result.error = str(error_info)

        # 如果任务正在进行，添加进度信息
        elif status == TaskStatus.STARTED:
            task_info = task_result.info
            if isinstance(task_info, dict) and "progress" in task_info:
                result.progress = task_info["progress"]

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "TASK_QUERY_FAILED",
                "error_message": f"查询任务状态失败: {str(e)}",
                "suggested_solution": "请检查任务ID是否正确"
            }
        )