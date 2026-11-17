"""客户与沟通记录路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.common import DeleteImpact
from app.schemas.crm import ClientIn, ClientOut, CommLogIn, CommLogOut
from app.services.client_service import ClientService

router = APIRouter(prefix="/api/clients", tags=["客户"])


def _service(db: Session = Depends(get_db)) -> ClientService:
    return ClientService(db)


def _out(client) -> ClientOut:
    return ClientOut(
        Id=client.Id,
        CreateBy=client.CreateBy or "",
        CreateTime=client.CreateTime,
        ModifyBy=client.ModifyBy,
        ModifyTime=client.ModifyTime,
        Version=client.Version or 1,
        Name=client.Name or "",
        Contact=client.Contact,
        Phone=client.Phone,
        Email=client.Email,
        Wechat=client.Wechat,
        Source=client.Source,
        Tags=client.Tags,
        Note=client.Note,
        Archived=bool(client.Archived),
    )


def _log_out(log) -> CommLogOut:
    return CommLogOut(
        Id=log.Id,
        CreateBy=log.CreateBy or "",
        CreateTime=log.CreateTime,
        ModifyBy=log.ModifyBy,
        ModifyTime=log.ModifyTime,
        Version=log.Version or 1,
        ClientId=log.ClientId or "",
        Type=log.Type,
        Content=log.Content or "",
        HappenTime=log.HappenTime,
        Next=log.Next,
    )


@router.get("", response_model=Result[list[ClientOut]], summary="客户列表")
def list_clients(service: ClientService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_out(client) for client in service.all()])


@router.post("", response_model=Result[ClientOut], summary="新增或修改客户")
def save_client(
    payload: ClientIn,
    service: ClientService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=_out(service.save(payload)), message="已保存。")


@router.get("/logs", response_model=Result[list[CommLogOut]], summary="全部沟通记录")
def list_logs(service: ClientService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_log_out(log) for log in service.all_logs()])


@router.post("/logs", response_model=Result[CommLogOut], summary="新增或修改沟通记录")
def save_log(
    payload: CommLogIn,
    service: ClientService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=_log_out(service.save_log(payload)), message="已记录。")


@router.delete("/logs/{log_id}", response_model=Result[None], summary="删除沟通记录")
def delete_log(log_id: str, service: ClientService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete_log(log_id)
    return Result(message="已删除。")


@router.get("/delete-impact/{client_id}", response_model=Result[DeleteImpact], summary="删除影响预览")
def preview_delete(
    client_id: str,
    service: ClientService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=service.preview_delete(client_id))


@router.delete("/{client_id}", response_model=Result[None], summary="删除客户")
def delete_client(
    client_id: str,
    detach: bool = Query(False, description="true 时把挂着的项目、发票、回款一并解绑保留"),
    service: ClientService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(message=service.delete(client_id, detach))
