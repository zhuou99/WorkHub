"""内容类实体（笔记/文章/片段/收藏/发布记录）的 schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseIn, EntityOut

__all__ = [
    "NoteIn", "NoteOut",
    "ArticleIn", "ArticleOut",
    "SnippetIn", "SnippetOut",
    "BookmarkIn", "BookmarkOut",
    "PublishLogIn", "PublishLogOut",
    "ArticleStatusRequest",
]


class NoteIn(BaseIn):
    Id: str | None = Field(default=None, max_length=36)
    Title: str = Field(..., max_length=300)
    Content: str | None = None
    Tags: str | None = Field(default=None, max_length=300)
    Pinned: bool = False


class NoteOut(EntityOut):
    Title: str = ""
    Content: str | None = None
    Tags: str | None = None
    Pinned: bool = False


class ArticleIn(BaseIn):
    Id: str | None = Field(default=None, max_length=36)
    Title: str = Field(..., max_length=300)
    Summary: str | None = Field(default=None, max_length=1000)
    Cover: str | None = Field(default=None, max_length=500)
    Tags: str | None = Field(default=None, max_length=300)
    ProjectId: str | None = Field(default=None, max_length=36)
    Content: str | None = None
    Status: str | None = Field(default="draft", max_length=20)
    PublishTime: datetime | None = None


class ArticleOut(EntityOut):
    Title: str = ""
    Summary: str | None = None
    Cover: str | None = None
    Tags: str | None = None
    ProjectId: str | None = None
    Content: str | None = None
    Status: str | None = None
    PublishTime: datetime | None = None


class ArticleStatusRequest(BaseIn):
    Status: str = Field(..., max_length=20)


class SnippetIn(BaseIn):
    Id: str | None = Field(default=None, max_length=36)
    Title: str = Field(..., max_length=300)
    Language: str | None = Field(default=None, max_length=50)
    Code: str | None = None
    Description: str | None = Field(default=None, max_length=1000)
    Tags: str | None = Field(default=None, max_length=300)


class SnippetOut(EntityOut):
    Title: str = ""
    Language: str | None = None
    Code: str | None = None
    Description: str | None = None
    Tags: str | None = None


class BookmarkIn(BaseIn):
    Id: str | None = Field(default=None, max_length=36)
    Title: str = Field(..., max_length=300)
    Url: str = Field(..., max_length=1000)
    Site: str | None = Field(default=None, max_length=200)
    Summary: str | None = Field(default=None, max_length=500)
    Content: str | None = None
    Tags: str | None = Field(default=None, max_length=300)
    Status: str | None = Field(default="unread", max_length=20)
    Favorite: bool = False
    Snapshot: str | None = Field(default=None, max_length=500)


class BookmarkOut(EntityOut):
    Title: str = ""
    Url: str = ""
    Site: str | None = None
    Summary: str | None = None
    Content: str | None = None
    Tags: str | None = None
    Status: str | None = None
    Favorite: bool = False
    Snapshot: str | None = None


class PublishLogIn(BaseIn):
    ArticleId: str | None = Field(default=None, max_length=36)
    ArticleTitle: str | None = Field(default=None, max_length=300)
    Channel: str = Field(..., max_length=20)
    Result: str | None = Field(default=None, max_length=20)
    Detail: str | None = None


class PublishLogOut(EntityOut):
    ArticleId: str | None = None
    ArticleTitle: str | None = None
    Channel: str = ""
    Result: str | None = None
    Detail: str | None = None
