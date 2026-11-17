"""开源仓库路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_config_store, get_db, get_protector, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.repo import ReleasePlanIn, ReleasePlanOut, RepoBoard, RepoIn, RepoOut, RepoSnapshotOut
from app.services.repo_service import RepoService

router = APIRouter(prefix="/api/repos", tags=["开源项目"])


def _service(
    db: Session = Depends(get_db),
    config=Depends(get_config_store),
    protector=Depends(get_protector),
) -> RepoService:
    return RepoService(db, config, protector)


@router.get("/board", response_model=Result[RepoBoard], summary="仓库页数据")
def board(service: RepoService = Depends(_service), _: UserInfo = Depends(require_user)):
    data = service.board()
    return Result(data=RepoBoard(
        Repos=[RepoOut.model_validate(item) for item in data["repos"]],
        Snapshots=[RepoSnapshotOut.model_validate(item) for item in data["snapshots"]],
        Plans=[ReleasePlanOut.model_validate(item) for item in data["plans"]],
        HasToken=data["hasToken"],
    ))


@router.post("", response_model=Result[None], summary="保存仓库")
def save_repo(payload: RepoIn, service: RepoService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.save(payload))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{repo_id}", response_model=Result[None], summary="删除仓库")
def delete_repo(repo_id: str, service: RepoService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete(repo_id)
    return Result(message="已删除。")


@router.post("/{repo_id}/sync", response_model=Result[None], summary="同步单个仓库")
def sync(repo_id: str, service: RepoService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.sync(repo_id))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync-all", response_model=Result[None], summary="同步全部仓库")
def sync_all(service: RepoService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.sync_all())
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans", response_model=Result[None], summary="保存发布计划")
def save_plan(payload: ReleasePlanIn, service: RepoService = Depends(_service), _: UserInfo = Depends(require_write)):
    return Result(message=service.save_plan(payload))


@router.post("/plans/{plan_id}/toggle", response_model=Result[None], summary="标记发布/取消")
def toggle_plan(plan_id: str, service: RepoService = Depends(_service), _: UserInfo = Depends(require_write)):
    return Result(message=service.toggle_plan(plan_id))


@router.delete("/plans/{plan_id}", response_model=Result[None], summary="删除发布计划")
def delete_plan(plan_id: str, service: RepoService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete_plan(plan_id)
    return Result(message="已删除。")
