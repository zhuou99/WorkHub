"""创作类实体：笔记、文章、代码片段、收藏、发布记录。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.types import BoolAsInteger, TextDateTime


class WhNote(EntityBaseMixin, Base):
    """笔记。"""

    __tablename__ = "wh_note"

    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Content: Mapped[str | None] = mapped_column("Content", Text, nullable=True)
    Tags: Mapped[str | None] = mapped_column("Tags", Text, nullable=True)
    Pinned: Mapped[bool] = mapped_column("Pinned", BoolAsInteger, nullable=False, default=False)


class WhArticle(EntityBaseMixin, Base):
    """文章。"""

    __tablename__ = "wh_article"

    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Summary: Mapped[str | None] = mapped_column("Summary", Text, nullable=True)
    Cover: Mapped[str | None] = mapped_column("Cover", Text, nullable=True)
    Tags: Mapped[str | None] = mapped_column("Tags", Text, nullable=True)
    ProjectId: Mapped[str | None] = mapped_column("ProjectId", Text, nullable=True)
    Content: Mapped[str | None] = mapped_column("Content", Text, nullable=True)
    Status: Mapped[str | None] = mapped_column("Status", Text, nullable=True, default="draft")
    PublishTime: Mapped[datetime | None] = mapped_column("PublishTime", TextDateTime(), nullable=True)


class WhBookmark(EntityBaseMixin, Base):
    """链接收藏。"""

    __tablename__ = "wh_bookmark"

    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Url: Mapped[str] = mapped_column("Url", Text, nullable=False)
    Site: Mapped[str | None] = mapped_column("Site", Text, nullable=True)
    Summary: Mapped[str | None] = mapped_column("Summary", Text, nullable=True)
    Content: Mapped[str | None] = mapped_column("Content", Text, nullable=True)
    Tags: Mapped[str | None] = mapped_column("Tags", Text, nullable=True)
    Status: Mapped[str | None] = mapped_column("Status", Text, nullable=True, default="unread")
    Favorite: Mapped[bool] = mapped_column("Favorite", BoolAsInteger, nullable=False, default=False)
    Snapshot: Mapped[str | None] = mapped_column("Snapshot", Text, nullable=True)


class WhSnippet(EntityBaseMixin, Base):
    """代码片段。"""

    __tablename__ = "wh_snippet"

    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Language: Mapped[str | None] = mapped_column("Language", Text, nullable=True)
    Code: Mapped[str | None] = mapped_column("Code", Text, nullable=True)
    Description: Mapped[str | None] = mapped_column("Description", Text, nullable=True)
    Tags: Mapped[str | None] = mapped_column("Tags", Text, nullable=True)


class WhPublishLog(EntityBaseMixin, Base):
    """发布记录。"""

    __tablename__ = "wh_publish_log"

    ArticleId: Mapped[str | None] = mapped_column("ArticleId", Text, nullable=True)
    ArticleTitle: Mapped[str | None] = mapped_column("ArticleTitle", Text, nullable=True)
    Channel: Mapped[str] = mapped_column("Channel", Text, nullable=False)
    Result: Mapped[str | None] = mapped_column("Result", Text, nullable=True)
    Detail: Mapped[str | None] = mapped_column("Detail", Text, nullable=True)
