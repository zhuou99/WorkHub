"""万能工具台路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.tool import ToolInfo, ToolOption, ToolPrefOut, ToolRecordRequest, ToolRunRequest, ToolRunResult
from app.services.tool_service import ToolService
from app.toolbox import catalog
from app.toolbox.runner import run_tool

router = APIRouter(prefix="/api/tools", tags=["工具台"])


def _service(db: Session = Depends(get_db)) -> ToolService:
    return ToolService(db)


def _info(tool: catalog.ToolDef) -> ToolInfo:
    return ToolInfo(
        Id=tool.id,
        Name=tool.name,
        Category=tool.category,
        Icon=tool.icon,
        Description=tool.description,
        Kind=tool.kind,
        Options=[ToolOption(Label=label, Value=value) for label, value in tool.options],
        Params=list(tool.params),
    )


def _pref_out(pref) -> ToolPrefOut:
    return ToolPrefOut(
        Id=pref.Id,
        CreateBy=pref.CreateBy or "",
        CreateTime=pref.CreateTime,
        ModifyBy=pref.ModifyBy,
        ModifyTime=pref.ModifyTime,
        Version=pref.Version or 1,
        ToolId=pref.ToolId or "",
        ToolName=pref.ToolName,
        Input=pref.Input,
    )


@router.get("", response_model=Result[list[ToolInfo]], summary="工具目录")
def list_tools(
    keyword: str | None = Query(None, description="按名称、说明、id 或分类检索"),
    _: UserInfo = Depends(require_user),
):
    return Result(data=[_info(tool) for tool in catalog.search(keyword)])


@router.get("/prefs", response_model=Result[list[ToolPrefOut]], summary="全部工具历史")
def list_prefs(service: ToolService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_pref_out(pref) for pref in service.all_prefs()])


@router.post("/{tool_id}/run", response_model=Result[ToolRunResult], summary="执行工具")
def run(
    tool_id: str,
    payload: ToolRunRequest,
    _: UserInfo = Depends(require_user),
):
    """Viewer 也能用——万能工具台是只读页。"""
    result = run_tool(tool_id, payload.Input, payload.Option, payload.Params)
    return Result(data=ToolRunResult(Output=result.get("output") or "", Data=result.get("data")))


@router.get("/{tool_id}/history", response_model=Result[list[ToolPrefOut]], summary="工具历史")
def history(tool_id: str, service: ToolService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_pref_out(pref) for pref in service.history(tool_id)])


@router.post("/{tool_id}/record", response_model=Result[None], summary="记录一次工具输入")
def record(
    tool_id: str,
    payload: ToolRecordRequest,
    service: ToolService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(message=service.record(tool_id, payload.ToolName, payload.Input))
