"""RSS 订阅的 schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseIn, EntityOut

__all__ = ["RssFeedOut", "RssItemOut", "RssBoard", "AddFeedRequest", "ReadAllRequest"]


class RssFeedOut(EntityOut):
    Title: str = ""
    Url: str = ""
    SiteUrl: str | None = None
    Description: str | None = None
    ETag: str | None = None
    LastFetchAt: datetime | None = None
    LastError: str | None = None
    Paused: bool = False
    Note: str | None = None


class RssItemOut(EntityOut):
    FeedId: str = ""
    Title: str = ""
    Url: str | None = None
    Guid: str | None = None
    Author: str | None = None
    Summary: str | None = None
    PublishedAt: datetime | None = None
    Read: bool = False
    Starred: bool = False


class RssBoard(BaseIn):
    Feeds: list[RssFeedOut] = []
    Unread: dict[str, int] = {}
    Starred: int = 0


class AddFeedRequest(BaseIn):
    Url: str = Field(..., max_length=1000)


class ReadAllRequest(BaseIn):
    FeedId: str = ""
