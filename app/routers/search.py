"""全文检索路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user
from app.schemas.auth import UserInfo
from app.schemas.search import SearchIndex, SearchResult
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["检索"])


def _service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(db)


@router.get("/index", response_model=Result[SearchIndex], summary="索引状态")
def get_index(service: SearchService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=service.get_index())


@router.post("/rebuild", response_model=Result[None], summary="重建索引")
def rebuild(service: SearchService = Depends(_service), _: UserInfo = Depends(require_user)):
    count, engine = service.rebuild()
    return Result(message=f"索引已重建：{count} 条内容 · {engine}。")


@router.get("", response_model=Result[SearchResult], summary="全文检索")
def search(
    kw: str = Query(""),
    kind: str = Query(""),
    service: SearchService = Depends(_service),
    _: UserInfo = Depends(require_user),
):
    return Result(data=service.search(kw, kind))
