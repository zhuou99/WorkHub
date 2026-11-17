"""SQLite 在线快照 / 覆盖 / 完整性检查：对应 C# 的 IDatabaseBackup。

用 sqlite3 的 backup API 而不是直接拷文件——服务正在写的时候直接拷可能拿到半截页。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

__all__ = ["DatabaseBackup"]


class DatabaseBackup:
    def resolve_file(self, db_path: Path | str) -> str | None:
        """把数据源解析成绝对路径；内存库返回 None。"""
        path = Path(db_path)
        if path.name == ":memory:" or str(path).startswith(":memory:"):
            return None
        return str(path.resolve())

    def snapshot(self, source: str, target: str) -> int:
        """在线快照到目标文件，返回表数量；副本必须通过完整性检查。"""
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(source)
        try:
            dst = sqlite3.connect(target)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        return self.check(target)

    def overwrite(self, source: str, target: str) -> None:
        """用备份库覆盖当前库。"""
        src = sqlite3.connect(source)
        try:
            dst = sqlite3.connect(target)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()

    def check(self, db_path: str) -> int:
        """完整性检查，返回表数量；检查不通过抛异常。"""
        conn = sqlite3.connect(db_path)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result is None or result[0] != "ok":
                raise RuntimeError(f"完整性检查未通过：{result[0] if result else '无结果'}")
            return conn.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]
        finally:
            conn.close()
