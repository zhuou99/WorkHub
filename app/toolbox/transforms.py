"""工具箱纯函数：输入字符串 → 输出字符串，失败抛带中文提示的异常。

对应 C# 的 WorkHub/Common/Transforms.cs。

几处 .NET 特有行为必须原样保留，否则工具输出会变：
- Base64 解码要先做 URL-safe 替换、去尾 `=`、再补齐到 4 的倍数。
- Url 编码用 RFC 3986 的 `%20`，不是 `+`。
- Unicode 解码的正则里 `.` 排在具体转义前面，`\\x` 会原样保留。
- Hex 解码的字节对必须恰好 2 位，`0x` 只认小写且全局剥离。
- HtmlEntity 用 .NET 的 `&#39;`（不是 html.escape 的 `&#x27;`），且不动非 ASCII。
- Json 的 escape 模式用 .NET 默认编码器（`\\u0022`、大写 `\\uXXXX`）。
- Case 的 title 模式保留前导空格（正则切分会产生空的首段）。
- SqlFormat 只有关键字大写与 SELECT 后的换行缩进真正生效。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import urllib.parse
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from app.common.exceptions import FormatException
from app.toolbox.json_codec import JsonNumber, dotnet_default_escape, parse_json, write_json

__all__ = [
    "base64_transform",
    "url",
    "unicode_escape",
    "hex",
    "html_entity",
    "jwt",
    "json_mode",
    "json_to_csharp",
    "json_to_typescript",
    "json_to_xml",
    "xml_to_json",
    "sql_format",
    "cron",
    "time_text",
    "split_words",
    "pascal",
    "naming",
    "case",
    "hash_all",
    "hmac_sign",
]

_WEEKDAY_FULL = ("星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六")
_WEEKDAY_SHORT = ("周日", "周一", "周二", "周三", "周四", "周五", "周六")

_CJK = "一-鿿"


def _clean(text: str | None) -> str:
    return (text or "").strip()


def _try_int(text: str) -> int | None:
    """对应 .NET 的 int.TryParse：允许前后空白与正负号。"""
    text = text.strip()
    if not text:
        return None
    body = text[1:] if text[0] in "+-" else text
    if not body.isdigit():
        return None
    try:
        return int(text)
    except ValueError:
        return None


# ---------- 编解码 ----------


def base64_transform(text: str, decode: bool = False) -> str:
    """Base64 编解码。解码兼容 URL-safe 字符与缺失的填充。"""
    if not decode:
        return base64.b64encode(text.encode("utf-8")).decode("ascii")
    normalized = _clean(text).replace("-", "+").replace("_", "/").rstrip("=")
    normalized += "=" * ((4 - len(normalized) % 4) % 4)
    try:
        # .NET 的 Convert.FromBase64String 会忽略空白，这里同样先去掉。
        raw = base64.b64decode("".join(normalized.split()), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise FormatException(f"不是合法的 Base64 文本：{exc}") from exc
    return raw.decode("utf-8", errors="replace")


def url(text: str, decode: bool = False) -> str:
    """URL 编解码。编码用 RFC 3986 的 %20，不是加号。"""
    if decode:
        return urllib.parse.unquote(text.replace("+", " "))
    return urllib.parse.quote(text, safe="")


_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})|\\(.|\\n|\r|\t|\n|\\)")


def unicode_escape(text: str, decode: bool = False) -> str:
    """Unicode 转义编解码。

    编码按 UTF-16 码元逐个处理（跟 C# 遍历 char 一致），非 BMP 字符会拆成两个代理项。
    """
    if not decode:
        out: list[str] = []
        for raw in _utf16_units(text):
            ch = chr(raw)
            if ch == "\\":
                out.append("\\\\")
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            elif raw < 0x20 or raw > 0x7E:
                out.append("\\u%04x" % raw)
            else:
                out.append(ch)
        return "".join(out)

    def replace(match: re.Match) -> str:
        if match.group(1):
            return chr(int(match.group(1), 16))
        token = match.group(2)
        return {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", "/": "/"}.get(token, match.group(0))

    return _UNICODE_ESCAPE.sub(replace, text)


def _utf16_units(text: str) -> Iterable[int]:
    """按 UTF-16 码元拆开（.NET 的 char 就是 UTF-16 码元）。"""
    data = text.encode("utf-16-le")
    for index in range(0, len(data), 2):
        yield data[index] | (data[index + 1] << 8)


def hex(text: str, to_hex: bool = True) -> str:
    """文本 ⇄ 十六进制字节。"""
    if to_hex:
        return " ".join(f"{byte:02x}" for byte in text.encode("utf-8"))
    normalized = re.sub(r"0x|[,\s]+", " ", text)
    data = bytearray()
    for part in normalized.split(" "):
        if not part:
            continue
        if len(part) != 2 or not re.fullmatch(r"[0-9a-fA-F]{2}", part):
            raise FormatException(f"“{part}”不是合法的十六进制字节对。")
        data.append(int(part, 16))
    return data.decode("utf-8", errors="replace")


def html_entity(text: str, encode: bool = True) -> str:
    """HTML 实体编解码。.NET 的 HtmlEncode 用 `&#39;` 表示单引号，且不动非 ASCII。"""
    if encode:
        out = []
        for ch in text:
            if ch == "&":
                out.append("&amp;")
            elif ch == "<":
                out.append("&lt;")
            elif ch == ">":
                out.append("&gt;")
            elif ch == '"':
                out.append("&quot;")
            elif ch == "'":
                out.append("&#39;")
            else:
                out.append(ch)
        return "".join(out)
    return _html_decode(text)


_NAMED_ENTITIES = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
    "nbsp": " ",
}


def _html_decode(text: str) -> str:
    def replace(match: re.Match) -> str:
        body = match.group(1)
        if body.startswith("#"):
            try:
                code = int(body[2:], 16) if body[1:2] in ("x", "X") else int(body[1:])
            except ValueError:
                return match.group(0)
            if 0 <= code <= 0x10FFFF:
                return chr(code)
            return match.group(0)
        return _NAMED_ENTITIES.get(body.lower(), match.group(0))

    return re.sub(r"&(#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);", replace, text)


def jwt(text: str) -> str:
    """拆出 JWT 的 Header / Payload / 过期时间（只看内容，不验签名）。"""
    parts = _clean(text).split(".")
    if len(parts) < 2:
        raise FormatException("JWT 应包含 header.payload.signature 三段（以 . 分隔）。")

    lines = ["== Header ==", _pretty_json(base64_transform(parts[0], decode=True))]
    lines.append("== Payload ==")
    payload_text = base64_transform(parts[1], decode=True)
    lines.append(_pretty_json(payload_text))

    claims = parse_json(payload_text)
    if isinstance(claims, dict):
        exp = claims.get("exp")
        if isinstance(exp, JsonNumber) and exp.is_integer:
            lines.append("== 过期时间 == exp = " + _from_unix(int(exp.value)))
    return "\n".join(lines).rstrip()


def _pretty_json(text: str) -> str:
    return write_json(parse_json(text), indented=True)


def _from_unix(ts: int) -> str:
    """Unix 时间戳 → 本地时间文案。"""
    seconds = ts / 1000 if len(str(ts)) >= 13 else ts
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S") + "（本地）"


# ---------- JSON ----------


def json_mode(text: str, mode: str) -> str:
    """JSON 格式化 / 压缩 / 转义 / 还原。

    mode 取值：escape、unescape、minify（别名 min）、pretty（默认）。
    """
    if mode == "escape":
        return dotnet_default_escape(text)
    if mode == "unescape":
        stripped = text.strip()
        if not stripped.startswith('"'):
            stripped = '"' + stripped + '"'
        value = parse_json(stripped)
        if not isinstance(value, str):
            raise FormatException("要还原的不是一个 JSON 字符串。")
        return value
    if mode in ("minify", "min"):
        return write_json(parse_json(text), indented=False)
    return write_json(parse_json(text), indented=True)


# ---------- JSON → C# ----------


def json_to_csharp(text: str, root_name: str = "Result") -> str:
    """由 JSON 样例生成 POCO 实体类。"""
    document = parse_json(text)
    name = "Result" if not (root_name or "").strip() else _sanitize_ident(root_name)
    classes: list[tuple[str, list[str]]] = []
    root_type = _build_csharp(document, name, classes)

    lines = ["using System.Text.Json.Serialization;", ""]
    for cls_name, props in classes:
        lines.append(f"public class {cls_name}")
        lines.append("{")
        for prop in props:
            lines.append(f"    {prop}")
        lines.append("}")
        lines.append("")
    if root_type != name:
        lines.append(f"public class RootObject {{ public {root_type} Data {{ get; set; }} }}")
    return "\n".join(lines).rstrip()


def _build_csharp(element, hint: str, classes: list[tuple[str, list[str]]]) -> str:
    if isinstance(element, dict):
        cls = _unique_name(_pascal(_sanitize_ident(hint)), classes)
        props: list[str] = []
        classes.append((cls, props))
        for key, value in element.items():
            prop_type = _csharp_type(value, key, classes)
            name = _pascal(key)
            if name != key and not _is_ascii_name(key):
                attr = f'\n    [JsonPropertyName("{key}")]'
            elif name != key and _needs_escape(key, name):
                attr = f'    [JsonPropertyName("{key}")]'
            else:
                attr = None
            prefix = f"{attr}\n    " if attr is not None else "    "
            props.append(f"{prefix}public {prop_type} {name} {{ get; set; }}")
        if not props:
            classes.remove((cls, props))
            return "object"
        return cls
    if isinstance(element, list):
        return _csharp_array_type(element, hint, classes)
    return "object"


def _csharp_type(value, hint: str, classes: list[tuple[str, list[str]]]) -> str:
    if isinstance(value, dict):
        return _build_csharp(value, hint, classes)
    if isinstance(value, list):
        return _csharp_array_type(value, hint, classes)
    if value is True or value is False:
        return "bool"
    if isinstance(value, JsonNumber):
        return "long" if value.is_integer else "double"
    if isinstance(value, str):
        return "string"
    return "object"


def _csharp_array_type(element: list, hint: str, classes: list[tuple[str, list[str]]]) -> str:
    first = next((item for item in element if item is not None), None)
    if isinstance(first, dict):
        item_type = _build_csharp(first, _singular(hint), classes)
    elif isinstance(first, list):
        item_type = "List<object>"
    elif first is True or first is False:
        item_type = "bool"
    elif isinstance(first, JsonNumber):
        item_type = "long" if first.is_integer else "double"
    elif isinstance(first, str):
        item_type = "string"
    else:
        item_type = "object"
    return f"List<{item_type}>"


def _needs_escape(origin: str, pascal_name: str) -> bool:
    """对应 .NET 的 NeedsEscape：首字符不是 ASCII 字母，或含 - / 空格。"""
    if len(origin) > 0 and not (origin[0].isascii() and origin[0].isalpha()):
        return True
    return "-" in origin or " " in origin


def _is_ascii_name(text: str) -> bool:
    return all(ch.isascii() and (ch.isalnum() or ch == "_") for ch in text)


def _unique_name(base_name: str, classes: list[tuple[str, list[str]]]) -> str:
    name = base_name
    index = 2
    while any(cls == name for cls, _ in classes):
        name = base_name + str(index)
        index += 1
    return name


def _sanitize_ident(text: str) -> str:
    chars = [ch if (ch.isalnum() or ch == "_") else "_" for ch in text]
    name = "".join(chars)
    if not name or name[0].isdigit():
        name = "_" + name
    return name


def _singular(hint: str) -> str:
    name = _pascal(hint)
    if len(name) > 3 and name.endswith("ies"):
        return name[:-3] + "y"
    if len(name) > 1 and name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name + "Item"


def _pascal(text: str) -> str:
    return "".join(word[0].upper() + word[1:].lower() for word in split_words(text) if word)


def pascal(text: str) -> str:
    """对应 C# 的 Transforms.Pascal：分词后每词首字母大写、其余小写。"""
    return _pascal(text)


