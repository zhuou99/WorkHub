"""项目与里程碑路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.common import DeleteImpact
from app.schemas.crm import MilestoneIn, MilestoneOut, ProjectIn, ProjectOut
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["项目"])


def _service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


def _out(project) -> ProjectOut:
    return ProjectOut(
        Id=project.Id,
        CreateBy=project.CreateBy or "",
        CreateTime=project.CreateTime,
        ModifyBy=project.ModifyBy,
        ModifyTime=project.ModifyTime,
        Version=project.Version or 1,
        Name=project.Name or "",
        ClientId=project.ClientId,
        Status=project.Status,
        Amount=project.Amount,
        SignedDate=project.SignedDate,
        StartDate=project.StartDate,
        EndDate=project.EndDate,
        ExpireDate=project.ExpireDate,
        ContractFile=project.ContractFile,
        Terms=project.Terms,
        Description=project.Description,
    )


def _milestone_out(milestone) -> MilestoneOut:
    return MilestoneOut(
        Id=milestone.Id,
        CreateBy=milestone.CreateBy or "",
        CreateTime=milestone.CreateTime,
        ModifyBy=milestone.ModifyBy,
        ModifyTime=milestone.ModifyTime,
        Version=milestone.Version or 1,
        ProjectId=milestone.ProjectId or "",
        Title=milestone.Title or "",
        StartDate=milestone.StartDate,
        DueDate=milestone.DueDate,
        Done=bool(milestone.Done),
        DoneTime=milestone.DoneTime,
        Sort=milestone.Sort or 0,
    )


@router.get("", response_model=Result[list[ProjectOut]], summary="项目列表")
def list_projects(service: ProjectService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_out(project) for project in service.all()])


@router.post("", response_model=Result[ProjectOut], summary="新增或修改项目")
def save_project(
    payload: ProjectIn,
    service: ProjectService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=_out(service.save(payload)), message="已保存。")


@router.get("/milestones", response_model=Result[list[MilestoneOut]], summary="全部里程碑")
def list_milestones(service: ProjectService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_milestone_out(item) for item in service.all_milestones()])


@router.post("/milestones", response_model=Result[MilestoneOut], summary="新增或修改里程碑")
def save_milestone(
    payload: MilestoneIn,
    service: ProjectService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=_milestone_out(service.save_milestone(payload)), message="已保存。")


@router.delete("/milestones/{milestone_id}", response_model=Result[None], summary="删除里程碑")
def delete_milestone(
    milestone_id: str,
    service: ProjectService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    service.delete_milestone(milestone_id)
    return Result(message="已删除。")


@router.get("/delete-impact/{project_id}", response_model=Result[DeleteImpact], summary="删除影响预览")
def preview_delete(
    project_id: str,
    service: ProjectService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=service.preview_delete(project_id))


@router.delete("/{project_id}", response_model=Result[None], summary="删除项目")
def delete_project(
    project_id: str,
    detach: bool = Query(False, description="true 时把挂着的任务、发票、支出一并解绑保留"),
    service: ProjectService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(message=service.delete(project_id, detach))
