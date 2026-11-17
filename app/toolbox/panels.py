"""万能工具台里的「面板型」工具。

C# 那边这些是 Blazor 组件（WorkHub/Components/Tools/*.razor.cs），交互在浏览器里；
API 化之后改成「参数 → 结果」的纯函数，行为口径照搬。

10 个面板工具：unit / regex / diff / count / hmac / guid / password / qr / color / translate。
"""

from __future__ import annotations

import re
import secrets
import string
import uuid
from array import array
from dataclasses import dataclass
from decimal import Decimal

from app.common.exceptions import FormatException
from app.common.ulid import decode_time, monotonic
from app.common.unit_catalog import UnitGroup, convert_all, group
from app.toolbox import transforms

__all__ = [
    "unit_convert",
    "regex_test",
    "diff_text",
    "count_text",
    "hmac_sign",
    "guid_batch",
    "password_batch",
    "qr_code",
    "color_convert",
    "DIFF_LINE_CAP",
    "REGEX_MATCH_CAP",
]

DIFF_LINE_CAP = 1200
REGEX_MATCH_CAP = 200


# ---------- 单位换算 ----------


def unit_convert(group_id: str, from_id: str, value: Decimal | str | int) -> dict:
    """把一个值换算到该组全部单位。"""
    target: UnitGroup = group(group_id)
    source = next((unit for unit in target.units if unit.id == from_id), None)
    if source is None:
        raise FormatException(f"单位 {from_id} 不在「{target.name}」这一组里。")
    amount = Decimal(str(value))
    rows = convert_all(target, source, amount)
    return {
        "groupId": target.id,
        "groupName": target.name,
        "fromId": source.id,
        "value": str(amount),
        "units": [{"id": unit.id, "label": unit.name, "text": text} for unit, text in rows],
    }


# ---------- 正则测试 ----------


def regex_test(pattern: str, subject: str, ignore_case: bool = False, multiline: bool = False) -> dict:
    """列出匹配项与分组（上限 200 条）。"""
    if not pattern or not subject:
        return {"matches": [], "count": 0, "error": "请填写表达式与测试文本。"}
    flags = 0
    if ignore_case:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        return {"matches": [], "count": 0, "error": f"表达式无效：{exc}"}

    matches = []
    for index, match in enumerate(compiled.finditer(subject)):
        if index >= REGEX_MATCH_CAP:
            break
        matches.append(
            {
                "index": match.start(),
                "value": match.group(0),
                "groups": list(match.groups()),
                "named": {key: value for key, value in (match.groupdict() or {}).items()},
            }
        )
    return {"matches": matches, "count": len(matches), "error": None if matches else "没有匹配项。"}


# ---------- 文本比对 ----------


def diff_text(left: str, right: str) -> dict:
    """逐行 Diff。掐掉公共前后缀后再跑 LCS，结果与 C# 侧一致。"""
    if not left and not right:
        return {"rows": [], "add": 0, "del": 0, "same": 0, "error": "请先输入两段文本。"}

    a = _split_lines(left)
    b = _split_lines(right)
    if len(a) > DIFF_LINE_CAP and len(b) > DIFF_LINE_CAP:
        return {
            "rows": [],
            "add": 0,
            "del": 0,
            "same": 0,
            "error": f"文本过长（各超过 {DIFF_LINE_CAP} 行），Diff 仅支持较小文本。",
        }

    pre = 0
    while pre < len(a) and pre < len(b) and a[pre] == b[pre]:
        pre += 1
    suf = 0
    while suf < len(a) - pre and suf < len(b) - pre and a[len(a) - 1 - suf] == b[len(b) - 1 - suf]:
        suf += 1

    core_a = a[pre : len(a) - suf]
    core_b = b[pre : len(b) - suf]
    middle = _lcs(core_a, core_b)

    rows: list[tuple[str, str]] = [("same", line) for line in a[:pre]]
    rows.extend(middle)
    rows.extend(("same", line) for line in a[len(a) - suf :])

    added = sum(1 for op, _ in rows if op == "add")
    deleted = sum(1 for op, _ in rows if op == "del")
    same = len(rows) - added - deleted
    return {
        "rows": [{"op": op, "line": line} for op, line in rows],
        "add": added,
        "del": deleted,
        "same": same,
        "error": None,
    }


