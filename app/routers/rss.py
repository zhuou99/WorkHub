"""RSS 订阅路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_db, get_storage, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.rss import AddFeedRequest, ReadAllRequest, RssBoard, RssFeedOut, RssItemOut
from app.services.rss_service import RssService

router = APIRouter(prefix="/api/rss", tags=["RSS"])


def _service(db: Session = Depends(get_db), storage=Depends(get_storage)) -> RssService:
    return RssService(db, storage)


@router.get("/board", response_model=Result[RssBoard], summary="订阅页数据")
def board(service: RssService = Depends(_service), _: UserInfo = Depends(require_user)):
    data = service.board()
    return Result(data=RssBoard(
        Feeds=[RssFeedOut.model_validate(item) for item in data["feeds"]],
        Unread=data["unread"],
        Starred=data["starred"],
    ))


@router.get("/items", response_model=Result[list[RssItemOut]], summary="条目列表")
def items(feed_id: str = "", service: RssService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[RssItemOut.model_validate(item) for item in service.items(feed_id)])


@router.post("/feeds", response_model=Result[None], summary="订阅")
def add_feed(payload: AddFeedRequest, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.add_feed(payload.Url))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/feeds/{feed_id}/sync", response_model=Result[None], summary="同步单个源")
def sync(feed_id: str, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.sync(feed_id))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync-all", response_model=Result[None], summary="同步全部源")
def sync_all(service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.sync_all())
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/feeds/{feed_id}/pause", response_model=Result[None], summary="暂停/恢复")
def toggle_pause(feed_id: str, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.toggle_pause(feed_id))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/feeds/{feed_id}", response_model=Result[None], summary="删除订阅源")
def delete_feed(feed_id: str, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete_feed(feed_id)
    return Result(message="已删除。")


@router.post("/items/{item_id}/read", response_model=Result[None], summary="标已读/未读")
def set_read(item_id: str, read: bool = True, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    return Result(message=service.set_read(item_id, read))


@router.post("/read-all", response_model=Result[None], summary="全部标已读")
def read_all(payload: ReadAllRequest, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    return Result(message=service.read_all(payload.FeedId))


@router.post("/items/{item_id}/star", response_model=Result[None], summary="收藏/取消收藏")
def toggle_star(item_id: str, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    return Result(message=service.toggle_star(item_id))


@router.delete("/items/{item_id}", response_model=Result[None], summary="删除条目")
def delete_item(item_id: str, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    return Result(message=service.delete_item(item_id))


@router.post("/items/{item_id}/clip", response_model=Result[None], summary="抓正文存收藏")
def clip(item_id: str, service: RssService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.clip(item_id))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
