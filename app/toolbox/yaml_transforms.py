"""YAML ⇄ JSON 互转。

对应 C# 的 WorkHub/Common/YamlTransforms.cs。

两条关键约定：

1. **标量类型自己判**。C# 那边 YamlDotNet 只做语法解析、不做 tag 归一化，
   标量的类型判定按 YAML 1.1 的字面量规则自己写。Python 侧用 PyYAML 的**事件流**
   （`yaml.parse`）而不是 `yaml.safe_load`——后者会自己按 YAML 1.1 解析类型
   （`y`/`n` 也算布尔、带引号的标量也会被重新定型），跟原项目的口径不一致。
   事件流保留了 tag（隐式为 None）、style（plain/quoted/字面量）与原始文本，正好够用。

2. **反向输出不用序列化器**。C# 那边刻意不用 YamlDotNet 的序列化器：
   它会把含换行的字符串折成 `>-`，回读时多出一个尾换行，配置文档上这是静默改数据。
   这里用自写的确定性发射器（不能安全裸写的字符串一律双引号转义）。
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from app.common.exceptions import FormatException, InvalidOperationException
from app.toolbox.json_codec import write_json

__all__ = ["yaml_to_json", "json_to_yaml"]


# ---------- YAML 节点 ----------


@dataclass
class YamlScalar:
    value: str
    tag: str | None = None
    style: str | None = None


@dataclass
class YamlSequence:
    items: list = field(default_factory=list)


@dataclass
class YamlMapping:
    items: list = field(default_factory=list)


class _NodeBuilder:
    """把 PyYAML 的事件流拼成树。"""

    def __init__(self, events: list):
        self.events = events
        self.pos = 0

    def peek(self):
        return self.events[self.pos] if self.pos < len(self.events) else None

    def take(self):
        event = self.events[self.pos]
        self.pos += 1
        return event

    def build_node(self):
        event = self.take()
        if isinstance(event, yaml.ScalarEvent):
            return YamlScalar(event.value, event.tag, event.style)
        if isinstance(event, yaml.SequenceStartEvent):
            items: list = []
            while not isinstance(self.peek(), yaml.SequenceEndEvent):
                items.append(self.build_node())
            self.take()
            return YamlSequence(items)
        if isinstance(event, yaml.MappingStartEvent):
            items: list = []
            while not isinstance(self.peek(), yaml.MappingEndEvent):
                key = self.build_node()
                value = self.build_node()
                items.append((key, value))
            self.take()
            return YamlMapping(items)
        raise FormatException(f"YAML 结构无法解析：{event}")


# ---------- YAML → JSON ----------


def yaml_to_json(text: str) -> str:
    """YAML → JSON。空文档返回 "null"。"""
    try:
        events = list(yaml.parse(text))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"（第 {mark.line + 1} 行第 {mark.column + 1} 列附近）" if mark else ""
        raise InvalidOperationException(f"YAML 解析失败{where}：{_yaml_message(exc)}") from exc

    builder = _NodeBuilder(events)
    # 跳过 StreamStart，找第一份文档
    while builder.peek() is not None and not isinstance(builder.peek(), yaml.DocumentStartEvent):
        builder.take()
    if builder.peek() is None:
        return "null"
    builder.take()  # DocumentStart
    if builder.peek() is None or isinstance(builder.peek(), yaml.DocumentEndEvent):
        return "null"

    node = builder.build_node()
    value = _from_yaml(node, 0)
    return write_json(value, indented=True)


def _yaml_message(exc: yaml.YAMLError) -> str:
    problem = getattr(exc, "problem", None)
    return problem if problem else str(exc).replace("\n", " ").strip()


def _from_yaml(node, depth: int):
    if depth > 64:
        raise InvalidOperationException("YAML 嵌套超过 64 层，拒绝继续（多半是锚点自引用）。")
    if isinstance(node, YamlSequence):
        return [_from_yaml(item, depth + 1) for item in node.items]
    if isinstance(node, YamlMapping):
        result: dict[str, Any] = {}
        for key_node, value_node in node.items:
            key = key_node.value if isinstance(key_node, YamlScalar) else ""
            if not key:
                key = "(空键)"
            result[key] = _from_yaml(value_node, depth + 1)
        return result
    return _scalar(node)


def _scalar(node: YamlScalar):
    text = node.value or ""
    tag = node.tag or ""

    # 显式 tag 优先；带引号/字面量/折叠块都是字符串，不做类型猜疑
    if tag.endswith(":str"):
        return text
    if tag.endswith(":null") or tag.endswith(":bool") or tag.endswith(":int") or tag.endswith(":float"):
        return _typed(text, tag)
    if node.style is not None:
        return text
    return _typed(text, "")


def _typed(text: str, tag: str):
    if tag.endswith(":null") or text in ("~", "null", "Null", "NULL", ""):
        return None
    flag = _bool_of(text)
    if flag is not None or tag.endswith(":bool"):
        return bool(flag)
    if tag.endswith(":int") or (tag == "" and _looks_int(text)):
        return _int(text)
    if tag.endswith(":float") or (tag == "" and _looks_float(text)):
        return _number(text)
    return text


def _bool_of(text: str) -> bool | None:
    """YAML 1.1 认 yes/no/on/off；y/n 太容易误伤（比如姓名缩写），不当布尔。"""
    value = text.lower()
    if value in ("true", "yes", "on"):
        return True
    if value in ("false", "no", "off"):
        return False
    return None


def _looks_int(text: str) -> bool:
    return bool(re.fullmatch(r"[-+]?(0|[1-9][0-9_]*)", text)) or bool(re.fullmatch(r"0x[0-9a-fA-F]+", text))


def _looks_float(text: str) -> bool:
    if not re.fullmatch(r"[-+]?(\.[0-9]+|[0-9][0-9_]*(\.[0-9_]*)?)([eE][-+]?[0-9]+)?", text):
        return False
    return "." in text or "e" in text or "E" in text


def _looks_octal_or_hex(text: str) -> bool:
    return bool(re.fullmatch(r"[-+]?0[0-9_]+", text)) or bool(re.fullmatch(r"0x[0-9a-fA-F]+", text))


def _int(text: str):
    clean = text.replace("_", "")
    try:
        return int(clean, 10)
    except ValueError:
        pass
    if clean.startswith("0x"):
        try:
            return int(clean[2:], 16)
        except ValueError:
            pass
    return text


def _number(text: str):
    clean = text.replace("_", "")
    try:
        value = float(clean)
    except ValueError:
        return text
    # .inf / .nan JSON 里没有对应值，保留字符串比悄悄变成 null 诚实
    if math.isnan(value) or math.isinf(value):
        return text
    return value


# ---------- JSON → YAML ----------


def json_to_yaml(text: str) -> str:
    """JSON → YAML。"""
    try:
        root = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidOperationException(f"JSON 解析失败：{exc.msg}") from exc

    out: list[str] = []
    _emit(root, out, 0, None)
    return "".join(out).rstrip()


def _emit(node, out: list[str], indent: int, first_pad: str | None) -> None:
    """first_pad 用于把序列项拼在 "- " 后面：`- id: 1` 而不是把整个映射缩进换行。

    out 里每段自带换行，最后统一拼接——跟 C# 的 StringBuilder + AppendLine 一致。
    """
    if isinstance(node, dict):
        if not node:
            out.append("{}")
            return
        pad = " " * indent
        first = True
        for key, value in node.items():
            out.append(first_pad if (first and first_pad is not None) else pad)
            first = False
            out.append(_yaml_key(key) + ":")
            if _is_container(value) and len(value) > 0:
                out.append("\n")
                _emit(value, out, indent + 2, None)
            else:
                out.append(" " + _scalar_of(value) + "\n")
        return
    if isinstance(node, list):
        if not node:
            out.append("[]")
            return
        pad = " " * indent
        for item in node:
            out.append(pad + "-")
            if _is_container(item) and len(item) > 0:
                _emit(item, out, indent + 2, " ")
            else:
                out.append(" " + _scalar_of(item) + "\n")
        return
    out.append(_scalar_of(node))


def _is_container(node) -> bool:
    return isinstance(node, (dict, list))


def _yaml_key(key: str) -> str:
    return key if _plain_safe(key) else _quote(key)


def _scalar_of(node) -> str:
    if node is None:
        return "null"
    if isinstance(node, bool):
        return "true" if node else "false"
    if isinstance(node, int):
        return str(node)
    if isinstance(node, float):
        return _yaml_number(node)
    if isinstance(node, str):
        return node if _plain_safe(node) else _quote(node)
    if isinstance(node, dict):
        return "{}" if not node else ""
    if isinstance(node, list):
        return "[]" if not node else ""
    return ""


def _yaml_number(value: float) -> str:
    """整数补一位小数，避免 1.0 输出成 1 之后类型从 double 掉成 int。"""
    if math.isnan(value) or math.isinf(value):
        return '"null"'
    text = _dotnet_double(value)
    return text if any(ch in text for ch in ".eE") else text + ".0"


def _dotnet_double(value: float) -> str:
    """对应 .NET 的 double.ToString("R")：最短往返表示，整数值不带小数点。"""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    text = repr(value)
    if "e" in text:
        mantissa, _, exponent = text.partition("e")
        sign = "-" if exponent.startswith("-") else "+"
        digits = exponent.lstrip("+-").lstrip("0") or "0"
        return f"{mantissa}E{sign}{digits}"
    return text


def _plain_safe(text: str) -> bool:
    """能裸写（plain）的字符串：非空、首尾无空格、不含结构性字符、也不会被读回成别的类型。"""
    if not text or text != text.strip():
        return False
    if _bool_of(text) is not None or text in ("~", "null", "Null", "NULL"):
        return False
    if _looks_int(text) or _looks_float(text) or _looks_octal_or_hex(text):
        return False
    # 解析时我们故意不把 Y/N 当布尔，但输出时必须加引号——别的 YAML 1.1 读法会把它当 true，
    # 裸写等于把 "Y" 悄悄交给下游解释
    if text.lower() in ("y", "n", ".inf", "-inf", ".nan"):
        return False
    if ": " in text or "#" in text or "\n" in text or "\r" in text or "\t" in text:
        return False
    return text[0] not in "-?:,[]{}#&*!|>'\"%@`" and '"' not in text and "\\" not in text


def _quote(text: str) -> str:
    """双引号标量用的转义与 JSON 兼容，YAML 解析器按同一套读回。"""
    out = ['"']
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append("\\u%04X" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)
