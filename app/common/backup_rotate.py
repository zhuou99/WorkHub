"""备份包轮转：只留最新 keep 份。

对应 C# 的 WorkHub/Services/BackupService.cs 里的 Rotate 静态方法。
zip 备份与恢复本体在阶段 2。
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["NAME_PATTERN", "rotate"]

NAME_PATTERN = re.compile(r"^workhub-backup-\d{8}-\d{6}\.zip$")


def rotate(folder: str | Path | None, keep: int) -> int:
    """删掉超出保留份数的旧包，返回删除条数。

    只认本功能生成的包名；按文件名倒序保留（时间戳定长，倒序即最新在前）；
    单个文件删不掉不算失败，留到下次。
    """
    if keep <= 0 or not folder:
        return 0
    path = Path(folder)
    if not path.is_dir():
        return 0

    removed = 0
    try:
        stale = sorted(
            (item for item in path.glob("*.zip") if NAME_PATTERN.match(item.name)),
            key=lambda item: item.name,
            reverse=True,
        )[keep:]
    except OSError:
        # 目录枚举失败（权限/IO）不该影响备份结果。
        return 0

    for item in stale:
        try:
            item.unlink()
            removed += 1
        except OSError:
            # 被别的进程占用就留到下次，不阻断本次备份。
            continue
    return removed
