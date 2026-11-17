"""状态字典：中文口径只写一处，多个页面共用。

对应 C# 的 WorkHub/Common/Labels.cs。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

__all__ = [
    "SelectOption",
    "money",
    "project_status",
    "invoice_status",
    "invoice_type",
    "plan_status",
    "task_status",
    "priority",
    "comm_type",
    "source",
    "pay_method",
    "article_status",
    "PROJECT_STATUSES",
    "INVOICE_STATUSES",
    "INVOICE_TYPES",
    "PLAN_STATUSES",
    "PRIORITIES",
    "PAY_METHODS",
    "project_options",
    "client_options",
    "name_of_client",
    "name_of_project",
]


@dataclass(frozen=True)
class SelectOption:
    """下拉项：Value 是存库的值，Text 是给人看的文案。"""

    value: str
    text: str


def money(value) -> str:
    """¥1,234.50。千分位用不分组随环境变化的固定写法，与 .NET 的 N2 对齐。"""
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return f"¥{amount:,.2f}"


def project_status(s: str | None) -> str:
    return {"active": "进行中", "accept": "验收中", "maintain": "维护期", "done": "已完结"}.get(s, "洽谈中")


def invoice_status(s: str | None) -> str:
    return {"sent": "已寄出", "paid": "已回款", "void": "作废"}.get(s, "已开票")


def invoice_type(s: str | None) -> str:
    return {"special": "专票", "agent": "个人代开"}.get(s, "普票")


def plan_status(s: str | None) -> str:
    return {"paid": "已到账", "skipped": "已免除"}.get(s, "待收")


def task_status(s: str | None) -> str:
    return {"doing": "进行中", "done": "已完成", "hold": "搁置"}.get(s, "待办")


def priority(s: str | None) -> str:
    return {"high": "急", "low": "不急"}.get(s, "普通")


def comm_type(s: str | None) -> str:
    return {"phone": "电话", "meet": "见面", "mail": "邮件", "other": "其他"}.get(s, "微信")


def source(s: str | None) -> str:
    return {"friend": "朋友介绍", "referral": "老客户转介", "platform": "平台接单", "other": "其他"}.get(s, "未知")


def pay_method(s: str | None) -> str:
    return {"wechat": "微信", "alipay": "支付宝", "cash": "现金", "other": "其他"}.get(s, "银行转账")


def article_status(s: str | None) -> str:
    return {"layout": "排版中", "done": "已发布", "failed": "已失败"}.get(s, "草稿")


PROJECT_STATUSES: tuple[SelectOption, ...] = (
    SelectOption("talking", "洽谈中"),
    SelectOption("active", "进行中"),
    SelectOption("accept", "验收中"),
    SelectOption("maintain", "维护期"),
    SelectOption("done", "已完结"),
)

INVOICE_STATUSES: tuple[SelectOption, ...] = (
    SelectOption("opened", "已开票"),
    SelectOption("sent", "已寄出"),
    SelectOption("paid", "已回款"),
    SelectOption("void", "作废"),
)

INVOICE_TYPES: tuple[SelectOption, ...] = (
    SelectOption("general", "普票"),
    SelectOption("special", "专票"),
    SelectOption("agent", "个人代开"),
)

PLAN_STATUSES: tuple[SelectOption, ...] = (
    SelectOption("pending", "待收"),
    SelectOption("paid", "已到账"),
    SelectOption("skipped", "已免除"),
)

PRIORITIES: tuple[SelectOption, ...] = (
    SelectOption("high", "急"),
    SelectOption("normal", "普通"),
    SelectOption("low", "不急"),
)

PAY_METHODS: tuple[SelectOption, ...] = (
    SelectOption("bank", "银行转账"),
    SelectOption("wechat", "微信"),
    SelectOption("alipay", "支付宝"),
    SelectOption("cash", "现金"),
    SelectOption("other", "其他"),
)


def project_options(projects: Iterable) -> list[SelectOption]:
    """下拉用的「空闲项目」：完结的不再出现在新选项里。"""
    return [SelectOption(p.Id, p.Name) for p in projects if p.Status != "done"]


def client_options(clients: Iterable) -> list[SelectOption]:
    """下拉用的客户：归档的不出现。"""
    return [SelectOption(c.Id, c.Name) for c in clients if not c.Archived]


def name_of_client(clients: Iterable, id_: str | None) -> str:
    """客户列的显示口径：没填 与 填了但对方已删 是两件事。

    注意：命中行但 Name 为空/None 时也要落到「客户已删除」——
    C# 的 `?.Name ?? "客户已删除"` 把 null 和查不到合并成同一个兜底。
    """
    if id_ is None or not id_.strip():
        return "未填客户"
    for client in clients:
        if client.Id == id_:
            name = client.Name
            return name if name is not None else "客户已删除"
    return "客户已删除"


def name_of_project(projects: Iterable, id_: str | None) -> str:
    """项目列的显示口径，语义同 :func:`name_of_client`。"""
    if id_ is None or not id_.strip():
        return "未挂项目"
    for project in projects:
        if project.Id == id_:
            name = project.Name
            return name if name is not None else "项目已删除"
    return "项目已删除"


def options_to_dicts(options: Sequence[SelectOption]) -> list[dict]:
    """给 /api/meta/labels 用的可序列化形式。"""
    return [{"value": o.value, "text": o.text} for o in options]
