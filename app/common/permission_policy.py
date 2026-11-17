"""授权口径：Owner 恒放行；Editor 拿全部业务目录；Viewer 只拿只读页。

对应 C# 的 WorkHub/Common/PermissionPolicy.cs。

C# 那边靠反射扫 [Menu]/[Action] 属性收集目录；Python 没有反射扫程序集这回事，
目录改成一份写死的清单 —— 同样的 17 个菜单名，行为不变。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "OWNER_ROLE",
    "EDITOR_ROLE",
    "VIEWER_ROLE",
    "READ_ONLY_MENUS",
    "PermDecision",
    "PermSnapshot",
    "MENU_CATALOG",
    "is_owner_role",
    "is_owner",
    "is_editor",
    "is_viewer",
    "can_see_menu",
    "catalog",
    "build_snapshot",
    "decide",
]

OWNER_ROLE = "Owner"
EDITOR_ROLE = "Editor"
VIEWER_ROLE = "Viewer"

#: Viewer 只读可见的菜单；其余业务页不开放，避免「进得去但一操作就失败」。
READ_ONLY_MENUS = frozenset({"工作台", "万能工具台", "全文检索", "收支统计"})

#: 全部业务页的菜单名（对应 C# 侧 [Menu] 属性的 Name，去重后共 17 个）。
MENU_CATALOG: tuple[str, ...] = (
    "RSS 订阅",
    "代码片段",
    "任务看板",
    "偏好设置",
    "发布记录",
    "文章",
    "客户",
    "开源项目",
    "回款计划",
    "工作台",
    "收支统计",
    "笔记",
    "我的收藏",
    "发票台账",
    "项目列表",
    "全文检索",
    "万能工具台",
)


class PermDecision(str, Enum):
    """三态裁决结果。"""

    ALLOW = "Allow"
    DENY = "Deny"
    DEFAULT = "Default"


@dataclass
class PermSnapshot:
    """登录用户的授权快照。"""

    loaded: bool = False
    managed: bool = False
    roles: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)


def is_owner_role(role: str | None) -> bool:
    """角色是否为 Owner（比较忽略大小写）。"""
    return bool(role and role.strip()) and role.lower() == OWNER_ROLE.lower()


def is_owner(user) -> bool:
    """用户是否为 Owner。"""
    return is_owner_role(getattr(user, "Role", None))


def is_editor(user) -> bool:
    return _role_of(user) == EDITOR_ROLE.lower()


def is_viewer(user) -> bool:
    return _role_of(user) == VIEWER_ROLE.lower()


def _role_of(user) -> str | None:
    role = getattr(user, "Role", None)
    if not role or not role.strip():
        return None
    return role.lower()


def can_see_menu(menu_name: str | None, user) -> bool:
    """菜单/路由层可见性：Owner 与 Editor 全部可见，Viewer 仅只读页。"""
    if user is None:
        return False
    if is_owner(user) or is_editor(user):
        return True
    if is_viewer(user):
        return menu_name is not None and menu_name.strip().lower() in {m.lower() for m in READ_ONLY_MENUS}
    return False


def catalog() -> list[str]:
    """当前宿主的授权目录；排序口径与 C# 的 OrdinalIgnoreCase 一致（忽略大小写）。"""
    return sorted(MENU_CATALOG, key=lambda code: code.upper())


def build_snapshot(user, catalog_codes) -> PermSnapshot:
    """登录用户的授权快照。

    Owner/Editor 拿全部目录码；Viewer 只拿只读页的菜单码（模块名，b_ 开头的按钮码不在其中）；
    角色不认识就什么都不给。
    """
    if user is None:
        return PermSnapshot()

    codes = list(catalog_codes or [])
    if not is_owner(user) and not is_editor(user):
        if is_viewer(user):
            allowed = {m.lower() for m in READ_ONLY_MENUS}
            codes = [code for code in codes if code.lower() in allowed]
        else:
            codes = []

    role = getattr(user, "Role", None)
    return PermSnapshot(
        loaded=True,
        managed=True,
        roles=[role] if role and role.strip() else [],
        codes=codes,
    )


def decide(snapshot: PermSnapshot | None, user, code: str) -> PermDecision:
    """三态裁决：匿名直接 Deny；Owner 恒 Allow；其余按白名单。"""
    if user is None:
        return PermDecision.DENY
    if is_owner(user):
        return PermDecision.ALLOW
    loaded = snapshot.loaded if snapshot else False
    managed = snapshot.managed if snapshot else False
    if loaded and managed:
        codes = snapshot.codes if snapshot else []
        return PermDecision.ALLOW if code in codes else PermDecision.DENY
    return PermDecision.DEFAULT
