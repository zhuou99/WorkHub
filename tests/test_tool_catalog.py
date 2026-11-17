"""工具目录与执行：28 个工具的注册、检索口径与面板工具的行为。"""

from __future__ import annotations

import pytest

from app.common.exceptions import WorkHubError
from app.toolbox import catalog
from app.toolbox.runner import run_tool


def test_catalog_has_28_tools():
    assert len(catalog.ALL) == 28
    assert len({tool.id for tool in catalog.ALL}) == 28


def test_catalog_covers_all_categories():
    assert set(catalog.CATEGORIES) == {tool.category for tool in catalog.ALL}


def test_catalog_search_returns_all_for_blank_keyword():
    assert len(catalog.search(None)) == 28
    assert len(catalog.search("  ")) == 28


def test_catalog_search_matches_name_and_description():
    hits = [tool.id for tool in catalog.search("base64")]
    # hmac 的描述里也有 "Base64"，所以它也命中
    assert "base64" in hits
    assert "hmac" in hits


def test_catalog_search_is_case_insensitive_for_name():
    assert "base64" in [tool.id for tool in catalog.search("BASE64")]


def test_catalog_search_matches_id():
    """id 与 category 是原样匹配的（只有 Name / Description 转小写）。"""
    assert [tool.id for tool in catalog.search("json2ts")] == ["json2ts"]


def test_catalog_search_matches_chinese_description():
    hits = catalog.search("二维码")
    assert "qr" in [tool.id for tool in hits]


def test_io_tool_option_mapping_is_asymmetric():
    """base64 判 dec、hex 判 enc——统一成一个方向会把工具翻转。"""
    assert run_tool("base64", "中文", "enc")["output"] == "5Lit5paH"
    assert run_tool("base64", "5Lit5paH", "dec")["output"] == "中文"
    assert run_tool("hex", "AB", "enc")["output"] == "41 42"
    assert run_tool("hex", "41 42", "dec")["output"] == "AB"


def test_json_tool_min_option_compresses():
    assert run_tool("json", '{"a":1}', "min")["output"] == '{"a":1}'


def test_unknown_tool_raises():
    with pytest.raises(WorkHubError):
        run_tool("nope", "x")


def test_unit_tool_lists_all_units_of_group():
    result = run_tool("unit", params={"groupId": "data", "fromId": "GiB", "value": 1})
    rows = {row["id"]: row["text"] for row in result["data"]["units"]}
    assert rows["B"] == "1,073,741,824"


def test_regex_tool_reports_matches():
    result = run_tool("regex", params={"pattern": r"\d+", "subject": "a1 b22"})
    assert result["data"]["count"] == 2
    assert result["data"]["matches"][0]["value"] == "1"


def test_regex_tool_reports_invalid_pattern():
    result = run_tool("regex", params={"pattern": "[", "subject": "x"})
    assert result["data"]["error"].startswith("表达式无效")


def test_diff_tool_marks_added_and_removed_lines():
    result = run_tool("diff", params={"left": "a\nb\nc", "right": "a\nx\nc"})
    ops = [row["op"] for row in result["data"]["rows"]]
    assert "add" in ops
    assert "del" in ops
    assert result["data"]["same"] == 2


def test_count_tool_counts():
    result = run_tool("count", params={"text": "中文 abc 123\n第二行"})
    data = result["data"]
    assert data["chinese"] == 5
    assert data["englishWords"] == 1
    assert data["digits"] == 3
    assert data["lines"] == 2


def test_hmac_tool_returns_signature():
    result = run_tool("hmac", params={"key": "key", "data": "The quick brown fox jumps over the lazy dog"})
    assert "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8" in result["output"]


def test_guid_tool_generates_requested_count():
    result = run_tool("guid", params={"count": 3, "format": "D"})
    assert len(result["data"]["ids"]) == 3
    assert all(len(item) == 36 for item in result["data"]["ids"])


def test_guid_tool_ulid_format_is_sortable():
    result = run_tool("guid", params={"count": 3, "format": "ULID"})
    ids = result["data"]["ids"]
    assert ids == sorted(ids)
    assert all(len(item) == 26 for item in ids)


def test_password_tool_respects_length_and_charset():
    result = run_tool("password", params={"length": 12, "count": 2, "lower": True, "upper": False, "digit": False})
    for password in result["data"]["passwords"]:
        assert len(password) == 12
        assert password.islower() or password.isalpha()


def test_password_tool_rejects_empty_charset():
    with pytest.raises(WorkHubError):
        run_tool("password", params={"length": 12, "count": 1, "lower": False, "upper": False, "digit": False})


def test_qr_tool_validates_barcode_payload():
    result = run_tool("qr", params={"value": "123", "mode": "barcode", "format": "ean13"})
    assert result["data"]["valid"] is False
    assert "EAN-13" in result["data"]["error"]


def test_qr_tool_accepts_valid_barcode_payload():
    result = run_tool("qr", params={"value": "123456789012", "mode": "barcode", "format": "ean13"})
    assert result["data"]["valid"] is True


def test_color_tool_converts_hex_to_rgb_and_hsl():
    result = run_tool("color", params={"hex": "#2f5bff"})
    assert result["data"]["rgb"] == "rgb(47, 91, 255)"
    assert result["data"]["hsl"].startswith("hsl(")


def test_color_tool_accepts_short_hex():
    """#2f5 展开成 #22ff55。"""
    result = run_tool("color", params={"hex": "#2f5"})
    assert result["data"]["rgb"] == "rgb(34, 255, 85)"


def test_translate_tool_reports_phase_two():
    with pytest.raises(WorkHubError) as exc:
        run_tool("translate", params={"text": "hi"})
    assert "阶段 2" in str(exc.value)
