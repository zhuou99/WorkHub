"""账号规则：纯函数，服务层只负责落库与审计。

对应 C# 的 WorkHub/Common/UserRules.cs。
"""

from __future__ import annotations

from app.common.permission_policy import EDITOR_ROLE, OWNER_ROLE, VIEWER_ROLE, is_owner_role

__all__ = ["validate_user_name", "validate_password", "is_role", "can_remove"]


def _is_letter_or_digit(ch: str) -> bool:
    """对应 .NET 的 char.IsLetterOrDigit：Unicode 字母（Lu/Ll/Lt/Lm/Lo）或十进制数字（Nd）。"""
    return ch.isalpha() or ch.isdecimal()


def validate_user_name(name: str | None) -> str | None:
    """返回错误文案；None 表示通过。长度检查在空格检查之前，与 C# 顺序一致。"""
    value = (name or "").strip()
    if len(value) == 0:
        return "账号不能为空。"
    if len(value) > 30:
        return "账号最多 30 个字符。"
    if any(ch.isspace() for ch in value):
        return "账号不能包含空格。"
    if any(not (_is_letter_or_digit(ch) or ch in "_-.") for ch in value):
        return "账号只能包含字母、数字、下划线和 . - 。"
    return None


def validate_password(password: str | None) -> str | None:
    """返回错误文案；None 表示通过。"""
    if not password or len(password) < 6:
        return "口令至少 6 位。"
    return None


def is_role(role: str | None) -> bool:
    """角色是否在 Owner / Editor / Viewer 之内（比较忽略大小写）。"""
    if role is None:
        return False
    return (
        is_owner_role(role)
        or role.lower() == EDITOR_ROLE.lower()
        or role.lower() == VIEWER_ROLE.lower()
    )


def can_remove(target_enabled: bool, target_role: str | None, enabled_owners: int) -> bool:
    """最后一个启用中的 Owner 不允许被禁用或删除。

    注意这里用的是「忽略大小写地等于 Owner」，不是 is_owner_role：
    空白角色不算 Owner。
    """
    if not target_enabled:
        return True
    if target_role is None or target_role.lower() != OWNER_ROLE.lower():
        return True
    return enabled_owners > 1