def _split_lines(text: str) -> list[str]:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _lcs(a: list[str], b: list[str]) -> list[tuple[str, str]]:
    """最长公共子序列（与 C# 的 DiffTool.Lcs 同一套 DP，输出必须一致）。"""
    n, m = len(a), len(b)
    width = m + 1
    # 用紧凑整型数组代替二维列表：1200×1200 的表用 list 会吃掉几十 MB。
    dp = array("i", [0]) * ((n + 1) * width)
    for i in range(n - 1, -1, -1):
        row = i * width
        below = (i + 1) * width
        current = a[i]
        for j in range(m - 1, -1, -1):
            if current == b[j]:
                dp[row + j] = dp[below + j + 1] + 1
            else:
                down = dp[below + j]
                right = dp[row + j + 1]
                dp[row + j] = down if down >= right else right

    result: list[tuple[str, str]] = []
    x = y = 0
    while x < n and y < m:
        if a[x] == b[y]:
            result.append(("same", a[x]))
            x += 1
            y += 1
        elif dp[(x + 1) * width + y] >= dp[x * width + y + 1]:
            result.append(("del", a[x]))
            x += 1
        else:
            result.append(("add", b[y]))
            y += 1
    while x < n:
        result.append(("del", a[x]))
        x += 1
    while y < m:
        result.append(("add", b[y]))
        y += 1
    return result


# ---------- 字数统计 ----------


def count_text(text: str) -> dict:
    """字符 / 中文 / 词 / 行 / 字节。"""
    value = text or ""
    lines = 0 if not value else value.count("\n") + 1
    return {
        "total": len(value),
        "noSpace": sum(1 for ch in value if not ch.isspace()),
        "chinese": sum(1 for ch in value if "一" <= ch <= "鿿"),
        "englishWords": len(re.findall(r"[A-Za-z]+", value)),
        "digits": sum(1 for ch in value if ch.isdigit()),
        "lines": lines,
        "bytes": len(value.encode("utf-8")),
    }


# ---------- HMAC ----------


def hmac_sign(key: str, data: str) -> str:
    """HMAC-SHA256 签名（Hex + Base64）。"""
    if not key or not data:
        raise FormatException("密钥与数据都不能为空。")
    return transforms.hmac_sign(key, data)


# ---------- GUID 批量 ----------


def guid_batch(count: int = 5, fmt: str = "D", upper: bool = False) -> dict:
    """批量生成 GUID（D/N/B/P）或 ULID。"""
    total = min(100, max(1, int(count)))
    if fmt == "ULID":
        ids = [monotonic() for _ in range(total)]
        times = [
            _ulid_time(item) for item in ids
        ]
        return {"ids": ids, "times": times, "format": fmt}

    if fmt not in ("D", "N", "B", "P"):
        raise FormatException(f"未知的 GUID 格式：{fmt}")
    ids = []
    for _ in range(total):
        text = str(uuid.uuid4())
        if fmt == "N":
            text = text.replace("-", "")
        elif fmt == "B":
            text = "{" + text + "}"
        elif fmt == "P":
            text = "(" + text + ")"
        ids.append(text.upper() if upper else text)
    return {"ids": ids, "times": [None] * total, "format": fmt}


def _ulid_time(value: str) -> str | None:
    try:
        return decode_time(value).astimezone().strftime("%H:%M:%S.%f")[:-3]
    except Exception:
        return None


# ---------- 随机密码 ----------


def password_batch(
    length: int = 16,
    count: int = 5,
    lower: bool = True,
    upper: bool = True,
    digit: bool = True,
    symbol: bool = False,
    no_confuse: bool = True,
) -> dict:
    """按字符集生成随机口令。"""
    size = min(64, max(6, int(length)))
    amount = min(20, max(1, int(count)))
    pool = ""
    if lower:
        pool += string.ascii_lowercase
    if upper:
        pool += string.ascii_uppercase
    if digit:
        pool += string.digits
    if symbol:
        pool += "!@#$%^&*()-_=+[]{};:,.<>?"
    if not pool:
        raise FormatException("至少勾选一种字符集。")
    if no_confuse:
        pool = "".join(ch for ch in pool if ch not in "Il1O0")
    passwords = ["".join(secrets.choice(pool) for _ in range(size)) for _ in range(amount)]
    return {"passwords": passwords, "length": size, "count": amount}


# ---------- 二维码 / 条码 ----------


def qr_code(value: str, mode: str = "qr", fmt: str = "code128", ecc: str = "M") -> dict:
    """校验条码内容；装了 segno 时顺带把二维码画成 SVG。

    C# 那边服务端只做校验，像素是 Blazor 组件画的——这里补上 SVG 输出，
    因为本项目没有界面，服务端得直接给得出图。
    """
    text = (value or "").strip()
    if not text:
        return {"valid": False, "error": "内容不能为空。", "svg": None, "mode": mode}
    if mode == "qr":
        return {"valid": True, "error": None, "svg": _qr_svg(text, ecc), "mode": mode}

    digits = text.strip("*")
    all_digits = digits.isdigit()
    error = {
        "ean13": "EAN-13 需要 12 或 13 位数字。" if (not all_digits or len(digits) not in (12, 13)) else None,
        "ean8": "EAN-8 需要 7 或 8 位数字。" if (not all_digits or len(digits) not in (7, 8)) else None,
        "upca": "UPC-A 需要 12 位数字。" if (not all_digits or len(digits) != 12) else None,
        "itf": "ITF 需要偶数位数字。" if (not all_digits or len(digits) % 2 != 0) else None,
        "code39": (
            "Code 39 仅支持字母数字与 - . $ / + % 空格。"
            if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-. $/+%" for ch in text.upper())
            else None
        ),
    }.get(fmt)
    return {"valid": error is None, "error": error, "svg": None, "mode": mode}


