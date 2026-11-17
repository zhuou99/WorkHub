"""状态字典与悬空引用口径：多个页面共用同一套中文与「未填/已删除」判定。

移植自 WorkHub.Tests/LabelsTests.cs。
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.common import labels
from app.models.crm import WhClient, WhProject


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("active", "进行中"),
        ("accept", "验收中"),
        ("maintain", "维护期"),
        ("done", "已完结"),
        ("talking", "洽谈中"),
        ("unknown", "洽谈中"),
    ],
)
def test_project_status_maps_known_and_falls_back(value, expected):
    assert labels.project_status(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("opened", "已开票"), ("sent", "已寄出"), ("paid", "已回款"), ("void", "作废"), ("", "已开票")],
)
def test_invoice_status_maps_known_and_falls_back(value, expected):
    assert labels.invoice_status(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("general", "普票"), ("special", "专票"), ("agent", "个人代开")],
)
def test_invoice_type_maps_known(value, expected):
    assert labels.invoice_type(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("pending", "待收"), ("paid", "已到账"), ("skipped", "已免除")],
)
def test_plan_status_maps_known(value, expected):
    assert labels.plan_status(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("doing", "进行中"), ("done", "已完成"), ("hold", "搁置"), ("todo", "待办")],
)
def test_task_status_maps_known(value, expected):
    assert labels.task_status(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("high", "急"), ("normal", "普通"), ("low", "不急")],
)
def test_priority_maps_known(value, expected):
    assert labels.priority(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("wechat", "微信"), ("phone", "电话"), ("meet", "见面"), ("mail", "邮件"), ("other", "其他")],
)
def test_comm_type_maps_known(value, expected):
    assert labels.comm_type(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("friend", "朋友介绍"), ("referral", "老客户转介"), ("platform", "平台接单"), ("other", "其他"), ("unknown", "未知")],
)
def test_source_maps_known(value, expected):
    assert labels.source(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("bank", "银行转账"), ("wechat", "微信"), ("alipay", "支付宝"), ("cash", "现金"), ("other", "其他")],
)
def test_pay_method_maps_known(value, expected):
    assert labels.pay_method(value) == expected


def test_money_uses_currency_prefix_and_two_decimals():
    text = labels.money(Decimal("1234.5"))
    assert text.startswith("¥")
    assert text.endswith(".50")


def test_name_of_distinguishes_missing_from_deleted():
    clients = [WhClient(Id="c1", Name="甲方")]
    assert labels.name_of_client(clients, None) == "未填客户"
    assert labels.name_of_client(clients, "  ") == "未填客户"
    assert labels.name_of_client(clients, "c1") == "甲方"
    assert labels.name_of_client(clients, "c2") == "客户已删除"

    projects = [WhProject(Id="p1", Name="官网改造")]
    assert labels.name_of_project(projects, "") == "未挂项目"
    assert labels.name_of_project(projects, "p1") == "官网改造"
    assert labels.name_of_project(projects, "p2") == "项目已删除"


def test_name_of_treats_null_name_as_deleted():
    """C# 的 `?.Name ?? "客户已删除"` 把 null 和查不到合并成同一个兜底。"""
    clients = [WhClient(Id="c1", Name=None)]
    assert labels.name_of_client(clients, "c1") == "客户已删除"


def test_project_options_excludes_finished_projects():
    projects = [
        WhProject(Id="p1", Name="进行中", Status="active"),
        WhProject(Id="p2", Name="已完结", Status="done"),
        WhProject(Id="p3", Name="洽谈中", Status="talking"),
    ]
    options = labels.project_options(projects)
    assert len(options) == 2
    assert [o.value for o in options] == ["p1", "p3"]
    assert options[0].text == "进行中"


def test_client_options_excludes_archived_clients():
    clients = [
        WhClient(Id="c1", Name="在用", Archived=False),
        WhClient(Id="c2", Name="已归档", Archived=True),
    ]
    options = labels.client_options(clients)
    assert len(options) == 1
    assert options[0].value == "c1"
