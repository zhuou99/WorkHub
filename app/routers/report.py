"""周报路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.common import BaseIn
from app.schemas.report import WeeklyReport
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/report", tags=["周报"])


class SaveRequest(BaseIn):
    Title: str = Field(default="", max_length=300)
    Markdown: str = ""


def _service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


@router.get("", response_model=Result[WeeklyReport], summary="生成周报")
def build(days: int = Query(7), service: ReportService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=service.build(days))


@router.post("/article", response_model=Result[None], summary="存为文章草稿")
def save_as_article(payload: SaveRequest, service: ReportService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.save_as_article(payload.Title, payload.Markdown))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/note", response_model=Result[None], summary="存为笔记")
def save_as_note(payload: SaveRequest, service: ReportService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.save_as_note(payload.Title, payload.Markdown))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