# ---------- JSON → TypeScript ----------

TS_RESERVED = frozenset(
    {
        "break", "case", "catch", "class", "const", "continue", "debugger", "default", "delete", "do",
        "else", "enum", "export", "extends", "false", "finally", "for", "function", "if", "import",
        "in", "instanceof", "new", "null", "return", "super", "switch", "this", "throw", "true",
        "try", "typeof", "var", "void", "while", "with", "as", "async", "await", "interface", "let",
        "of", "static", "yield", "keyof",
    }
)


def json_to_typescript(text: str, root_name: str = "Root") -> str:
    """由 JSON 样例生成 interface：对象逐层建接口，数组按首个非 null 元素推断。"""
    document = parse_json(text)
    name = "Root" if not (root_name or "").strip() else _sanitize_ident(root_name)
    seen: list[str] = []
    bodies: list[tuple[str, list[str]]] = []

    root_type = _ts_of(document, name, seen, bodies)
    if root_type == name and not any(body[0] == name for body in bodies):
        return f"export type {name} = {root_type};"

    lines: list[str] = []
    for face, members in bodies:
        lines.append(f"export interface {face} {{")
        for member in members:
            lines.append(f"  {member}")
        lines.append("}")
        lines.append("")
    if root_type != name:
        lines.append(f"export type {name} = {root_type};")
    return "\n".join(lines).rstrip()


