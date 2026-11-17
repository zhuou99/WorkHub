"""附件落盘：对应 C# 的 IFileStorage。

存到 <root>/uploads/yyyyMM/<安全文件名>，回 /uploads/yyyyMM/… 站内地址。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

__all__ = ["FileStorage", "ROUTE"]

ROUTE = "/uploads"

# 文件名里只保留这些字符；其余换成下划线
_SAFE = re.compile(r"[^A-Za-z0-9._-]")


class FileStorage:
    def __init__(self, root_dir: Path | str):
        self._root = Path(root_dir)

    @property
    def root_dir(self) -> Path:
        return self._root

    def save(self, file_name: str, data: bytes) -> str:
        """落盘并返回站内相对地址（/uploads/yyyyMM/…）。"""
        stem, dot, ext = (file_name or "file").rpartition(".")
        if not dot:
            dot, ext = ".", ""
        clean_stem = _SAFE.sub("_", stem).strip("._")[:120] or "file"
        # 冲突时兜底：同目录同名文件追加随机段，绝不覆盖
        month = datetime.now().strftime("%Y%m")
        target_dir = self._root / "uploads" / month
        target_dir.mkdir(parents=True, exist_ok=True)
        name = f"{clean_stem}{dot}{ext}"
        target = target_dir / name
        if target.exists():
            name = f"{clean_stem}-{uuid.uuid4().hex[:8]}{dot}{ext}"
            target = target_dir / name
        target.write_bytes(data)
        return f"{ROUTE}/{month}/{name}"

    def resolve(self, relative: str) -> Path | None:
        """把站内地址解析成绝对路径；越界返回 None。"""
        rel = relative.lstrip("/")
        candidate = (self._root / rel).resolve()
        try:
            candidate.relative_to(self._root.resolve())
        except ValueError:
            return None
        return candidate
