"""依赖注入：数据库会话、服务与角色闸门。

角色闸门：C# 那边靠页面层拦，API 没有页面，必须在路由层拦。
- require_user  —— 任意已登录角色
- require_write —— Owner + Editor（Viewer 只读）
- require_owner —— 仅 Owner（账号管理、审计清空）
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.common.permission_policy import is_editor, is_owner, is_viewer
from app.core.session import SessionManager
from app.models.user import WhUser
from app.schemas.auth import UserInfo
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.config_service import ConfigStore
from app.services.user_service import UserService

__all__ = [
    "get_db",
    "get_config_store",
    "get_audit",
    "get_users",
    "get_auth",
    "get_session_manager",
    "get_current_user",
    "get_storage",
    "get_protector",
    "get_database_backup",
    "get_content_root",
    "require_user",
    "require_write",
    "require_owner",
]


def get_db(request: Request) -> Iterator[Session]:
    """每个请求一个会话；异常回滚。"""
    with request.app.state.sessionmaker() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_config_store(db: Session = Depends(get_db)) -> ConfigStore:
    return ConfigStore(db)


def get_audit(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)


def get_users(db: Session = Depends(get_db), audit: AuditService = Depends(get_audit)) -> UserService:
    return UserService(db, audit)


def get_auth(
    db: Session = Depends(get_db),
    config: ConfigStore = Depends(get_config_store),
    users: UserService = Depends(get_users),
    audit: AuditService = Depends(get_audit),
) -> AuthService:
    return AuthService(db, config, users, audit)


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


def get_storage(request: Request):
    """附件落盘。"""
    return request.app.state.file_storage


def get_protector(request: Request):
    """外部服务密钥加解密。"""
    return request.app.state.secret_protector


def get_database_backup(request: Request):
    """SQLite 在线备份。"""
    return request.app.state.database_backup


def get_content_root(request: Request):
    """内容根目录（backups / Logs 都挂在这下面）。"""
    from pathlib import Path

    return Path(request.app.state.settings.db_path).parent


def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserInfo | None:
    """读会话 Cookie → 查 wh_user → 校验启用状态。

    每个请求都重读用户行，所以禁用账号、删账号、改角色立刻生效。
    """
    manager: SessionManager = request.app.state.session_manager
    user_id = manager.read(request.cookies.get(manager.cookie_name))
    if not user_id:
        return None
    row = db.get(WhUser, user_id)
    if row is None or not row.Enabled:
        return None
    return UserInfo(
        Id=row.Id,
        UserName=row.UserName or "",
        Name=row.DisplayName if (row.DisplayName or "").strip() else (row.UserName or ""),
        Role=row.Role,
        AppId="WorkHub",
        Token=row.Id,
        Enabled=True,
        LastLoginTime=row.LastLoginTime,
    )


def require_user(user: UserInfo | None = Depends(get_current_user)) -> UserInfo:
    if user is None:
        raise HTTPException(status_code=401, detail="还没有登录，或登录已失效。")
    return user


def require_write(user: UserInfo = Depends(require_user)) -> UserInfo:
    """写操作：Viewer 只读。"""
    if is_viewer(user):
        raise HTTPException(status_code=403, detail="Viewer 角色只能查看，不能修改。")
    return user


def require_owner(user: UserInfo = Depends(require_user)) -> UserInfo:
    """Owner 专属：账号管理、审计清空。"""
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="这个操作只有 Owner 能做。")
    return user


def require_editor(user: UserInfo = Depends(require_user)) -> UserInfo:
    """Owner 或 Editor。"""
    if not (is_owner(user) or is_editor(user)):
        raise HTTPException(status_code=403, detail="当前角色没有这个权限。")
    return user
