"""任务看板路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.common import BaseIn
from app.schemas.crm import TaskIn, TaskOut
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["任务"])


class TaskMoveRequest(BaseIn):
    Status: str = Field(..., max_length=20)


def _service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db)


def _out(task) -> TaskOut:
    return TaskOut(
        Id=task.Id,
        CreateBy=task.CreateBy or "",
        CreateTime=task.CreateTime,
        ModifyBy=task.ModifyBy,
        ModifyTime=task.ModifyTime,
        Version=task.Version or 1,
        Title=task.Title or "",
        Status=task.Status,
        ProjectId=task.ProjectId,
        DueDate=task.DueDate,
        Priority=task.Priority,
        Note=task.Note,
        DoneTime=task.DoneTime,
    )


@router.get("", response_model=Result[list[TaskOut]], summary="任务列表")
def list_tasks(service: TaskService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_out(task) for task in service.all()])


@router.post("", response_model=Result[TaskOut], summary="新增或修改任务")
def save_task(payload: TaskIn, service: TaskService = Depends(_service), _: UserInfo = Depends(require_write)):
    return Result(data=_out(service.save(payload)), message="已保存。")


@router.post("/{task_id}/move", response_model=Result[TaskOut], summary="看板换列")
def move_task(
    task_id: str,
    payload: TaskMoveRequest,
    service: TaskService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    task = service.move(task_id, payload.Status)
    if task is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="这个任务已经不在了，或者看板没有这一列。")
    return Result(data=_out(task), message="已移动。")


@router.delete("/{task_id}", response_model=Result[None], summary="删除任务")
def delete_task(task_id: str, service: TaskService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete(task_id)
    return Result(message="已删除。")
