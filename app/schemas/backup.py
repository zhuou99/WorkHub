"""备份的 schema。"""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseIn

__all__ = ["BackupInfo", "BackupOptions"]


class BackupInfo(BaseIn):
    Name: str = ""
    Created: str = ""
    Size: str = ""
    Folder: str = ""


class BackupOptions(BaseIn):
    ExtraFolder: str = ""
    Keep: int = Field(default=10)
