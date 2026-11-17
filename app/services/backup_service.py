"""一键备份与恢复：对应 C# 的 WorkHub/Services/BackupService.cs。

SQLite 在线快照 + uploads/ 附件 + 恢复说明，压成一个 zip 落到 backups/。
用 sqlite3 的 backup API 而不是直接拷文件——服务正在写的时候直接拷可能拿到半截页。
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.backup_rotate import rotate
from app.common.exceptions import WorkHubError
from app.platforms.database_backup import DatabaseBackup
from app.schemas.backup import BackupInfo, BackupOptions
from app.services.audit_service import AuditService
from app.services.config_service import ConfigStore

__all__ = ["BackupService"]

_NAME_PATTERN = re.compile(r"^workhub-backup-\d{8}-\d{6}\.zip$")
_OPTIONS_KEY = "workhub.backup.options"


class BackupService:
    def __init__(self, session: Session, config: ConfigStore, audit: AuditService,
                 storage, content_root: Path, database: DatabaseBackup):
        self._db = session
        self._config = config
        self._audit = audit
        self._storage = storage
        self._root = Path(content_root)
        self._database = database

    @property
    def folder(self) -> Path:
        return self._root / "backups"

    # ---------- 设置 ----------

    def get_folder(self) -> str:
        self.folder.mkdir(parents=True, exist_ok=True)
        return str(self.folder)

    def get_options(self) -> BackupOptions:
        fallback = BackupOptions()
        raw = self._config.get(_OPTIONS_KEY)
        if not raw:
            return fallback
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return fallback
        keep = data.get("Keep", data.get("keep", 10))
        return BackupOptions(
            ExtraFolder=(data.get("ExtraFolder", data.get("extraFolder", "")) or "").strip(),
            Keep=keep if 1 <= keep <= 100 else 10,
        )

    def save_options(self, options: BackupOptions) -> str:
        if options.Keep < 1 or options.Keep > 100:
            raise WorkHubError("保留份数请在 1 到 100 之间。")

        extra = (options.ExtraFolder or "").strip()
        if extra:
            if not Path(extra).is_absolute():
                raise WorkHubError("第二备份目录请填绝对路径，例如 D:\\Backup\\WorkHub。")
            try:
                full = str(Path(extra).resolve())
                if full.rstrip("\\/").lower() == str(self.folder.resolve()).rstrip("\\/").lower():
                    raise WorkHubError("第二备份目录不能和默认备份目录相同。")
                Path(full).mkdir(parents=True, exist_ok=True)
                extra = full
            except WorkHubError:
                raise
            except Exception as exc:
                raise WorkHubError(f"第二备份目录不可用：{exc}") from exc

        self._config.set_json(_OPTIONS_KEY, {"ExtraFolder": extra, "Keep": options.Keep})
        self._audit.write("settings", "backup-options", True, f"保留 {options.Keep} 份；第二目录 {extra}")
        return "备份设置已保存。"

    # ---------- 备份 ----------

    def run(self) -> str:
        ok, message, _ = self._run_core()
        self._audit.write("backup", "backup-run", ok, message)
        if not ok:
            raise WorkHubError(message)
        return message

    def _run_core(self) -> tuple[bool, str, str]:
        db_file = self._database.resolve_file(self._db.get_bind().url.database)
        if db_file is None:
            return False, "没连上 SQLite 数据库，备份不了。", ""
        if not Path(db_file).exists():
            return False, f"数据库文件不在：{db_file}", ""

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stage = Path(tempfile.gettempdir()) / "workhub-backup" / stamp
        zip_path = self.folder / f"workhub-backup-{stamp}.zip"

        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            stage.mkdir(parents=True, exist_ok=True)

            db_stat = {"tables": 0, "files": 0, "db_size": "", "upload_size": ""}
            try:
                db_stat["tables"] = self._database.snapshot(db_file, str(stage / "WorkHub.db"))
            except Exception as exc:
                return False, f"数据库快照失败：{exc}", ""

            count, byte_count = self._copy_uploads(stage / "uploads")
            db_stat["files"] = count
            db_stat["upload_size"] = _human(byte_count)
            db_stat["db_size"] = _human((stage / "WorkHub.db").stat().st_size)

            (stage / "恢复说明.txt").write_text(self._readme(db_stat, db_file), encoding="utf-8")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in stage.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(stage))

            info = zip_path.stat()
            options = self.get_options()
            extra_note = ""
            if (options.ExtraFolder or "").strip():
                try:
                    extra_dir = Path(options.ExtraFolder)
                    extra_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy(zip_path, extra_dir / zip_path.name)
                    rotate(str(extra_dir), options.Keep)
                except Exception as exc:
                    extra_note = f"；第二备份目录写入失败：{exc}"

            pruned = rotate(str(self.folder), options.Keep)
            rotate_note = f"（按保留 {options.Keep} 份清理了 {pruned} 个旧包）" if pruned > 0 else ""

            message = f"已备份 {zip_path.name}（{_human(info.st_size)} · 附件 {db_stat['files']} 个）{rotate_note}{extra_note}。"
            return True, message, zip_path.name
        except Exception as exc:
            _try_clean(zip_path)
            return False, f"备份失败：{exc}", ""
        finally:
            _try_clean(stage)

    def list(self) -> list[BackupInfo]:
        result: list[BackupInfo] = []
        if self.folder.is_dir():
            for file in sorted(self.folder.glob("*.zip"), key=lambda f: f.stat().st_mtime, reverse=True):
                if not _NAME_PATTERN.match(file.name):
                    continue
                result.append(BackupInfo(
                    Name=file.name,
                    Created=datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    Size=_human(file.stat().st_size),
                    Folder=str(self.folder),
                ))
        return result

    def delete(self, name: str) -> str:
        if not name or Path(name).name != name or not _NAME_PATTERN.match(name):
            raise WorkHubError("文件名不对，只让删本功能生成的备份包。")
        file = self.folder / name
        if not file.exists():
            self._audit.write("backup", "backup-delete", False, f"{name} 已不存在")
            raise WorkHubError("这个备份已经不在了。")
        try:
            file.unlink()
            self._audit.write("backup", "backup-delete", True, f"已删除 {name}")
            return f"已删除 {name}。"
        except Exception as exc:
            self._audit.write("backup", "backup-delete", False, f"删除 {name} 失败：{exc}")
            raise WorkHubError(f"删除失败：{exc}") from exc

    # ---------- 恢复 ----------

    def restore(self, name: str) -> str:
        try:
            message = self._restore_core(name)
            self._audit.write("backup", "backup-restore", True, message)
            return message
        except WorkHubError as exc:
            self._audit.write("backup", "backup-restore", False, str(exc))
            raise

    def _restore_core(self, name: str) -> str:
        if not name or Path(name).name != name or not _NAME_PATTERN.match(name):
            raise WorkHubError("文件名不对，只能恢复本功能生成的备份包。")
        pack = self.folder / name
        if not pack.exists():
            raise WorkHubError("这个备份已经不在了。")
        db_file = self._database.resolve_file(self._db.get_bind().url.database)
        if db_file is None:
            raise WorkHubError("没连上 SQLite 数据库，恢复不了。")

        stage = Path(tempfile.gettempdir()) / "workhub-restore" / datetime.now().strftime("%H%M%S%f")
        try:
            with zipfile.ZipFile(pack) as zf:
                zf.extractall(stage)
            source_db = stage / "WorkHub.db"
            if not source_db.exists():
                raise WorkHubError("包里找不到 WorkHub.db，这个备份不完整。")

            tables = self._database.check(str(source_db))

            ok, back_message, back_name = self._run_core()
            if not ok:
                raise WorkHubError(f"没能先给当前数据打备份，恢复中止：{back_message}")

            self._database.overwrite(str(source_db), db_file)
            files = self._restore_uploads(stage / "uploads")
            return (f"已用 {name} 覆盖数据库（{tables} 张表 · 附件覆盖 {files} 个）。"
                    f"当前数据先存成了 {back_name}；重启 WorkHub 之后页面读到的才是恢复后的库。")
        except WorkHubError:
            raise
        except Exception as exc:
            raise WorkHubError(f"恢复失败：{exc}") from exc
        finally:
            _try_clean(stage)

    # ---------- 内部 ----------

    def _copy_uploads(self, stage_dir: Path) -> tuple[int, int]:
        root = self._storage.root_dir
        if not root.is_dir():
            return 0, 0
        stage_dir.mkdir(parents=True, exist_ok=True)
        byte_count = 0
        count = 0
        for file in root.rglob("*"):
            if not file.is_file():
                continue
            relative = file.relative_to(root)
            target = stage_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
            byte_count += file.stat().st_size
            count += 1
        return count, byte_count

    def _restore_uploads(self, stage_dir: Path) -> int:
        """附件按包内内容覆盖同名文件，包里没有的不动。"""
        if not stage_dir.is_dir():
            return 0
        root = self._storage.root_dir
        root.mkdir(parents=True, exist_ok=True)
        n = 0
        for file in stage_dir.rglob("*"):
            if not file.is_file():
                continue
            target = root / file.relative_to(stage_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
            n += 1
        return n

    def _readme(self, stat: dict, db_file: str) -> str:
        return (
            f"WorkHub 备份包 · {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            "内容\n"
            f"  WorkHub.db        数据库在线快照（{stat['db_size']}，{stat['tables']} 张表）\n"
            f"  uploads/          附件与图片（{stat['files']} 个文件，{stat['upload_size']}）\n"
            "  恢复说明.txt      本文件\n\n"
            "恢复\n"
            "  1. 先关掉正在运行的 WorkHub。\n"
            f"  2. 解压本包，把 WorkHub.db 放回 {Path(db_file).parent}。\n"
            f"  3. 把 uploads/ 里的内容按原目录结构放回附件目录 {self._storage.root_dir}。\n"
            "  4. 重新启动 WorkHub。\n\n"
            "注意\n"
            "  · 外部服务密钥（百度翻译、GitHub）是加密密文，只在打包时的这台机器上能解开。"
            "换机器后重新录入即可，其余数据不受影响。\n"
            "  · 备份包里没有口令明文，登录口令是 PBKDF2 散列。\n"
        )


def _human(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} B"
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / 1024 / 1024:.1f} MB"


def _try_clean(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    except OSError:
        pass
