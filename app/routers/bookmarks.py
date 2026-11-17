"""收藏路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_db, get_storage, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.content import BookmarkIn, BookmarkOut
from app.services.content_service import BookmarkService

router = APIRouter(prefix="/api/bookmarks", tags=["收藏"])


def _service(db: Session = Depends(get_db), storage=Depends(get_storage)) -> BookmarkService:
    return BookmarkService(db, storage)


@router.get("", response_model=Result[list[BookmarkOut]], summary="全部收藏")
def list_bookmarks(service: BookmarkService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[BookmarkOut.model_validate(item) for item in service.get_all()])


@router.post("/clip", response_model=Result[BookmarkOut], summary="抓取链接入库")
def clip_bookmark(url: str, service: BookmarkService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        bookmark = service.clip(url)
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Result(data=BookmarkOut.model_validate(bookmark), message="已收藏。")


@router.post("", response_model=Result[BookmarkOut], summary="新增或修改收藏")
def save_bookmark(payload: BookmarkIn, service: BookmarkService = Depends(_service), _: UserInfo = Depends(require_write)):
    bookmark = service.save(payload)
    if bookmark is None:
        raise HTTPException(status_code=400, detail="标题与链接不能为空。")
    return Result(data=BookmarkOut.model_validate(bookmark), message="已保存。")


@router.delete("/{bookmark_id}", response_model=Result[None], summary="删除收藏")
def delete_bookmark(bookmark_id: str, service: BookmarkService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete(bookmark_id)
    return Result(message="已删除。")
