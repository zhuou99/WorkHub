""".NET 的 JSON 编码/写出行为。

Python 自带的 json 有两处和 .NET 不一样，格式化工具里会被用户看见：

1. 编码器。.NET 默认编码器把 `"` 输出成 `\\u0022`、非 ASCII 输出成**大写** `\\uXXXX`，
   还会转义 `< > & ' + ` ` 这些 HTML 敏感字符；Python 的 json.dumps 用的是 `\"`。
   .NET 的 UnsafeRelaxedJsonEscaping 则只转义 `"`、`\\` 与控制字符。
2. 数字原文。.NET 的 JsonDocument 会原样保留 `1e5`、`1.0` 这种写法；
   Python 的 json.loads 会把它们变成 100000.0 / 1.0，格式化时就把原文改掉了。

所以这里自己写解析（数字保留原文）与写出。
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

__all__ = ["JsonNumber", "parse_json", "write_json", "dotnet_default_escape", "json_loads_relaxed"]


class JsonNumber:
    """保留原文的 JSON 数字。"""

    __slots__ = ("text", "value")

    def __init__(self, text: str):
        self.text = text
        self.value = Decimal(text)

    @property
    def is_integer(self) -> bool:
        """能否装进 Int64（对应 .NET 的 TryGetInt64）。"""
        if self.value != self.value.to_integral_value():
            return False
        return -(2**63) <= self.value < 2**63

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"JsonNumber({self.text!r})"


def parse_json(text: str) -> Any:
    """解析 JSON，数字保留原文。格式不对抛 FormatException。"""
    from app.common.exceptions import FormatException

    try:
        return json.loads(text, parse_float=JsonNumber, parse_int=JsonNumber)
    except json.JSONDecodeError as exc:
        raise FormatException(f"JSON 解析失败：{exc.msg}") from exc


def json_loads_relaxed(text: str) -> Any:
    """解析普通 JSON（数字变成 int/Decimal），给不需要保留原文的地方用。"""
    from app.common.exceptions import FormatException

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise FormatException(f"JSON 解析失败：{exc.msg}") from exc


def dotnet_default_escape(text: str) -> str:
    """.NET 默认 JavaScriptEncoder 的转义：等价于 JsonSerializer.Serialize(string)。

    `"` → `\\u0022`，`\\` → `\\\\`，控制字符用短转义或 `\\u00XX`（大写十六进制），
    其余非 ASCII 全部 `\\uXXXX`（大写十六进制）；`< > & ' + ` ` ` 也会被转义。
    """
    out = ['"']
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out.append("\\u0022")
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif code < 0x20 or code > 0x7E or ch in "<>&'+`":
            out.append("\\u%04X" % code)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _escape_relaxed(text: str) -> str:
    """UnsafeRelaxedJsonEscaping：只转义 `"`、`\\` 与控制字符（小写十六进制）。"""
    out = ['"']
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif code < 0x20:
            out.append("\\u%04x" % code)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def write_json(value: Any, indented: bool = True) -> str:
    """写出 JSON，行为对齐 Utf8JsonWriter + UnsafeRelaxedJsonEscaping。

    缩进两格，分隔符 `": "`，非 ASCII 与 `< > &` 都不转义。
    """
    out: list[str] = []
    _write(value, out, 0, indented)
    return "".join(out)


def _write(value: Any, out: list[str], level: int, indented: bool) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, JsonNumber):
        out.append(value.text)
    elif isinstance(value, str):
        out.append(_escape_relaxed(value))
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, Decimal):
        out.append(str(value))
    elif isinstance(value, float):
        out.append(repr(value))
    elif isinstance(value, dict):
        if not value:
            out.append("{}")
            return
        out.append("{")
        items = list(value.items())
        for index, (key, item) in enumerate(items):
            if indented:
                out.append("\n" + "  " * (level + 1))
            out.append(_escape_relaxed(str(key)))
            out.append(": " if indented else ":")
            _write(item, out, level + 1, indented)
            if index < len(items) - 1:
                out.append(",")
        if indented:
            out.append("\n" + "  " * level)
        out.append("}")
    elif isinstance(value, (list, tuple)):
        if not value:
            out.append("[]")
            return
        out.append("[")
        for index, item in enumerate(value):
            if indented:
                out.append("\n" + "  " * (level + 1))
            _write(item, out, level + 1, indented)
            if index < len(value) - 1:
                out.append(",")
        if indented:
            out.append("\n" + "  " * level)
        out.append("]")
    else:
        out.append(_escape_relaxed(str(value)))
