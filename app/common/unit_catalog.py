"""单位换算目录：八组单位，换算与格式化。

对应 C# 的 WorkHub/Common/UnitCatalog.cs 与 WorkHub/Models/Unit.cs。

全程用 Decimal（.NET 的 decimal 同款），不用 float。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext

__all__ = ["Unit", "UnitGroup", "Groups", "group", "convert_all", "format_value"]

KB = Decimal(1000)
KIB = Decimal(1024)


@dataclass(frozen=True)
class Unit:
    id: str
    name: str
    to_base: Callable[[Decimal], Decimal]
    from_base: Callable[[Decimal], Decimal]

    @staticmethod
    def linear(unit_id: str, name: str, factor: Decimal) -> Unit:
        """线性单位：换算就是乘除一个系数。"""
        return Unit(
            unit_id,
            name,
            lambda value: value * factor,
            lambda value: value / factor,
        )

    @staticmethod
    def affine(unit_id: str, name: str, to_base: Callable[[Decimal], Decimal],
               from_base: Callable[[Decimal], Decimal]) -> Unit:
        """仿射单位：温标这类要加减偏移的。"""
        return Unit(unit_id, name, to_base, from_base)


@dataclass(frozen=True)
class UnitGroup:
    id: str
    name: str
    units: tuple[Unit, ...]


def _temp_c_to_base(value: Decimal) -> Decimal:
    return value


def _temp_c_from_base(value: Decimal) -> Decimal:
    return value


def _temp_f_to_base(value: Decimal) -> Decimal:
    return (value - Decimal(32)) * Decimal(5) / Decimal(9)


def _temp_f_from_base(value: Decimal) -> Decimal:
    return value * Decimal(9) / Decimal(5) + Decimal(32)


def _temp_k_to_base(value: Decimal) -> Decimal:
    return value - Decimal("273.15")


def _temp_k_from_base(value: Decimal) -> Decimal:
    return value + Decimal("273.15")


Groups: tuple[UnitGroup, ...] = (
    UnitGroup(
        "length",
        "长度",
        (
            Unit.linear("mm", "毫米 mm", Decimal("0.001")),
            Unit.linear("cm", "厘米 cm", Decimal("0.01")),
            Unit.linear("m", "米 m（基准）", Decimal(1)),
            Unit.linear("km", "千米 km", Decimal(1000)),
            Unit.linear("in", "英寸 in", Decimal("0.0254")),
            Unit.linear("ft", "英尺 ft", Decimal("0.3048")),
            Unit.linear("yd", "码 yd", Decimal("0.9144")),
            Unit.linear("mi", "英里 mi", Decimal("1609.344")),
            Unit.linear("nmi", "海里 nmi", Decimal(1852)),
            Unit.linear("ly", "光年 ly", Decimal("94607304725808")),
        ),
    ),
    UnitGroup(
        "area",
        "面积",
        (
            Unit.linear("mm2", "平方毫米 mm²", Decimal("0.000001")),
            Unit.linear("m2", "平方米 m²（基准）", Decimal(1)),
            Unit.linear("ha", "公顷 ha", Decimal(10000)),
            Unit.linear("km2", "平方千米 km²", Decimal(1000000)),
            Unit.linear("mu", "亩", Decimal(2000) / Decimal(3)),
            Unit.linear("acre", "英亩 acre", Decimal("4046.8564224")),
        ),
    ),
    UnitGroup(
        "volume",
        "体积",
        (
            Unit.linear("ml", "毫升 mL", Decimal("0.001")),
            Unit.linear("l", "升 L（基准）", Decimal(1)),
            Unit.linear("m3", "立方米 m³", Decimal(1000)),
            Unit.linear("gal", "加仑（美制）gal", Decimal("3.785411784")),
            Unit.linear("floz", "液盎司（美制）fl oz", Decimal("0.0295735295625")),
        ),
    ),
    UnitGroup(
        "mass",
        "重量",
        (
            Unit.linear("g", "克 g", Decimal("0.001")),
            Unit.linear("kg", "千克 kg（基准）", Decimal(1)),
            Unit.linear("t", "吨 t", Decimal(1000)),
            Unit.linear("jin", "斤（市斤）", Decimal("0.5")),
            Unit.linear("liang", "两（市两）", Decimal("0.05")),
            Unit.linear("lb", "磅 lb", Decimal("0.45359237")),
            Unit.linear("oz", "盎司 oz", Decimal("0.028349523125")),
        ),
    ),
    UnitGroup(
        "data",
        "存储",
        (
            Unit.linear("B", "字节 B（基准）", Decimal(1)),
            Unit.linear("KB", "千字节 KB（1000）", KB),
            Unit.linear("MB", "兆字节 MB", KB * 1000),
            Unit.linear("GB", "吉字节 GB", KB * 1000 * 1000),
            Unit.linear("TB", "太字节 TB", KB * 1000 * 1000 * 1000),
            Unit.linear("KiB", "二进制 KiB（1024）", KIB),
            Unit.linear("MiB", "二进制 MiB", KIB * 1024),
            Unit.linear("GiB", "二进制 GiB", KIB * 1024 * 1024),
            Unit.linear("TiB", "二进制 TiB", KIB * 1024 * 1024 * 1024),
        ),
    ),
    UnitGroup(
        "time",
        "时间",
        (
            Unit.linear("ms", "毫秒 ms", Decimal("0.001")),
            Unit.linear("s", "秒 s（基准）", Decimal(1)),
            Unit.linear("min", "分钟 min", Decimal(60)),
            Unit.linear("h", "小时 h", Decimal(3600)),
            Unit.linear("d", "天 d", Decimal(86400)),
            Unit.linear("wk", "周 wk", Decimal(604800)),
            Unit.linear("yr", "年（365 天）", Decimal(31536000)),
        ),
    ),
    UnitGroup(
        "speed",
        "速度",
        (
            Unit.linear("kmh", "千米每小时 km/h", Decimal(1)),
            Unit.linear("mps", "米每秒 m/s", Decimal("3.6")),
            Unit.linear("mph", "英里每小时 mph", Decimal("1.609344")),
            Unit.linear("kn", "节 kn（海里/时）", Decimal("1.852")),
        ),
    ),
    UnitGroup(
        "temp",
        "温度",
        (
            Unit.affine("c", "摄氏度 ℃（基准）", _temp_c_to_base, _temp_c_from_base),
            Unit.affine("f", "华氏度 ℉", _temp_f_to_base, _temp_f_from_base),
            Unit.affine("k", "开尔文 K", _temp_k_to_base, _temp_k_from_base),
        ),
    ),
)


def group(group_id: str | None) -> UnitGroup:
    """按 id 取组；找不到时退回第一组（长度）。"""
    for item in Groups:
        if item.id == group_id:
            return item
    return Groups[0]


def convert_all(target_group: UnitGroup, from_unit: Unit, value: Decimal) -> list[tuple[Unit, str]]:
    """把 value（from 单位）换算到该组所有单位，按组内声明顺序返回。"""
    base_value = from_unit.to_base(value)
    return [(unit, format_value(unit.from_base(base_value))) for unit in target_group.units]


def format_value(value: Decimal) -> str:
    """有效数字 + 千分位；过小/过大时保留科学计数，不做四舍五入成 0 的傻事。

    对应 .NET 的 ToString("G12") + ToString("#,0.##########")。
    """
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= Decimal("1e12") or magnitude < Decimal("1e-6"):
        return _general(value, 6)
    text = _general(value, 12)
    if "E" in text:
        return text
    return _grouped(Decimal(text))


def _general(value: Decimal, digits: int) -> str:
    """对应 .NET 的 decimal.ToString("G{n}")。

    .NET 的规则：保留 n 位有效数字；调整指数落在 (-5, n) 之间用定点，否则用科学计数。
    Python 自带的 Decimal 'G' 用的是十进制自己的指数（Decimal('1E+3') 会输出 1E+3），
    跟 .NET 不是一回事，所以这里自己实现。
    """
    if value == 0:
        return "0"
    adjusted = _adjusted_exponent(value)
    if -5 < adjusted < digits:
        rounded = _round_significant(value, digits)
        text = f"{rounded:f}"
        return "0" if text in ("-0", "-0.0") else text
    return _scientific(value, digits)


def _adjusted_exponent(value: Decimal) -> int:
    """调整指数：把数写成 d.ddd × 10^exp 时的 exp。"""
    _, digit_tuple, exponent = value.as_tuple()
    return len(digit_tuple) + exponent - 1


def _round_significant(value: Decimal, digits: int) -> Decimal:
    """按有效数字四舍五入。

    .NET 的格式化器用「中点远离零」，不是 Math.Round 的银行家舍入——
    格式化与 Math.Round 是两套规则，这里跟格式化对齐。
    """
    adjusted = _adjusted_exponent(value)
    target_exp = adjusted - (digits - 1)
    with localcontext() as ctx:
        ctx.prec = 80
        return value.quantize(Decimal(1).scaleb(target_exp), rounding=ROUND_HALF_UP)


def _scientific(value: Decimal, digits: int) -> str:
    """科学计数：1.23457E+12。尾零去掉，指数至少两位。"""
    rounded = _round_significant(value, digits)
    _, digit_tuple, exponent = rounded.as_tuple()
    coefficient = int("".join(str(d) for d in digit_tuple))
    adjusted = len(digit_tuple) + exponent - 1
    mantissa = f"{Decimal(coefficient).scaleb(-(len(digit_tuple) - 1)):f}"
    if "." in mantissa:
        mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa}E{adjusted:+03d}"


def _grouped(value: Decimal) -> str:
    """对应 .NET 的 ToString("#,0.##########")：千分位 + 最多 10 位小数，尾零去掉。"""
    with localcontext() as ctx:
        ctx.prec = 80
        quantized = value.quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)
    text = f"{quantized:,.10f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
