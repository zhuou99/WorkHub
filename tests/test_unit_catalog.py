"""单位换算表：每组一个基准，验证「到基准 + 逆变换」没写反。

移植自 WorkHub.Tests/UnitCatalogTests.cs。
"""

from __future__ import annotations

from decimal import Decimal

from app.common.unit_catalog import Groups, convert_all, format_value, group


def to(group_id: str, from_id: str, to_id: str, value) -> str:
    target = group(group_id)
    source = next(u for u in target.units if u.id == from_id)
    return next(text for unit, text in convert_all(target, source, Decimal(value)) if unit.id == to_id)


def test_length_kilometer_is_thousand_meters():
    assert to("length", "km", "m", 1) == "1,000"


def test_length_meter_is_thousand_millimeters():
    assert to("length", "m", "mm", 1) == "1,000"


def test_area_mu_is_two_thirds_of_are():
    value = float(to("area", "mu", "m2", 1))
    assert 666.66 <= value <= 666.67


def test_data_gib_is_power_of_two_bytes():
    assert to("data", "GiB", "B", 1) == "1,073,741,824"


def test_data_gb_is_power_of_ten_bytes():
    assert to("data", "GB", "B", 1) == "1,000,000,000"


def test_temperature_freezing_and_boiling():
    assert to("temp", "c", "f", 0) == "32"
    assert to("temp", "f", "c", 32) == "0"
    assert to("temp", "c", "k", 0) == "273.15"
    assert to("temp", "c", "k", 100) == "373.15"


def test_time_hour_is_sixty_minutes():
    assert to("time", "h", "min", 1) == "60"


def test_format_normalizes_zero_thousands_and_scientific():
    assert format_value(Decimal(0)) == "0"
    assert format_value(Decimal("1234.5")) == "1,234.5"
    assert "E" in format_value(Decimal("0.0000001"))


def test_group_falls_back_to_first_when_unknown():
    assert group("不存在的组").id == Groups[0].id
