"""账号规则：账号/口令校验文案、角色识别、最后一个启用 Owner 的保护。

移植自 WorkHub.Tests/UserRulesTests.cs。
"""

from __future__ import annotations

import re

import pytest

from app.common.user_rules import can_remove, is_role, validate_password, validate_user_name

CHINESE = re.compile(r"[一-鿿]")


def assert_chinese_message(message):
    assert message is not None and message.strip()
    assert CHINESE.search(message)


@pytest.mark.parametrize("name", ["zhang_san", "a.b-c", "user2026", "user.01", "张三"])
def test_validate_user_name_valid_returns_none(name):
    assert validate_user_name(name) is None


@pytest.mark.parametrize("name", [None, "", "   "])
def test_validate_user_name_empty_or_whitespace_returns_chinese_message(name):
    assert_chinese_message(validate_user_name(name))


def test_validate_user_name_thirty_chars_returns_none():
    assert validate_user_name("a" * 30) is None


def test_validate_user_name_over_thirty_chars_returns_chinese_message():
    assert_chinese_message(validate_user_name("a" * 31))


@pytest.mark.parametrize("name", ["zhang san", "张 三"])
def test_validate_user_name_inner_space_returns_chinese_message(name):
    assert_chinese_message(validate_user_name(name))


@pytest.mark.parametrize("name", ["a@b", "a/b", "a#b"])
def test_validate_user_name_illegal_char_returns_chinese_message(name):
    assert_chinese_message(validate_user_name(name))


@pytest.mark.parametrize("password", [None, "", "12345"])
def test_validate_password_too_short_returns_chinese_message(password):
    assert_chinese_message(validate_password(password))


@pytest.mark.parametrize("password", ["123456", "1234567890"])
def test_validate_password_at_least_six_returns_none(password):
    assert validate_password(password) is None


@pytest.mark.parametrize("role", ["Owner", "owner", "EDITOR", "Viewer"])
def test_is_role_known_role_returns_true(role):
    assert is_role(role) is True


@pytest.mark.parametrize("role", ["Guest", "", None])
def test_is_role_unknown_or_empty_returns_false(role):
    assert is_role(role) is False


@pytest.mark.parametrize(
    ("role", "enabled_owners", "expected"),
    [
        ("Owner", 1, False),
        ("Owner", 2, True),
        ("owner", 1, False),
        ("OWNER", 2, True),
        ("Editor", 1, True),
        ("Viewer", 1, True),
    ],
)
def test_can_remove_enabled_account_follows_last_owner_guard(role, enabled_owners, expected):
    assert can_remove(True, role, enabled_owners) is expected


@pytest.mark.parametrize("role", ["Owner", "Editor"])
def test_can_remove_disabled_account_returns_true(role):
    assert can_remove(False, role, 1) is True
