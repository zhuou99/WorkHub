"""错误文本收敛：截断保留「…」标记、标题只取类型与消息首行。

移植自 WorkHub.Tests/ErrorLogRulesTests.cs。
"""

from __future__ import annotations

from app.common.error_log_rules import title, trim
from app.common.exceptions import InvalidOperationException


def test_trim_null_returns_null():
    assert trim(None, 300) is None


def test_trim_empty_returns_empty():
    assert trim("", 300) == ""


def test_trim_short_text_unchanged():
    assert trim("数据库连接失败", 300) == "数据库连接失败"


def test_trim_exactly_max_unchanged():
    text = "a" * 300
    assert trim(text, 300) == text


def test_trim_over_max_truncates_and_appends_ellipsis():
    trimmed = trim("a" * 301, 300)
    assert trimmed == "a" * 300 + "…"
    assert trimmed.endswith("…")
    assert len(trimmed) == 301


def test_trim_non_positive_max_keeps_only_ellipsis():
    assert trim("abc", 0) == "…"
    assert trim("abc", -1) == "…"


def test_title_normal_exception_returns_type_and_message():
    assert title(InvalidOperationException("数据库连接失败")) == "InvalidOperationException: 数据库连接失败"


def test_title_empty_message_returns_type_only():
    assert title(Exception("")) == "Exception"


def test_title_null_returns_unknown():
    assert title(None) == "未知错误"


def test_title_multiline_message_takes_first_line():
    assert title(Exception("第一步失败\r\n第二步失败")) == "Exception: 第一步失败"