def _qr_svg(value: str, ecc: str) -> str | None:
    try:
        import segno
    except ImportError:
        return None
    try:
        return segno.make(value, error=(ecc or "M").lower()).svg()
    except Exception:
        return None


# ---------- 颜色转换 ----------


@dataclass
class Rgb:
    r: int
    g: int
    b: int


def color_convert(hex_value: str | None = None, rgb_text: str | None = None) -> dict:
    """取色 → HEX / RGB / HSL 互查，外加 4 档深浅色。"""
    if hex_value:
        parsed = _parse_hex(hex_value)
        if parsed is None:
            raise FormatException("无法识别，支持 #RGB / #RRGGBB / rgb(r, g, b)。")
    elif rgb_text:
        parsed = _parse_rgb(rgb_text)
        if parsed is None:
            raise FormatException("无法识别，支持 #RGB / #RRGGBB / rgb(r, g, b)。")
    else:
        raise FormatException("无法识别，支持 #RGB / #RRGGBB / rgb(r, g, b)。")

    hue, saturation, lightness = _rgb_to_hsl(parsed)
    return {
        "hex": _to_hex(parsed),
        "rgb": f"rgb({parsed.r}, {parsed.g}, {parsed.b})",
        "hsl": f"hsl({hue}, {saturation}%, {lightness}%)",
        "hue": hue,
        "saturation": saturation,
        "lightness": lightness,
        "shades": _shades(hue, saturation, lightness, parsed),
    }


def _parse_hex(text: str) -> Rgb | None:
    value = text.strip().lower()
    if value.startswith("#") and len(value) in (7, 4):
        if len(value) == 4:
            value = "#" + "".join(ch * 2 for ch in value[1:])
        if re.fullmatch(r"#[0-9a-f]{6}", value):
            return Rgb(int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
    return None


def _parse_rgb(text: str) -> Rgb | None:
    match = re.search(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", text.strip().lower())
    if not match:
        return None
    return Rgb(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _to_hex(color: Rgb) -> str:
    return f"#{color.r:02x}{color.g:02x}{color.b:02x}"


def _rgb_to_hsl(color: Rgb) -> tuple[int, int, int]:
    r, g, b = color.r / 255, color.g / 255, color.b / 255
    highest = max(r, g, b)
    lowest = min(r, g, b)
    hue = saturation = 0.0
    lightness = (highest + lowest) / 2
    if highest != lowest:
        delta = highest - lowest
        saturation = delta / (2 - highest - lowest) if lightness > 0.5 else delta / (highest + lowest)
        if highest == r:
            hue = (g - b) / delta + (6 if g < b else 0)
        elif highest == g:
            hue = (b - r) / delta + 2
        else:
            hue = (r - g) / delta + 4
        hue /= 6
    return round(hue * 360), round(saturation * 100), round(lightness * 100)


def _hsl_to_hex(hue: int, saturation: int, lightness: int) -> str:
    s, lightness_ratio = saturation / 100, lightness / 100

    def channel(n: int) -> int:
        k = (n + hue / 30.0) % 12
        a = s * min(lightness_ratio, 1 - lightness_ratio)
        value = lightness_ratio - a * max(-1, min(k - 3, min(9 - k, 1)))
        return round(value * 255)

    return f"#{channel(0):02x}{channel(8):02x}{channel(4):02x}"


def _shades(hue: int, saturation: int, lightness: int, base: Rgb) -> list[dict]:
    shades: list[dict] = []
    for index in range(1, 5):
        level = min(100, max(0, lightness - index * (lightness / 5.0)))
        shades.append({"label": f"暗 {index}", "hex": _hsl_to_hex(hue, saturation, int(level)).upper()})
    shades.append({"label": "原色", "hex": _to_hex(base).upper()})
    for index in range(1, 5):
        level = min(100, max(0, lightness + (100 - lightness) * index / 5.0))
        shades.append({"label": f"亮 {index}", "hex": _hsl_to_hex(hue, saturation, int(level)).upper()})
    return shades


def unit_info(group_id: str) -> list[dict]:
    """列出某一组的全部单位（给前端渲染下拉用）。"""
    target: UnitGroup = group(group_id)
    return [{"id": unit.id, "label": unit.name} for unit in target.units]
