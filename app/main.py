"""应用装配：create_app() 工厂 + 启动期建表、迁移、种子。

对应 C# 的 WorkHubWeb/Program.cs + AppServer.cs。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import routers
from app.common.schema_migration import run as run_migrations
from app.common.security_options import SecurityOptions
from app.config import Settings
from app.core.errors import register_exception_handlers
from app.core.session import SessionManager
from app.db import create_all, create_db_engine, create_sessionmaker
from app.platforms.database_backup import DatabaseBackup
from app.platforms.file_storage import FileStorage
from app.platforms.secret_protector import SecretProtector
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.config_service import ConfigStore
from app.services.user_service import UserService

logger = logging.getLogger("workhub")

__all__ = ["create_app", "app", "SESSION_KEY", "SECRET_KEY"]

SESSION_KEY = "workhub.session.key"
SECRET_KEY = "workhub.secret.key"


def bootstrap(app: FastAPI) -> None:
    """启动期准备：安全边界 → 建表 → 结构迁移 → 会话/密钥 → 种子。"""
    settings: Settings = app.state.settings

    security = SecurityOptions(
        allow_insecure_remote=settings.allow_insecure_remote,
        behind_tls_proxy=settings.behind_tls_proxy,
        allowed_networks=settings.allowed_networks,
    )
    refusal = security.validate(settings.urls)
    if refusal:
        raise RuntimeError(refusal)

    create_all(app.state.engine)

    with app.state.sessionmaker() as session:
        run_migrations(session)

        store = ConfigStore(session)
        secret = settings.session_key or store.get(SESSION_KEY)
        if not secret:
            secret = SessionManager.new_secret()
            store.set(SESSION_KEY, secret)

        protector_key = store.get(SECRET_KEY)
        if not protector_key:
            protector_key = SecretProtector.new_key()
            store.set(SECRET_KEY, protector_key)

        audit = AuditService(session)
        users = UserService(session, audit)
        AuthService(session, store, users, audit).seed()

    app.state.session_manager = SessionManager(
        secret,
        settings.cookie_name,
        settings.cookie_max_age,
        settings.cookie_secure,
    )
    app.state.secret_protector = SecretProtector(protector_key)
    app.state.file_storage = FileStorage(settings.db_path.parent)
    app.state.database_backup = DatabaseBackup()


def create_app(settings: Settings | None = None) -> FastAPI:
    """应用工厂。测试里用自定义 settings 建一个隔离实例。"""
    resolved = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bootstrap(app)
        yield

    app = FastAPI(
        title="WorkHub",
        version="0.1.0",
        description="个人工作空间后端：工作台、笔记文章、收藏与 RSS、代码片段、客户项目、发票收支和万能工具台。",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.engine = create_db_engine(resolved.db_path)
    app.state.sessionmaker = create_sessionmaker(app.state.engine)

    register_exception_handlers(app)
    _register_access_guard(app, resolved)
    _register_cors(app, resolved)

    # 注意用 routers.xxx 引用：模块名 settings 会被 create_app 的同名参数遮住。
    for module in (
        routers.auth,
        routers.users,
        routers.clients,
        routers.projects,
        routers.tasks,
        routers.finance,
        routers.tools,
        routers.settings,
        routers.audit,
        routers.meta,
        routers.notes,
        routers.articles,
        routers.snippets,
        routers.bookmarks,
        routers.search,
        routers.rss,
        routers.repos,
        routers.translate,
        routers.publish,
        routers.report,
        routers.backup,
        routers.scheduler,
        routers.secrets,
        routers.files,
    ):
        app.include_router(module.router)

    @app.get("/", include_in_schema=False)
    def index():
        return JSONResponse({"app": "WorkHub", "docs": "/docs", "health": "/health"})

    return app


def _register_access_guard(app: FastAPI, settings: Settings) -> None:
    """访问控制中间件：名单外地址连接口都碰不到。"""
    security = SecurityOptions(
        allow_insecure_remote=settings.allow_insecure_remote,
        behind_tls_proxy=settings.behind_tls_proxy,
        allowed_networks=settings.allowed_networks,
    )
    if not settings.allowed_networks.strip():
        return

    @app.middleware("http")
    async def access_guard(request: Request, call_next):
        remote = request.client.host if request.client else ""
        if not security.is_allowed(remote):
            return JSONResponse(status_code=403, content={"code": 403, "message": "来源地址不在访问白名单里。", "data": None})
        return await call_next(request)


def _register_cors(app: FastAPI, settings: Settings) -> None:
    """跨域：前端开发服务器跑在 5173，API 在 5277。

    会话是 HttpOnly Cookie，所以必须 allow_credentials；
    带凭证时浏览器不允许 origins 为 "*"，只能逐个列出来。
    """
    origins = [origin for origin in settings.cors_origins if origin.strip()]
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app = create_app()


def main() -> None:
    """命令行入口：python -m app.main"""
    import uvicorn

    settings = app.state.settings
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
