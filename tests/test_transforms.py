"""工具箱纯函数：输入 → 输出契约钉死，改实现时先看这些用例。

移植自 WorkHub.Tests/TransformsTests.cs。
"""

from __future__ import annotations

import json

import pytest

from app.common.exceptions import FormatException
from app.toolbox import transforms


def test_base64_encodes_and_decodes():
    assert transforms.base64_transform("中文", decode=False) == "5Lit5paH"
    assert transforms.base64_transform("5Lit5paH", decode=True) == "中文"


def test_base64_decode_accepts_url_safe_and_missing_padding():
    # URL-safe 字符与省略的 = 都要能读回来
    assert transforms.base64_transform("fn5-", decode=True) == "~~~"
    assert transforms.base64_transform("YQ", decode=True) == "a"


@pytest.mark.parametrize(("plain", "encoded"), [("a b", "a%20b")])
def test_url_round_trips(plain, encoded):
    assert transforms.url(plain, decode=False) == encoded
    assert transforms.url(encoded, decode=True) == plain
    assert transforms.url("a+b", decode=True) == "a b"


def test_unicode_round_trips():
    encoded = transforms.unicode_escape("中\n\t\\", decode=False)
    assert encoded == "\\u4e2d\\n\\t\\\\"
    assert transforms.unicode_escape(encoded, decode=True) == "中\n\t\\"


def test_unicode_decode_keeps_unknown_escape_verbatim():
    """正则里 `.` 排在具体转义前面，`\\x` 不会被吃掉。"""
    assert transforms.unicode_escape("\\x", decode=True) == "\\x"


def test_hex_round_trips_and_rejects_invalid_pair():
    assert transforms.hex("AB", to_hex=True) == "41 42"
    assert transforms.hex("41 42", to_hex=False) == "AB"
    assert transforms.hex("0x41,0x42", to_hex=False) == "AB"

    with pytest.raises(FormatException) as exc:
        transforms.hex("41 4", to_hex=False)
    assert "不是合法的十六进制字节对" in str(exc.value)


def test_html_entity_round_trips():
    assert transforms.html_entity("<a>&", encode=True) == "&lt;a&gt;&amp;"
    assert transforms.html_entity("&lt;a&gt;&amp;", encode=False) == "<a>&"


def test_html_entity_uses_dotnet_apos_entity():
    """html.escape 会写成 `&#x27;`，.NET 是 `&#39;`。"""
    assert transforms.html_entity("it's", encode=True) == "it&#39;s"


def test_html_entity_leaves_non_ascii_alone():
    assert transforms.html_entity("中文", encode=True) == "中文"


@pytest.mark.parametrize("raw", ['{"a":1,"b":[1,2]}'])
def test_json_minify_and_pretty(raw):
    assert transforms.json_mode(raw, "minify") == '{"a":1,"b":[1,2]}'

    pretty = transforms.json_mode(raw, "pretty")
    assert '\n  "a": 1' in pretty
    assert '\n  "b": [' in pretty


def test_json_min_alias_also_minifies():
    """C# 那边目录里注册的是 "min"，但实现只认 "minify"，按了"压缩"其实输出格式化结果。
    Python 版把 "min" 也映射到压缩，并把这个差异记在 README 里。"""
    assert transforms.json_mode('{"a":1,"b":[1,2]}', "min") == '{"a":1,"b":[1,2]}'


def test_json_escape_and_unescape():
    # 默认编码器把引号写成 "，不是 \"
    assert transforms.json_mode('a"b', "escape") == '"a\\u0022b"'
    assert transforms.json_mode('"hello"', "unescape") == "hello"


def test_json_invalid_input_throws():
    with pytest.raises(FormatException):
        transforms.json_mode("{", "pretty")


def test_json_preserves_number_text():
    """格式化工具不该把 1e5 改成 100000.0。"""
    assert transforms.json_mode('{"a":1e5}', "minify") == '{"a":1e5}'
    assert transforms.json_mode('{"a":1.0}', "minify") == '{"a":1.0}'


