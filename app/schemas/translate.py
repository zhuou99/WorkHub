"""翻译与术语表的 schema。"""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseIn, EntityOut

__all__ = ["GlossaryIn", "GlossaryOut", "TranslateOutcome", "TranslateRequest"]


class GlossaryIn(BaseIn):
    Id: str | None = Field(default=None, max_length=36)
    Term: str = Field(..., max_length=200)
    Translation: str = Field(..., max_length=500)
    Lang: str = Field(default="en", max_length=20)
    Note: str | None = Field(default=None, max_length=300)


class GlossaryOut(EntityOut):
    Term: str = ""
    Translation: str = ""
    Lang: str = ""
    Note: str | None = None


class TranslateOutcome(BaseIn):
    Text: str = ""
    From: str = ""
    To: str = ""
    Forced: list[str] = []
    ExactHit: bool = False


class TranslateRequest(BaseIn):
    Text: str = Field(..., max_length=6000)
    From: str = "auto"
    To: str = "en"
    ForceGlossary: bool = False
