"""全文检索的结果模型：对应 C# 的 WorkHub/Models/SearchHit.cs。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.common import to_camel_case

__all__ = ["SearchPart", "SearchHit", "SearchIndex", "SearchResult"]


class _Base(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)


class SearchPart(_Base):
    """检索命中里的一段文本。"""

    Text: str = ""
    Mark: bool = False


class SearchHit(_Base):
    Id: str = ""
    Kind: str = ""
    Title: str = ""
    Url: str = ""
    Time: str = ""
    TitleParts: list[SearchPart] = []
    Parts: list[SearchPart] = []


class SearchIndex(_Base):
    """索引状态。"""

    Engine: str = ""
    Count: int = 0
    Source: int = 0
    Gap: int = 0
    BuiltAt: str = ""


class SearchResult(_Base):
    """一次检索的结果。"""

    Hits: list[SearchHit] = []
    Kinds: dict[str, int] = {}
    Engine: str = ""
