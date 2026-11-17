"""传输边界：回环默认放行、对外明文默认拒绝、TLS/反代/人工覆盖三条出路可放行。

移植自 WorkHub.Tests/SecurityOptionsTests.cs。
"""

from __future__ import annotations

import pytest

from app.common.security_options import SecurityOptions, is_loopback_host


@pytest.mark.parametrize(
    "urls",
    [
        None,
        "",
        "   ",
        "http://127.0.0.1:5277",
        "http://localhost:5277",
        "http://localhost:5277;http://[::1]:5277",
    ],
)
def test_validate_loopback_allows(urls):
    assert SecurityOptions().validate(urls) is None


@pytest.mark.parametrize(
    "urls",
    [
        "http://0.0.0.0:5277",
        "http://*:5277",
        "http://+:5277",
        "http://192.168.1.10:5277",
        "http://127.0.0.1:5277;http://0.0.0.0:5277",
    ],
)
def test_validate_public_bind_refuses(urls):
    reason = SecurityOptions().validate(urls)
    assert reason is not None
    assert "不是回环地址" in reason
    assert "Security:AllowInsecureRemote=true" in reason


@pytest.mark.parametrize(
    "urls",
    ["https://127.0.0.1:7263", "https://localhost:7263;http://0.0.0.0:5277"],
)
def test_validate_https_allows(urls):
    assert SecurityOptions().validate(urls) is None


def test_validate_proxy_allows():
    assert SecurityOptions(behind_tls_proxy=True).validate("http://0.0.0.0:5277") is None


def test_validate_override_allows():
    assert SecurityOptions(allow_insecure_remote=True).validate("http://0.0.0.0:5277") is None


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost", True),
        ("127.0.0.1", True),
        ("::1", True),
        ("[::1]", True),
        ("127.0.0.2", True),
        ("0.0.0.0", False),
        ("*", False),
        ("+", False),
        ("192.168.1.10", False),
        ("", False),
        (None, False),
    ],
)
def test_is_loopback_host_cases(host, expected):
    assert is_loopback_host(host) is expected


def test_defaults_are_conservative():
    options = SecurityOptions()
    assert options.behind_tls_proxy is False
    assert options.allow_insecure_remote is False
    assert options.allowed_networks == ""


def test_is_allowed_without_allowlist():
    assert SecurityOptions().is_allowed("10.1.2.3") is True


def test_is_allowed_with_allowlist():
    options = SecurityOptions(allowed_networks="10.0.0.0/8")
    assert options.is_allowed("10.1.2.3") is True
    assert options.is_allowed("192.168.1.1") is False
