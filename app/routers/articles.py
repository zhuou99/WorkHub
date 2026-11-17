"""文章路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.result import PagingResult, Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.content import ArticleIn, ArticleOut, ArticleStatusRequest
from app.services.content_service import ArticleService

router = APIRouter(prefix="/api/articles", tags=["文章"])


def _service(db: Session = Depends(get_db)) -> ArticleService:
    return ArticleService(db)


@router.get("", response_model=Result[list[ArticleOut]], summary="全部文章")
def list_articles(service: ArticleService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[ArticleOut.model_validate(item) for item in service.get_all()])


@router.get("/page", response_model=PagingResult[ArticleOut], summary="分页文章")
def page_articles(
    page_index: int = Query(1, alias="pageIndex"),
    page_size: int = Query(20, alias="pageSize"),
    keyword: str = Query(""),
    project_id: str = Query("", alias="projectId"),
    service: ArticleService = Depends(_service),
    _: UserInfo = Depends(require_user),
):
    total, rows = service.page(page_index, page_size, keyword, project_id)
    return PagingResult(total=total, rows=[ArticleOut(**row) for row in rows])


@router.get("/{article_id}", response_model=Result[ArticleOut], summary="按 ID 取文章")
def get_article(article_id: str, service: ArticleService = Depends(_service), _: UserInfo = Depends(require_user)):
    article = service.get(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="这篇文章已经不在了。")
    return Result(data=ArticleOut.model_validate(article))


@router.post("", response_model=Result[ArticleOut], summary="新增或修改文章")
def save_article(payload: ArticleIn, service: ArticleService = Depends(_service), _: UserInfo = Depends(require_write)):
    article = service.save(payload)
    if article is None:
        raise HTTPException(status_code=400, detail="标题不能为空。")
    return Result(data=ArticleOut.model_validate(article), message="已保存。")


@router.post("/{article_id}/status", response_model=Result[ArticleOut], summary="标记发布状态")
def set_status(
    article_id: str,
    payload: ArticleStatusRequest,
    service: ArticleService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    article = service.set_status(article_id, payload.Status)
    if article is None:
        raise HTTPException(status_code=404, detail="这篇文章已经不在了。")
    return Result(data=ArticleOut.model_validate(article), message="已更新。")


@router.delete("/{article_id}", response_model=Result[None], summary="删除文章")
def delete_article(article_id: str, service: ArticleService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete(article_id)
    return Result(message="已删除。")
