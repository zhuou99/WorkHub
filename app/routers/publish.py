"""导出与发布路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.models.content import WhArticle
from app.schemas.auth import UserInfo
from app.schemas.common import BaseIn
from app.schemas.content import PublishLogOut
from app.services.publish_service import PublishService

router = APIRouter(prefix="/api/publish", tags=["发布"])


class ArticleRef(BaseIn):
    ArticleId: str = Field(..., max_length=36)


class LogRequest(BaseIn):
    ArticleId: str | None = Field(default=None, max_length=36)
    Channel: str = Field(..., max_length=20)
    Result: str = Field(..., max_length=20)
    Detail: str | None = None


def _service(db: Session = Depends(get_db)) -> PublishService:
    return PublishService(db)


def _load_article(db: Session, article_id: str) -> WhArticle:
    article = db.get(WhArticle, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="这篇文章已经不在了。")
    return article


@router.post("/cnblogs", response_model=Result[str], summary="博客园 Markdown")
def cnblogs(payload: ArticleRef, db: Session = Depends(get_db), service: PublishService = Depends(_service),
            _: UserInfo = Depends(require_user)):
    return Result(data=service.cnblogs_markdown(_load_article(db, payload.ArticleId)))


@router.post("/wechat", response_model=Result[str], summary="公众号 HTML")
def wechat(payload: ArticleRef, db: Session = Depends(get_db), service: PublishService = Depends(_service),
           _: UserInfo = Depends(require_user)):
    return Result(data=service.wechat_html(_load_article(db, payload.ArticleId)))


@router.post("/log", response_model=Result[None], summary="记发布日志")
def log(payload: LogRequest, db: Session = Depends(get_db), service: PublishService = Depends(_service),
        _: UserInfo = Depends(require_write)):
    article = _load_article(db, payload.ArticleId) if payload.ArticleId else None
    service.log(article, payload.Channel, payload.Result, payload.Detail)
    return Result(message="已记录。")


@router.get("/logs", response_model=Result[list[PublishLogOut]], summary="发布日志")
def logs(service: PublishService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[PublishLogOut.model_validate(item) for item in service.get_all_logs()])


@router.delete("/logs", response_model=Result[None], summary="清空发布日志")
def clear_logs(service: PublishService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.clear_logs()
    return Result(message="已清空。")


@router.delete("/logs/{log_id}", response_model=Result[None], summary="删除单条日志")
def delete_log(log_id: str, service: PublishService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete_log(log_id)
    return Result(message="已删除。")
