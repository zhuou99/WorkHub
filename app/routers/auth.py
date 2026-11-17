"""认证路由：登录、登出、当前用户、登录保护状态。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.result import Result
from app.core.session import SessionManager
from app.deps import get_auth, get_current_user, get_session_manager, require_user
from app.schemas.auth import AuthGuardState, LoginRequest, UserInfo
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=Result[UserInfo], summary="登录")
def login(
    payload: LoginRequest,
    response: Response,
    auth: AuthService = Depends(get_auth),
    sessions: SessionManager = Depends(get_session_manager),
):
    user = auth.login(payload.UserName, payload.Password)
    if user is None:
        raise HTTPException(status_code=401, detail="账号或口令不正确。")
    sessions.set_cookie(response, user.Id)
    return Result(data=user, message="登录成功。")


@router.post("/logout", response_model=Result[None], summary="登出")
def logout(
    response: Response,
    user: UserInfo = Depends(require_user),
    auth: AuthService = Depends(get_auth),
    sessions: SessionManager = Depends(get_session_manager),
):
    auth.logout(user.UserName)
    sessions.clear_cookie(response)
    return Result(message="已退出登录。")


@router.get("/me", response_model=Result[UserInfo], summary="当前登录用户")
def me(user: UserInfo = Depends(require_user)):
    return Result(data=user)


@router.get("/guard", response_model=Result[AuthGuardState], summary="登录保护状态（匿名可读）")
def guard(auth: AuthService = Depends(get_auth)):
    return Result(data=auth.guard_state())


@router.get("/session", response_model=Result[UserInfo], summary="当前登录用户（未登录返回 null）")
def session_info(user: UserInfo | None = Depends(get_current_user)):
    return Result(data=user)