def test_json_to_csharp_produces_class_and_properties():
    code = transforms.json_to_csharp('{"id":1,"user_name":"x","tags":["a"]}', "demo")
    assert "public class Demo" in code
    assert "public long Id { get; set; }" in code
    assert "public string UserName { get; set; }" in code
    assert "public List<string> Tags { get; set; }" in code


def test_json_to_typescript_parenthesizes_union_array():
    code = transforms.json_to_typescript('{"tags":["a",1]}', "Root")
    assert "export interface Root" in code
    assert "tags: (string | number)[];" in code


def test_json_xml_round_trips_shape():
    xml = transforms.json_to_xml('{"name":"a","list":[1,2]}')
    assert "<name>a</name>" in xml

    root = json.loads(transforms.xml_to_json(xml))["root"]
    assert root["name"] == "a"
    # 数组 XML 化后是同名重复元素，回读时会收成 { "item": [...] } 这种对象
    assert len(root["list"]["item"]) == 2
    assert root["list"]["item"][0] == "1"


def test_sql_format_uppercases_keywords():
    sql = transforms.sql_format("select id from t where id=1")
    assert sql.startswith("SELECT\n    ")
    assert "select" not in sql
    assert " FROM t WHERE " in sql


def test_cron_describes_fields_and_lists_next_runs():
    text = transforms.cron("*/5 * * * *")
    assert "每 5 分" in text
    assert "== 接下来 5 次 ==" in text

    six = transforms.cron("0 */10 8 * * *")
    assert "秒：0 秒" in six


def test_cron_rejects_wrong_field_count():
    with pytest.raises(FormatException) as exc:
        transforms.cron("1 2 3")
    assert "5 或 6 段" in str(exc.value)


def test_time_converts_timestamp():
    text = transforms.time_text("1700000000")
    assert "秒级时间戳：1700000000" in text
    assert "毫秒时间戳：1700000000000" in text


def test_time_rejects_unrecognized_input():
    with pytest.raises(FormatException) as exc:
        transforms.time_text("not a time")
    assert "无法识别" in str(exc.value)


def test_split_words_and_naming():
    assert transforms.split_words("userName") == ["user", "Name"]
    naming = transforms.naming("userName")
    assert "snake_case：user_name" in naming
    assert "kebab-case：user-name" in naming
    assert "PascalCase：UserName" in naming
    assert "camelCase：userName" in naming


@pytest.mark.parametrize(
    ("value", "mode", "expected"),
    [
        ("abc", "upper", "ABC"),
        ("ABC", "lower", "abc"),
        ("hello world", "title", "Hello World"),
        ("aBc", "swap", "AbC"),
        ("aBc", "unknown", "aBc"),
    ],
)
def test_case_transforms_as_named(value, mode, expected):
    assert transforms.case(value, mode) == expected


def test_case_title_keeps_leading_space():
    """正则切分会在前导空白处产生空的首段，结果因此保留一个前导空格。"""
    assert transforms.case(" hi", "title") == " Hi"


def test_hash_all_known_digests():
    text = transforms.hash_all("abc")
    assert "900150983cd24fb0d6963f7d28e17f72" in text  # MD5
    assert "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" in text  # SHA256


def test_hmac_known_vector():
    text = transforms.hmac_sign("key", "The quick brown fox jumps over the lazy dog")
    assert "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8" in text


def test_jwt_splits_header_and_payload():
    token = transforms.base64_transform('{"alg":"HS256"}', decode=False).rstrip("=") + "." + transforms.base64_transform(
        '{"sub":"42","exp":1700000000}', decode=False
    ).rstrip("=") + ".sig"
    text = transforms.jwt(token)
    assert "== Header ==" in text
    assert "== Payload ==" in text
    assert "== 过期时间 ==" in text


def test_jwt_rejects_short_token():
    with pytest.raises(FormatException) as exc:
        transforms.jwt("abc")
    assert "三段" in str(exc.value)