def _ts_of(element, hint: str, seen: list[str], bodies: list[tuple[str, list[str]]]) -> str:
    if isinstance(element, dict):
        face = _unique_ts(_pascal(_sanitize_ident(hint)), seen)
        seen.append(face)
        members: list[str] = []
        bodies.append((face, members))
        for key, value in element.items():
            member_type = _ts_of(value, key, seen, bodies)
            if value is None:
                member_type = "null"
            optional = value is None
            members.append(f"{_ts_prop(key)}{'?' if optional else ''}: {member_type};")
        if not members:
            bodies.remove((face, members))
            seen.remove(face)
            return "Record<string, unknown>"
        return face
    if isinstance(element, list):
        kinds = []
        for item in element:
            kind = _ts_kind(item)
            if kind not in kinds:
                kinds.append(kind)
        if not kinds:
            return "unknown[]"
        first = next((item for item in element if item is not None), None)
        inner = "unknown" if first is None else _ts_of(first, _singular(hint), seen, bodies)
        if len(kinds) > 1:
            inner = " | ".join(dict.fromkeys(_ts_kind_name(kind) for kind in kinds))
        # 联合类型必须加括号，否则 `number | string[]` 读起来是「数字 或 字符串数组」
        return f"({inner})[]" if " | " in inner else f"{inner}[]"
    return _ts_kind_name(_ts_kind(element))


