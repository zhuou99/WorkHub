"""笔记路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.result import PagingResult, Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.content import NoteIn, NoteOut
from app.services.content_service import NoteService

router = APIRouter(prefix="/api/notes", tags=["笔记"])


def _service(db: Session = Depends(get_db)) -> NoteService:
    return NoteService(db)


@router.get("", response_model=Result[list[NoteOut]], summary="全部笔记")
def list_notes(service: NoteService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[NoteOut.model_validate(item) for item in service.get_all()])


@router.get("/page", response_model=PagingResult[NoteOut], summary="分页笔记")
def page_notes(
    page_index: int = Query(1, alias="pageIndex"),
    page_size: int = Query(20, alias="pageSize"),
    keyword: str = Query(""),
    service: NoteService = Depends(_service),
    _: UserInfo = Depends(require_user),
):
    total, rows = service.page(page_index, page_size, keyword)
    return PagingResult(total=total, rows=[NoteOut(**row) for row in rows])


@router.get("/{note_id}", response_model=Result[NoteOut], summary="按 ID 取笔记")
def get_note(note_id: str, service: NoteService = Depends(_service), _: UserInfo = Depends(require_user)):
    note = service.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="这条笔记已经不在了。")
    return Result(data=NoteOut.model_validate(note))


@router.post("", response_model=Result[NoteOut], summary="新增或修改笔记")
def save_note(payload: NoteIn, service: NoteService = Depends(_service), _: UserInfo = Depends(require_write)):
    note = service.save(payload)
    if note is None:
        raise HTTPException(status_code=400, detail="标题不能为空。")
    return Result(data=NoteOut.model_validate(note), message="已保存。")


@router.delete("/{note_id}", response_model=Result[None], summary="删除笔记")
def delete_note(note_id: str, service: NoteService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete(note_id)
    return Result(message="已删除。")
