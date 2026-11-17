"""元信息与健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.common import labels
from app.common.permission_policy import build_snapshot, can_see_menu, catalog
from app.core.result import Result
from app.deps import get_db, require_user
from app.schemas.auth import UserInfo

router = APIRouter(tags=["元信息"])


@router.get("/health", summary="健康检查（匿名可访问）")
def health(request: Request, db: Session = Depends(get_db)):
    """只暴露布尔与版本，不返回任何路径或文件名。"""
    db_ok = True
    schema_version = 0
    try:
        db.execute(text("SELECT 1"))
        row = db.execute(
            text("SELECT ConfigValue FROM SysConfig WHERE AppId = :app AND ConfigKey = :key"),
            {"app": "WorkHub", "key": "workhub.schema.version"},
        ).first()
        schema_version = int(row[0]) if row and row[0] else 0
    except Exception:
        db_ok = False

    ok = db_ok
    return {
        "status": "ok" if ok else "degraded",
        "db": db_ok,
        "schemaVersion": schema_version,
    }


@router.get("/api/meta/labels", response_model=Result[dict], summary="状态字典")
def meta_labels(_: UserInfo = Depends(require_user)):
    """下拉选项与标签口径，前端不用再各写一份。"""
    return Result(
        data={
            "projectStatuses": [option.model_dump() for option in labels.PROJECT_STATUSES],
            "invoiceStatuses": [option.model_dump() for option in labels.INVOICE_STATUSES],
            "invoiceTypes": [option.model_dump() for option in labels.INVOICE_TYPES],
            "planStatuses": [option.model_dump() for option in labels.PLAN_STATUSES],
            "priorities": [option.model_dump() for option in labels.PRIORITIES],
            "payMethods": [option.model_dump() for option in labels.PAY_METHODS],
            "taskColumns": ["todo", "doing", "done", "hold"],
        }
    )


@router.get("/api/meta/menus", response_model=Result[dict], summary="可见菜单")
def meta_menus(user: UserInfo = Depends(require_user)):
    """当前用户能看到哪些菜单。"""
    codes = catalog()
    snapshot = build_snapshot(user, codes)
    return Result(
        data={
            "catalog": codes,
            "visible": [name for name in codes if can_see_menu(name, user)],
            "codes": snapshot.codes,
            "roles": snapshot.roles,
        }
    )
