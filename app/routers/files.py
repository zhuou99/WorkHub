"""附件上传路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_storage, require_write
from app.schemas.auth import UserInfo
from app.schemas.common import BaseIn
from app.services.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["附件"])


class UploadRequest(BaseIn):
    FileName: str = Field(..., max_length=300)
    Base64: str = ""


def _service(storage=Depends(get_storage)) -> FileService:
    return FileService(storage)


@router.post("/upload", response_model=Result[str], summary="上传文件")
def upload(payload: UploadRequest, service: FileService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        path = service.upload(payload.FileName, payload.Base64)
        return Result(data=path, message="已上传。")
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
