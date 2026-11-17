"""密钥管理路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_audit, get_config_store, get_protector, require_owner
from app.schemas.auth import UserInfo
from app.schemas.common import BaseIn
from app.services.audit_service import AuditService
from app.services.config_service import ConfigStore
from app.services.secret_service import SecretService

router = APIRouter(prefix="/api/secrets", tags=["密钥"])


class SecretSetRequest(BaseIn):
    Key: str = Field(..., max_length=50)
    Value: str = Field(..., max_length=500)


def _service(
    config: ConfigStore = Depends(get_config_store),
    audit: AuditService = Depends(get_audit),
    protector=Depends(get_protector),
) -> SecretService:
    return SecretService(config, audit, protector)


@router.get("", response_model=Result[list[dict]], summary="密钥目录")
def get_all(service: SecretService = Depends(_service), _: UserInfo = Depends(require_owner)):
    return Result(data=service.get_all())


@router.post("", response_model=Result[None], summary="录入密钥")
def set_secret(payload: SecretSetRequest, service: SecretService = Depends(_service), _: UserInfo = Depends(require_owner)):
    try:
        return Result(message=service.set(payload.Key, payload.Value))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{key}", response_model=Result[None], summary="清除密钥")
def remove_secret(key: str, service: SecretService = Depends(_service), _: UserInfo = Depends(require_owner)):
    try:
        return Result(message=service.remove(key))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
