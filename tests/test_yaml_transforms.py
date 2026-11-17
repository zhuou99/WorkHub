"""YAML ⇄ JSON：标量类型判定、引号规则与往返一致性。

移植自 WorkHub.Tests/YamlTransformsTests.cs。
"""

from __future__ import annotations

import json

import pytest

from app.common.exceptions import InvalidOperationException
from app.toolbox.yaml_transforms import json_to_yaml, yaml_to_json


def test_yaml_to_json_resolves_scalar_types():
    text = """
name: 中文
flag: yes
hex: 0x10
ratio: 1.0
quoted: "123"
empty: ~
"""
    root = json.loads(yaml_to_json(text))
    assert root["name"] == "中文"
    assert root["flag"] is True
    assert root["hex"] == 16
    assert root["ratio"] == 1.0
    assert root["quoted"] == "123"
    assert root["empty"] is None


def test_yaml_to_json_keeps_type_when_quoted():
    """带引号的标量不重新定型。"""
    assert json.loads(yaml_to_json('v: "true"'))["v"] == "true"


def test_yaml_to_json_does_not_treat_y_n_as_bool():
    """YAML 1.1 认 yes/no/on/off，但 y/n 容易误伤（姓名缩写），不当布尔。"""
    assert json.loads(yaml_to_json("v: y"))["v"] == "y"
    assert json.loads(yaml_to_json("v: n"))["v"] == "n"


def test_yaml_to_json_keeps_leading_zero_as_string():
    assert json.loads(yaml_to_json("v: 01"))["v"] == "01"


def test_json_to_yaml_quotes_ambiguous_scalars():
    text = json_to_yaml('{"a":"yes","b":"Y","c":"","d":1.0,"e":{},"f":[]}')
    assert 'a: "yes"' in text
    assert 'b: "Y"' in text
    assert 'c: ""' in text
    assert "d: 1.0" in text
    assert "e: {}" in text
    assert "f: []" in text


def test_round_trip_keeps_nested_chinese_document():
    text = '{"标题":"中文测试","tags":["a","b"],"meta":{"ok":true,"count":2}}'
    yaml_text = json_to_yaml(text)
    root = json.loads(yaml_to_json(yaml_text))

    assert root["标题"] == "中文测试"
    assert len(root["tags"]) == 2
    assert root["meta"]["ok"] is True
    assert root["meta"]["count"] == 2


def test_round_trip_keeps_nested_document_shape():
    text = json_to_yaml('{"标题":"中文测试","tags":["a","b"],"meta":{"ok":true,"count":2}}')
    assert text == (
        "标题: 中文测试\n"
        "tags:\n"
        "  - a\n"
        "  - b\n"
        "meta:\n"
        "  ok: true\n"
        "  count: 2"
    )


def test_yaml_to_json_invalid_yaml_throws_readable_error():
    with pytest.raises(InvalidOperationException) as exc:
        yaml_to_json("a: [1,")
    assert "YAML 解析失败" in str(exc.value)


def test_json_to_yaml_invalid_json_throws_readable_error():
    with pytest.raises(InvalidOperationException) as exc:
        json_to_yaml("{")
    assert "JSON 解析失败" in str(exc.value)


def test_json_to_yaml_never_uses_folded_blocks():
    """多行字符串用双引号转义，不能折成 >-（回读会多出一个尾换行）。"""
    text = json_to_yaml(json.dumps({"note": "第一行\n第二行"}))
    assert ">-" not in text
    assert "\\n" in text
