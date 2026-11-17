"""授权口径：Owner 恒放行、匿名全拒、目录收集，全部脱离宿主可测。

移植自 WorkHub.Tests/PermissionPolicyTests.cs。

C# 那边靠反射扫 [Menu]/[Action] 收集授权目录，Python 没有这回事，
目录改成写死的 17 个菜单名 —— 行为一致，收集方式换了。
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.common.permission_policy import (
    PermDecision,
    build_snapshot,
    can_see_menu,
    catalog,
    decide,
    is_editor,
    is_owner,
    is_owner_role,
    is_viewer,
)

CATALOG_CODES = ["文章", "b_文章_demo", "偏好设置"]


@dataclass
class UserInfo:
    Id: str = ""
    UserName: str = ""
    Name: str = ""
    Role: str | None = None


def owner() -> UserInfo:
    return UserInfo(Id="admin", UserName="admin", Name="主人", Role="Owner")


def editor() -> UserInfo:
    return UserInfo(UserName="editor", Role="Editor")


def viewer() -> UserInfo:
    return UserInfo(UserName="viewer", Role="Viewer")


def test_build_snapshot_owner_carries_catalog_and_role():
    snapshot = build_snapshot(owner(), CATALOG_CODES)
    assert snapshot.loaded is True
    assert snapshot.managed is True
    assert snapshot.roles == ["Owner"]
    assert len(snapshot.codes) == len(CATALOG_CODES)
    for code in CATALOG_CODES:
        assert code in snapshot.codes


def test_build_snapshot_other_role_has_no_codes():
    snapshot = build_snapshot(UserInfo(UserName="guest", Role="Guest"), CATALOG_CODES)
    assert snapshot.loaded is True
    assert snapshot.managed is True
    assert snapshot.roles == ["Guest"]
    assert snapshot.codes == []


def test_build_snapshot_anonymous_is_empty():
    snapshot = build_snapshot(None, CATALOG_CODES)
    assert snapshot.loaded is False
    assert snapshot.managed is False
    assert snapshot.codes == []
    assert snapshot.roles == []


def test_decide_anonymous_deny():
    snapshot = build_snapshot(None, CATALOG_CODES)
    assert decide(snapshot, None, "文章") == PermDecision.DENY


def test_decide_owner_allow_unknown_code():
    snapshot = build_snapshot(owner(), CATALOG_CODES)
    assert decide(snapshot, owner(), "b_不存在_x") == PermDecision.ALLOW


def test_decide_other_role_deny_known_and_unknown():
    user = UserInfo(UserName="guest", Role="Guest")
    snapshot = build_snapshot(user, CATALOG_CODES)
    assert decide(snapshot, user, "文章") == PermDecision.DENY
    assert decide(snapshot, user, "b_不存在_x") == PermDecision.DENY


def test_catalog_contains_all_menus():
    codes = catalog()
    assert len(codes) == 17
    assert "文章" in codes
    assert "偏好设置" in codes
    assert "发票台账" in codes
    assert not any(code.startswith("b_") for code in codes)


def test_build_snapshot_editor_carries_catalog_and_role():
    snapshot = build_snapshot(editor(), CATALOG_CODES)
    assert snapshot.loaded is True
    assert snapshot.managed is True
    assert snapshot.roles == ["Editor"]
    assert len(snapshot.codes) == len(CATALOG_CODES)
    for code in CATALOG_CODES:
        assert code in snapshot.codes


def test_decide_editor_allow_known_codes():
    snapshot = build_snapshot(editor(), CATALOG_CODES)
    for code in CATALOG_CODES:
        assert decide(snapshot, editor(), code) == PermDecision.ALLOW


def test_build_snapshot_viewer_only_read_only_menus():
    snapshot = build_snapshot(viewer(), ["文章", "工作台", "全文检索", "偏好设置"])
    assert snapshot.loaded is True
    assert snapshot.managed is True
    assert snapshot.roles == ["Viewer"]
    assert len(snapshot.codes) == 2
    assert "工作台" in snapshot.codes
    assert "全文检索" in snapshot.codes
    assert "文章" not in snapshot.codes
    assert "偏好设置" not in snapshot.codes


def test_decide_viewer_only_snapshot_codes_allow():
    # 快照 Loaded/Managed 为 true 时按 Codes 纯白名单裁决：命中 Allow、未命中 Deny；
    # Default 只在快照未建立或账号未纳管时出现。
    snapshot = build_snapshot(viewer(), ["文章", "工作台", "全文检索", "偏好设置"])
    assert decide(snapshot, viewer(), "工作台") == PermDecision.ALLOW
    assert decide(snapshot, viewer(), "文章") == PermDecision.DENY
    assert decide(snapshot, viewer(), "偏好设置") == PermDecision.DENY
    assert decide(snapshot, viewer(), "b_文章_x") == PermDecision.DENY


def test_can_see_menu_null_user_false():
    assert can_see_menu("工作台", None) is False


@pytest.mark.parametrize("menu_name", [None, "文章", "未知菜单"])
def test_can_see_menu_owner_and_editor_any_menu_true(menu_name):
    assert can_see_menu(menu_name, owner()) is True
    assert can_see_menu(menu_name, editor()) is True


@pytest.mark.parametrize(
    ("menu_name", "expected"),
    [("工作台", True), ("全文检索", True), ("文章", False), ("未知菜单", False), (None, False)],
)
def test_can_see_menu_viewer_only_read_only_menus(menu_name, expected):
    assert can_see_menu(menu_name, viewer()) is expected


@pytest.mark.parametrize("role", ["Guest", "", None])
def test_can_see_menu_unknown_role_false(role):
    assert can_see_menu("工作台", UserInfo(UserName="guest", Role=role)) is False


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("Owner", True),
        ("owner", True),
        ("OWNER", True),
        ("Editor", False),
        ("", False),
        ("   ", False),
        (None, False),
    ],
)
def test_is_owner_role_various_expected(role, expected):
    assert is_owner_role(role) is expected


def test_is_owner_null_or_roleless_user_false():
    assert is_owner(None) is False
    assert is_owner(UserInfo(UserName="nobody")) is False


@pytest.mark.parametrize(
    ("role", "expected"),
    [("Editor", True), ("editor", True), ("EDITOR", True), ("Viewer", False), ("", False), (None, False)],
)
def test_is_editor_role_comparison_ignores_case(role, expected):
    assert is_editor(UserInfo(UserName="u", Role=role)) is expected


def test_is_editor_null_user_false():
    assert is_editor(None) is False


@pytest.mark.parametrize(
    ("role", "expected"),
    [("Viewer", True), ("viewer", True), ("VIEWER", True), ("Editor", False), ("", False), (None, False)],
)
def test_is_viewer_role_comparison_ignores_case(role, expected):
    assert is_viewer(UserInfo(UserName="u", Role=role)) is expected


def test_is_viewer_null_user_false():
    assert is_viewer(None) is False
