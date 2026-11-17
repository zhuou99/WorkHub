"""任务看板：对应 C# 的 WorkHub/Services/TaskService.cs。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crm import WhTask
from app.schemas.crm import TaskIn
from app.services.crud import LOCAL, now, upsert

__all__ = ["TaskService", "TASK_COLUMNS"]

TASK_FIELDS = ("Title", "Status", "ProjectId", "DueDate", "Priority", "Note", "DoneTime")

#: 看板四列
TASK_COLUMNS = ("todo", "doing", "done", "hold")


class TaskService:
    def __init__(self, session: Session):
        self._session = session

    def all(self) -> list[WhTask]:
        rows = list(self._session.execute(select(WhTask)).scalars().all())
        return sorted(rows, key=lambda item: item.CreateTime or now(), reverse=True)

    def save(self, task: TaskIn, task_id: str | None = None) -> WhTask:
        entity = WhTask(Id=task_id or "")
        for name in TASK_FIELDS:
            setattr(entity, name, getattr(task, name))
        return upsert(self._session, entity, TASK_FIELDS)

    def delete(self, task_id: str) -> None:
        entity = self._session.get(WhTask, task_id)
        if entity is not None:
            self._session.delete(entity)
            self._session.commit()

    def move(self, task_id: str, status: str) -> WhTask | None:
        """拖拽换列：只改状态，落到「已完成」时补完成时间。

        状态没变就原样返回（不更新时间戳）；非法列名返回 None。
        """
        if not task_id or status not in TASK_COLUMNS:
            return None
        task = self._session.get(WhTask, task_id)
        if task is None or task.Status == status:
            return task

        task.Status = status
        task.DoneTime = now() if status == "done" else None
        task.ModifyBy = LOCAL
        task.ModifyTime = now()
        self._session.add(task)
        self._session.commit()
        return task
