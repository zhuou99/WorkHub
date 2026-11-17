"""备份轮转：只删本功能生成的包、按时间保留最新 N 份。

移植自 WorkHub.Tests/BackupServiceTests.cs（只取 Rotate 这一段；
zip 备份与恢复本体在阶段 2）。
"""

from __future__ import annotations

from pathlib import Path

from app.common.backup_rotate import rotate


def test_rotate_keeps_newest_and_deletes_older_packs(tmp_path: Path):
    for stamp in ["20260101-000000", "20260102-000000", "20260103-000000"]:
        (tmp_path / f"workhub-backup-{stamp}.zip").write_text("x", encoding="utf-8")

    # 不是本功能产物的文件不该被碰
    (tmp_path / "readme.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "other.zip").write_text("keep", encoding="utf-8")

    removed = rotate(tmp_path, 2)

    assert removed == 1
    assert (tmp_path / "workhub-backup-20260103-000000.zip").exists()
    assert (tmp_path / "workhub-backup-20260102-000000.zip").exists()
    assert not (tmp_path / "workhub-backup-20260101-000000.zip").exists()
    assert (tmp_path / "readme.txt").exists()
    assert (tmp_path / "other.zip").exists()


def test_rotate_missing_folder_is_no_op(tmp_path: Path):
    assert rotate(tmp_path / "missing", 2) == 0


def test_rotate_non_positive_keep_is_no_op(tmp_path: Path):
    target = tmp_path / "workhub-backup-20260101-000000.zip"
    target.write_text("x", encoding="utf-8")
    assert rotate(tmp_path, 0) == 0
    assert target.exists()
