"""开源仓库镜像、快照与发布计划。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.types import BoolAsInteger, TextDateTime


class WhRepo(EntityBaseMixin, Base):
    """开源仓库。"""

    __tablename__ = "wh_repo"

    Owner: Mapped[str] = mapped_column("Owner", Text, nullable=False)
    Name: Mapped[str] = mapped_column("Name", Text, nullable=False)
    Description: Mapped[str | None] = mapped_column("Description", Text, nullable=True)
    Url: Mapped[str | None] = mapped_column("Url", Text, nullable=True)
    Language: Mapped[str | None] = mapped_column("Language", Text, nullable=True)
    Topics: Mapped[str | None] = mapped_column("Topics", Text, nullable=True)
    Homepage: Mapped[str | None] = mapped_column("Homepage", Text, nullable=True)
    Stars: Mapped[int] = mapped_column("Stars", Integer, nullable=False, default=0)
    Forks: Mapped[int] = mapped_column("Forks", Integer, nullable=False, default=0)
    OpenIssues: Mapped[int] = mapped_column("OpenIssues", Integer, nullable=False, default=0)
    SyncTime: Mapped[datetime | None] = mapped_column("SyncTime", TextDateTime(), nullable=True)
    PushedAt: Mapped[datetime | None] = mapped_column("PushedAt", TextDateTime(), nullable=True)
    LastRelease: Mapped[str | None] = mapped_column("LastRelease", Text, nullable=True)
    LastReleaseAt: Mapped[datetime | None] = mapped_column("LastReleaseAt", TextDateTime(), nullable=True)
    ProjectId: Mapped[str | None] = mapped_column("ProjectId", Text, nullable=True)
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)


class WhRepoSnapshot(EntityBaseMixin, Base):
    """仓库的一次镜像快照（时间点直接取 CreateTime）。"""

    __tablename__ = "wh_repo_snapshot"

    RepoId: Mapped[str] = mapped_column("RepoId", Text, nullable=False)
    Stars: Mapped[int] = mapped_column("Stars", Integer, nullable=False, default=0)
    Forks: Mapped[int] = mapped_column("Forks", Integer, nullable=False, default=0)
    OpenIssues: Mapped[int] = mapped_column("OpenIssues", Integer, nullable=False, default=0)


class WhReleasePlan(EntityBaseMixin, Base):
    """发布计划（版本号用 Tag，不叫 Version——基类占用了）。"""

    __tablename__ = "wh_release_plan"

    RepoId: Mapped[str] = mapped_column("RepoId", Text, nullable=False)
    Tag: Mapped[str] = mapped_column("Tag", Text, nullable=False)
    PlanDate: Mapped[datetime | None] = mapped_column("PlanDate", TextDateTime(), nullable=True)
    Notes: Mapped[str | None] = mapped_column("Notes", Text, nullable=True)
    Released: Mapped[bool] = mapped_column("Released", BoolAsInteger, nullable=False, default=False)
    ReleaseDate: Mapped[datetime | None] = mapped_column("ReleaseDate", TextDateTime(), nullable=True)