def _ts_kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, JsonNumber):
        return "number"
    if isinstance(value, str):
        return "string"
    return "boolean"


def _ts_kind_name(kind: str) -> str:
    return {
        "null": "null",
        "object": "unknown",
        "array": "unknown[]",
        "number": "number",
        "string": "string",
        "boolean": "boolean",
    }.get(kind, "unknown")


def _ts_prop(name: str) -> str:
    # 中文键本身是合法 TS 标识符，裸写更干净；只有带 -、空格、保留字或数字开头的才加引号
    safe = (
        len(name) > 0
        and (name[0].isalpha() or name[0] in "_$")
        and all(ch.isalnum() or ch in "_$" for ch in name)
        and name.lower() not in TS_RESERVED
    )
    if safe:
        return name
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unique_ts(base_name: str, seen: list[str]) -> str:
    name = base_name if base_name else "Item"
    index = 2
    while name in seen:
        name = base_name + str(index)
        index += 1
    return name


# ---------- JSON ⇄ XML ----------


def json_to_xml(text: str) -> str:
    """JSON → XML。同名字段自动聚合成数组节点。"""
    import xml.etree.ElementTree as ET

    document = parse_json(text)
    root = ET.Element("root")
    _append_xml(root, document)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def _append_xml(element, value) -> None:
    import xml.etree.ElementTree as ET

    if isinstance(value, dict):
        for key, item in value.items():
            child = ET.Element(_safe_xml_name(key))
            _append_xml(child, item)
            element.append(child)
    elif isinstance(value, list):
        for item in value:
            child = ET.Element("item")
            _append_xml(child, item)
            element.append(child)
    elif value is None:
        element.set("nil", "true")
    else:
        element.text = _xml_scalar(value)


