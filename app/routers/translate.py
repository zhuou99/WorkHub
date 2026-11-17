"""翻译与术语表路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.core.result import Result
from app.deps import get_config_store, get_db, get_protector, require_user, require_write
from app.schemas.auth import UserInfo
from app.schemas.translate import GlossaryIn, GlossaryOut, TranslateOutcome, TranslateRequest
from app.services.translate_service import TranslateService

router = APIRouter(prefix="/api/translate", tags=["翻译"])


def _service(
    db: Session = Depends(get_db),
    config=Depends(get_config_store),
    protector=Depends(get_protector),
) -> TranslateService:
    return TranslateService(db, config, protector)


@router.get("/ready", response_model=Result[bool], summary="密钥是否配好")
def is_ready(service: TranslateService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=service.is_ready())


@router.post("", response_model=Result[TranslateOutcome], summary="翻译")
def translate(payload: TranslateRequest, service: TranslateService = Depends(_service), _: UserInfo = Depends(require_user)):
    try:
        message, outcome = service.translate(payload.Text, payload.From, payload.To, payload.ForceGlossary)
        return Result(data=outcome, message=message)
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/glossary", response_model=Result[list[GlossaryOut]], summary="术语表")
def glossary(service: TranslateService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[GlossaryOut.model_validate(item) for item in service.glossary()])


@router.post("/glossary", response_model=Result[None], summary="保存术语")
def save_glossary(payload: GlossaryIn, service: TranslateService = Depends(_service), _: UserInfo = Depends(require_write)):
    try:
        return Result(message=service.save_glossary(payload))
    except WorkHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/glossary/{glossary_id}", response_model=Result[None], summary="删除术语")
def delete_glossary(glossary_id: str, service: TranslateService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete_glossary(glossary_id)
    return Result(message="已删除。")
