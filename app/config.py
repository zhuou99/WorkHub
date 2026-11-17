"""运行期配置：全部来自环境变量（可放在项目根的 .env），每项都有默认值。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_dotenv(path: Path | None = None) -> None:
    """极简 .env 读取：只认 KEY=VALUE，# 开头是注释；已存在的环境变量优先。"""
    target = path or (BASE_DIR / ".env")
    if not target.exists():
        return
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


@dataclass
class Settings:
    """一份配置快照；测试里直接构造，生产走 :meth:`from_env`。"""

    app_id: str = "WorkHub"
    app_name: str = "WorkHub"
    db_path: Path = field(default_factory=lambda: BASE_DIR / "WorkHub.db")
    host: str = "127.0.0.1"
    port: int = 5277
    cookie_name: str = "workhub_session"
    cookie_max_age: int = 43200
    session_key: str | None = None
    cookie_secure: bool = False
    allow_insecure_remote: bool = False
    #: 允许跨域访问的来源。前端开发服务器默认 5173。
    cors_origins: list[str] = field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )
    behind_tls_proxy: bool = False
    allowed_networks: str = ""
    log_dir: Path = field(default_factory=lambda: BASE_DIR / "Logs")

    @property
    def urls(self) -> str:
        """当前监听地址，写法与 C# 版的 Urls 配置一致。"""
        return f"http://{self.host}:{self.port}"

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        db_path = os.environ.get("WORKHUB_DB_PATH", "").strip()
        return cls(
            db_path=Path(db_path) if db_path else BASE_DIR / "WorkHub.db",
            host=os.environ.get("WORKHUB_HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=_env_int("WORKHUB_PORT", 5277),
            cookie_name=os.environ.get("WORKHUB_COOKIE_NAME", "workhub_session").strip() or "workhub_session",
            cookie_max_age=_env_int("WORKHUB_COOKIE_MAX_AGE", 43200),
            session_key=os.environ.get("WORKHUB_SESSION_KEY", "").strip() or None,
            cookie_secure=_env_bool("WORKHUB_COOKIE_SECURE"),
            allow_insecure_remote=_env_bool("WORKHUB_ALLOW_INSECURE_REMOTE"),
            cors_origins=_env_list("WORKHUB_CORS_ORIGINS",
                                    ["http://127.0.0.1:5173", "http://localhost:5173"]),
            behind_tls_proxy=_env_bool("WORKHUB_BEHIND_TLS_PROXY"),
            allowed_networks=os.environ.get("WORKHUB_ALLOWED_NETWORKS", ""),
        )