def _xml_scalar(value) -> str:
    if value is True:
        return "True"
    if value is False:
        return "False"
    if isinstance(value, JsonNumber):
        return value.text
    return str(value)


def _safe_xml_name(text: str) -> str:
    name = "".join(ch if (ch.isalnum() or ch in "_-.") else "_" for ch in text)
    if not name or name[0].isdigit() or name.lower().startswith("xml"):
        name = "e_" + name
    return name


def xml_to_json(text: str) -> str:
    """XML → JSON。属性带 @ 前缀，重复节点成数组。"""
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise FormatException(f"XML 解析失败：{exc}") from exc

    value = _element_to_value(root)
    return write_json({_local_name(root.tag): value}, indented=True)


def _element_to_value(element):

    children = list(element)
    if not children:
        return element.text or ""
    result: dict = {}
    for key, value in element.attrib.items():
        result["@" + _local_name(key)] = value
    groups: dict[str, list] = {}
    order: list[str] = []
    for child in children:
        name = _local_name(child.tag)
        if name not in groups:
            groups[name] = []
            order.append(name)
        groups[name].append(_element_to_value(child))
    for name in order:
        values = groups[name]
        key = name
        if key in result:
            key = key + "_"
        result[key] = values if len(values) > 1 else values[0]
    return result


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


# ---------- SQL / Cron ----------


SQL_KEYWORDS = (
    "select", "from", "where", "group by", "order by", "having", "union all", "union",
    "insert into", "values", "update", "set", "delete from", "left join", "right join",
    "inner join", "full join", "cross join", "join", "on", "and", "or", "limit", "offset",
)


def sql_format(text: str) -> str:
    """SQL 格式化：关键字大写 + SELECT 后断行缩进。"""
    result = re.sub(r"\s+", " ", text).strip()
    for keyword in SQL_KEYWORDS:
        result = re.sub(
            r"(?<![\w`])(" + re.escape(keyword) + r")(?![\w`])",
            lambda m: m.group(1).upper(),
            result,
            flags=re.IGNORECASE,
        )
    result = re.sub(r"^(SELECT)\s", r"\1\n    ", result, flags=re.IGNORECASE)
    return result.strip()


def cron(text: str) -> str:
    """5/6 段 cron → 中文说明 + 接下来 5 次触发时间。"""
    fields = [item for item in _clean(text).split(" ") if item]
    if len(fields) not in (5, 6, 7):
        raise FormatException(f"应为 5 或 6 段 cron 表达式，当前 {len(fields)} 段。")
    sec_start = 0 if len(fields) >= 6 else -1
    if len(fields) >= 6:
        sec_expr, minute, hour, dom, mon, dow = fields[:6]
    else:
        sec_expr, minute, hour, dom, mon, dow = "0", fields[0], fields[1], fields[2], fields[3], fields[4]

    lines = [
        f"秒：{_describe(sec_expr, '秒')}",
        f"分：{_describe(minute, '分')}",
        f"时：{_describe(hour, '时')}",
        f"日：{_describe(dom, '日')}",
        f"月：{_describe(mon, '月')}",
        f"周：{_describe(dow, '星期', _WEEKDAY_SHORT)}",
    ]
    lines.append("== 接下来 5 次 ==")
    for moment in _next_runs(sec_expr, minute, hour, dom, mon, dow, sec_start, 5):
        lines.append(moment.strftime("%Y-%m-%d %H:%M:%S ") + f"({_weekday_short(moment)})")
    return "\n".join(lines).rstrip()


