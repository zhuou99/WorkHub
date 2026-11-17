"""代码片段路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.content import SnippetIn, SnippetOut
from app.services.content_service import SnippetService

router = APIRouter(prefix="/api/snippets", tags=["代码片段"])


def _service(db: Session = Depends(get_db)) -> SnippetService:
    return SnippetService(db)


@router.get("", response_model=Result[list[SnippetOut]], summary="全部片段")
def list_snippets(service: SnippetService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[SnippetOut.model_validate(item) for item in service.get_all()])


@router.post("", response_model=Result[SnippetOut], summary="新增或修改片段")
def save_snippet(payload: SnippetIn, service: SnippetService = Depends(_service), _: UserInfo = Depends(require_write)):
    snippet = service.save(payload)
    if snippet is None:
        raise HTTPException(status_code=400, detail="标题不能为空。")
    return Result(data=SnippetOut.model_validate(snippet), message="已保存。")


@router.delete("/{snippet_id}", response_model=Result[None], summary="删除片段")
def delete_snippet(snippet_id: str, service: SnippetService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete(snippet_id)
    return Result(message="已删除。")
