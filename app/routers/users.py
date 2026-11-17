"""账号管理路由（Owner 专属）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.result import Result
from app.deps import get_users, require_owner
from app.schemas.auth import UserCreate, UserInfo, UserResetPassword, UserUpdate, UserView
from app.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["账号"])


def _view(user) -> UserView:
    return UserView(
        Id=user.Id,
        UserName=user.UserName or "",
        DisplayName=user.DisplayName,
        Role=user.Role,
        Enabled=bool(user.Enabled),
        LastLoginTime=user.LastLoginTime,
    )


@router.get("", response_model=Result[list[UserView]], summary="账号列表")
def list_users(users: UserService = Depends(get_users), _: UserInfo = Depends(require_owner)):
    views = [_view(user) for user in sorted(users.all(), key=lambda item: item.CreateTime or item.SetTime)]
    return Result(data=views)


@router.post("", response_model=Result[UserView], summary="新建账号")
def create_user(
    payload: UserCreate,
    users: UserService = Depends(get_users),
    _: UserInfo = Depends(require_owner),
):
    user = users.create(payload.UserName, payload.DisplayName, payload.Password, payload.Role)
    return Result(data=_view(user), message=f"已新增账号 {user.UserName}。")


@router.patch("/{user_id}", response_model=Result[UserView], summary="改账号")
def update_user(
    user_id: str,
    payload: UserUpdate,
    users: UserService = Depends(get_users),
    _: UserInfo = Depends(require_owner),
):
    user = users.update(user_id, payload.DisplayName, payload.Role, payload.Enabled)
    return Result(data=_view(user), message=f"已更新账号 {user.UserName}。")


@router.post("/{user_id}/password", response_model=Result[None], summary="重置口令")
def reset_password(
    user_id: str,
    payload: UserResetPassword,
    users: UserService = Depends(get_users),
    _: UserInfo = Depends(require_owner),
):
    user = users.reset_password(user_id, payload.Password)
    return Result(message=f"已重置 {user.UserName} 的口令。")


@router.delete("/{user_id}", response_model=Result[None], summary="删除账号")
def delete_user(
    user_id: str,
    users: UserService = Depends(get_users),
    me: UserInfo = Depends(require_owner),
):
    return Result(message=users.delete(user_id, me.UserName))
