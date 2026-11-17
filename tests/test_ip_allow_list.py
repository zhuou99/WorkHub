"""白名单匹配：精确 IP、IPv4 CIDR、端口/方括号归一化、非法规则不命中。

移植自 WorkHub.Tests/IpAllowListTests.cs。
"""

from __future__ import annotations

import pytest

from app.common.ip_allow_list import any_match, is_loopback, is_match, normalize


@pytest.mark.parametrize(
    ("ip", "rule", "expected"),
    [
        ("127.0.0.1", "127.0.0.1", True),
        ("127.0.0.1", "10.0.0.1", False),
        ("::1", "::1", True),
        ("::1", "127.0.0.1", False),
    ],
)
def test_is_match_exact(ip, rule, expected):
    assert is_match(ip, rule) is expected


@pytest.mark.parametrize(
    ("ip", "rule", "expected"),
    [
        ("10.1.2.3", "10.0.0.0/8", True),
        ("192.168.1.20", "192.168.1.0/24", True),
        ("192.168.1.20", "192.168.2.0/24", False),
        ("172.16.0.1", "172.16.0.0/12", True),
        ("172.32.0.1", "172.16.0.0/12", False),
        ("10.0.0.1", "10.0.0.0/32", False),
        ("10.0.0.0", "10.0.0.0/32", True),
        ("10.0.0.1", "10.0.0.0/0", True),
    ],
)
def test_is_match_cidr(ip, rule, expected):
    assert is_match(ip, rule) is expected


@pytest.mark.parametrize(
    ("ip", "rule", "expected"),
    [
        ("127.0.0.1:5277", "127.0.0.1", True),
        ("[::1]:5277", "::1", True),
        (" 10.1.2.3 ", "10.0.0.0/8", True),
    ],
)
def test_is_match_normalizes_port_and_brackets(ip, rule, expected):
    assert is_match(ip, rule) is expected


@pytest.mark.parametrize(
    ("ip", "rule"),
    [
        ("10.0.0.1", "not-an-ip"),
        ("10.0.0.1", "10.0.0.0/33"),
        ("10.0.0.1", "10.0.0.0/-1"),
        ("10.0.0.1", "::/0"),
        ("", "10.0.0.0/8"),
    ],
)
def test_is_match_invalid_rule_does_not_match(ip, rule):
    assert is_match(ip, rule) is False


@pytest.mark.parametrize(
    ("ip", "rules", "expected"),
    [
        ("10.1.2.3", "192.168.0.1, 10.0.0.0/8", True),
        ("10.1.2.3", "192.168.0.1;10.0.0.0/8", True),
        ("172.16.5.5", "192.168.0.1, 10.0.0.0/8", False),
        ("127.0.0.1", "", False),
    ],
)
def test_any_match_list(ip, rules, expected):
    assert any_match(ip, rules) is expected


@pytest.mark.parametrize(
    ("ip", "expected"),
    [("127.0.0.1", True), ("127.0.0.2", True), ("::1", True), ("10.0.0.1", False)],
)
def test_is_loopback(ip, expected):
    assert is_loopback(ip) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("", ""),
        (" 127.0.0.1 ", "127.0.0.1"),
        ("127.0.0.1:5277", "127.0.0.1"),
        ("[::1]:5277", "::1"),
        ("::1", "::1"),
    ],
)
def test_normalize(value, expected):
    assert normalize(value) == expected
