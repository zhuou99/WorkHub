"""开源仓库的 schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseIn, EntityOut

__all__ = ["RepoIn", "RepoOut", "RepoSnapshotOut", "ReleasePlanIn", "ReleasePlanOut", "RepoBoard"]


class RepoIn(BaseIn):
    Id: str | None = Field(default=None, max_length=50)
    Owner: str = Field(..., max_length=100)
    Name: str = Field(..., max_length=100)
    Description: str | None = Field(default=None, max_length=500)
    Url: str | None = Field(default=None, max_length=300)
    Homepage: str | None = Field(default=None, max_length=300)
    ProjectId: str | None = Field(default=None, max_length=50)
    Note: str | None = Field(default=None, max_length=1000)


class RepoOut(EntityOut):
    Owner: str = ""
    Name: str = ""
    Description: str | None = None
    Url: str | None = None
    Language: str | None = None
    Topics: str | None = None
    Homepage: str | None = None
    Stars: int = 0
    Forks: int = 0
    OpenIssues: int = 0
    SyncTime: datetime | None = None
    PushedAt: datetime | None = None
    LastRelease: str | None = None
    LastReleaseAt: datetime | None = None
    ProjectId: str | None = None
    Note: str | None = None


class RepoSnapshotOut(EntityOut):
    RepoId: str = ""
    Stars: int = 0
    Forks: int = 0
    OpenIssues: int = 0


class ReleasePlanIn(BaseIn):
    Id: str | None = Field(default=None, max_length=50)
    RepoId: str = Field(..., max_length=50)
    Tag: str = Field(..., max_length=50)
    PlanDate: datetime | None = None
    Notes: str | None = Field(default=None, max_length=500)


class ReleasePlanOut(EntityOut):
    RepoId: str = ""
    Tag: str = ""
    PlanDate: datetime | None = None
    Notes: str | None = None
    Released: bool = False
    ReleaseDate: datetime | None = None


class RepoBoard(BaseIn):
    Repos: list[RepoOut] = []
    Snapshots: list[RepoSnapshotOut] = []
    Plans: list[ReleasePlanOut] = []
    HasToken: bool = False