def _describe(expr: str, unit: str, names: tuple[str, ...] | None = None) -> str:
    expr = expr.strip()
    if expr in ("*", "?"):
        return f"每{unit}" + ("（不限）" if names is not None else "")
    if expr.startswith("*/"):
        return f"每 {expr[2:]} {unit}"
    value = _try_int(expr)
    if value is not None:
        if names is not None and 0 <= value < len(names):
            return names[value]
        return f"{expr} {unit}"
    return "、".join(_describe_token(part.strip(), unit, names) for part in expr.split(","))


def _describe_token(text: str, unit: str, names: tuple[str, ...] | None) -> str:
    if "/" in text:
        parts = text.split("/")
        origin = "" if parts[0] in ("*", "?") else f"自 {parts[0]} 起"
        suffix = f"（{origin}）" if origin else ""
        return f"每 {parts[1]} {unit}{suffix}"
    if "-" in text:
        return text.replace("-", "~")
    value = _try_int(text)
    if names is not None and value is not None:
        return names[value % len(names)]
    return f"{text} {unit}"


def _match_set(expr: str, low: int, high: int) -> set[int]:
    values: set[int] = set()
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        step = 1
        if "/" in part:
            parts = part.split("/")
            part = parts[0]
            step_value = _try_int(parts[1])
            if step_value is None:
                raise FormatException(f"cron 步长不是整数：{parts[1]}")
            step = step_value
        if part in ("*", "?"):
            start, end = low, high
        elif "-" in part:
            bounds = part.split("-")
            start, end = int(bounds[0]), int(bounds[1])
        else:
            start = end = int(part)
        for value in range(start, end + 1, max(1, step)):
            values.add(value)
    return values


def _next_runs(sec, minute, hour, dom, mon, dow, sec_start: int, count: int) -> list[datetime]:
    secs = _match_set(sec, 0, 59) if sec_start >= 0 else {0}
    mins = _match_set(minute, 0, 59)
    hours = _match_set(hour, 0, 23)
    doms = _match_set(dom, 1, 31)
    mons = _match_set(mon, 1, 12)
    dows = _match_set(dow, 0, 6)
    if 7 in dows:
        dows.discard(7)
        dows.add(0)

    results: list[datetime] = []
    now = datetime.now()
    moment = now + timedelta(seconds=1)
    moment = moment.replace(microsecond=0, second=moment.second if sec_start >= 0 else 0)
    guard = 0
    while guard < 400_000 and len(results) < count:
        weekday = (moment.weekday() + 1) % 7  # .NET 的 DayOfWeek：周日为 0
        if (
            moment.month in mons
            and (moment.day in doms or dow == "*")
            and (dow == "*" or weekday in dows)
            and (dom == "*" or moment.day in doms)
            and moment.hour in hours
            and moment.minute in mins
            and moment.second in secs
        ):
            results.append(moment)
        moment = moment + (timedelta(seconds=1) if sec_start >= 0 else timedelta(minutes=1))
        if moment.year > now.year + 4:
            break
        guard += 1
    return results


def _weekday_short(moment: datetime) -> str:
    return _WEEKDAY_SHORT[(moment.weekday() + 1) % 7]


def _weekday_full(moment: datetime) -> str:
    return _WEEKDAY_FULL[(moment.weekday() + 1) % 7]


# ---------- 时间戳 ----------


