"""RSS 订阅源与条目。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.types import BoolAsInteger, TextDateTime


class WhRssFeed(EntityBaseMixin, Base):
    """订阅源。"""

    __tablename__ = "wh_rss_feed"

    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Url: Mapped[str] = mapped_column("Url", Text, nullable=False)
    SiteUrl: Mapped[str | None] = mapped_column("SiteUrl", Text, nullable=True)
    Description: Mapped[str | None] = mapped_column("Description", Text, nullable=True)
    ETag: Mapped[str | None] = mapped_column("ETag", Text, nullable=True)
    LastFetchAt: Mapped[datetime | None] = mapped_column("LastFetchAt", TextDateTime(), nullable=True)
    LastError: Mapped[str | None] = mapped_column("LastError", Text, nullable=True)
    Paused: Mapped[bool] = mapped_column("Paused", BoolAsInteger, nullable=False, default=False)
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)


class WhRssItem(EntityBaseMixin, Base):
    """订阅条目。"""

    __tablename__ = "wh_rss_item"

    FeedId: Mapped[str] = mapped_column("FeedId", Text, nullable=False)
    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Url: Mapped[str | None] = mapped_column("Url", Text, nullable=True)
    Guid: Mapped[str | None] = mapped_column("Guid", Text, nullable=True)
    Author: Mapped[str | None] = mapped_column("Author", Text, nullable=True)
    Summary: Mapped[str | None] = mapped_column("Summary", Text, nullable=True)
    PublishedAt: Mapped[datetime | None] = mapped_column("PublishedAt", TextDateTime(), nullable=True)
    Read: Mapped[bool] = mapped_column("Read", BoolAsInteger, nullable=False, default=False)
    Starred: Mapped[bool] = mapped_column("Starred", BoolAsInteger, nullable=False, default=False)