def time_text(text: str) -> str:
    """空输入=当前时间；10/13 位时间戳 ⇄ 日期。"""
    value = _clean(text)
    if not value:
        now = datetime.now()
        lines = [
            f"本地时间：{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} ({_weekday_full(now)})",
            f"UTC 时间：{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}",
            f"秒级时间戳：{int(now.timestamp())}",
            f"毫秒时间戳：{int(now.timestamp() * 1000)}",
        ]
        return "\n".join(lines).rstrip()

    if value.isdigit() and len(value) in (10, 13, 19):
        number = int(value)
        if len(value) == 19:
            moment = datetime.fromtimestamp(number / 1_000_000)
        elif len(value) == 13:
            moment = datetime.fromtimestamp(number / 1000)
        else:
            moment = datetime.fromtimestamp(number)
        return _time_lines(moment)

    parsed = _parse_datetime(value)
    if parsed is None:
        raise FormatException("无法识别：请输入时间戳（10/13 位数字）或日期时间字符串。")
    return _time_lines(parsed)


def _time_lines(moment: datetime) -> str:
    stamp = moment.timestamp()
    return "\n".join(
        [
            f"秒级时间戳：{int(stamp)}",
            f"毫秒时间戳：{int(stamp * 1000)}",
            f"本地时间：{moment.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} ({_weekday_full(moment)})",
            f"UTC 时间：{moment.astimezone(UTC).strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    ).rstrip()


_TIME_ONLY = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")


def _parse_datetime(text: str) -> datetime | None:
    """宽松的日期解析，够用即可（.NET 那边走的是 CurrentCulture 的 TryParse）。"""
    candidates = [
        text,
        text.replace("/", "-"),
        text.replace("年", "-").replace("月", "-").replace("日", ""),
    ]
    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    # 纯时间按今天算（strptime 的无年份格式在 Python 3.15 会改行为，这里手写）
    only_time = _TIME_ONLY.match(text)
    if only_time:
        today = datetime.now()
        hour = int(only_time.group(1))
        minute = int(only_time.group(2))
        second = int(only_time.group(3) or 0)
        if hour < 24 and minute < 60 and second < 60:
            return today.replace(hour=hour, minute=minute, second=second, microsecond=0)
    return None


# ---------- 文本 ----------


def split_words(text: str) -> list[str]:
    """按驼峰与分隔符切词（中文按字成词）。"""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [word for word in re.split(rf"[^A-Za-z0-9{_CJK}]+", spaced) if word]


def _cap1(word: str) -> str:
    return word[0].upper() + word[1:] if word else word


def naming(text: str) -> str:
    """一词 → snake / kebab / Pascal / camel 全家桶。"""
    words = split_words(text)
    lower = [word.lower() for word in words]
    lines = [
        "snake_case：" + "_".join(lower),
        "kebab-case：" + "-".join(lower),
        "PascalCase：" + "".join(_cap1(word) for word in lower),
        "camelCase：" + "".join(word if i == 0 else _cap1(word) for i, word in enumerate(lower)),
        "UPPER_SNAKE：" + "_".join(word.upper() for word in lower),
        "Title Case：" + " ".join(_cap1(word) for word in lower),
    ]
    return "\n".join(lines).rstrip()


def case(text: str, mode: str) -> str:
    """大小写变换。"""
    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    if mode == "title":
        # 正则切分会在前导空白处产生空的首段，结果因此保留一个前导空格。
        return " ".join(_cap1(part) for part in re.split(r"\s+", text))
    if mode == "swap":
        return "".join(ch.lower() if ch.isupper() else ch.upper() if ch.islower() else ch for ch in text)
    return text


# ---------- 哈希 ----------


def hash_all(text: str) -> str:
    """MD5 / SHA1 / SHA256 / SHA512 一次全出。"""
    data = text.encode("utf-8")
    lines = [
        f"MD5     ：{hashlib.md5(data).hexdigest()}",
        f"SHA1    ：{hashlib.sha1(data).hexdigest()}",
        f"SHA256  ：{hashlib.sha256(data).hexdigest()}",
        f"SHA512  ：{hashlib.sha512(data).hexdigest()}",
    ]
    return "\n".join(lines).rstrip()


def hmac_sign(key: str, data: str) -> str:
    """HMAC-SHA256 签名（Hex + Base64）。"""
    digest = hmac.new(key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).digest()
    return f"Hex   ：{digest.hex()}\nBase64：{base64.b64encode(digest).decode('ascii')}"
