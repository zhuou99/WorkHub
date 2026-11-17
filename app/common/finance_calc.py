"""财务口径：发票已收 / 待收 / 逾期 / 税额，以及回款计划的待收与占比。

对应 C# 的 WorkHub/Common/FinanceCalc.cs（原为扩展方法，这里改成普通函数）。

两条硬规矩：
1. 一律用 decimal.Decimal，绝不混 float。.NET 的 decimal 最多 28~29 位有效数字，
   Python 的 float 是二进制双精度，56.6 * 3 会变成 169.79999999999997。
2. 舍入用银行家舍入（ROUND_HALF_EVEN），与 .NET 的 Math.Round(decimal) 默认行为一致。
   Math.Round(12.5m) == 12，不是 13。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal

__all__ = [
    "to_decimal",
    "paid",
    "due",
    "is_invoice_overdue",
    "tax_of",
    "plan_due",
    "is_plan_overdue",
    "percent_of",
    "month_key",
]


def to_decimal(value) -> Decimal:
    """把 float / int / str 收敛成 Decimal。float 走 str() 取最短往返表示，
    避免 Decimal(0.1) 变成 0.1000000000000000055511151231257827。"""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal(0)
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value))


def _round(value: Decimal, digits: int) -> Decimal:
    """Math.Round(decimal, digits)：银行家舍入。"""
    quantum = Decimal(1).scaleb(-digits)
    return value.quantize(quantum, rounding=ROUND_HALF_EVEN)


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def paid(invoice, payments: Iterable) -> Decimal:
    """已收金额：这张发票名下的回款合计。作废票一律算 0。"""
    if invoice.Status == "void":
        return Decimal(0)
    total = Decimal(0)
    for payment in payments:
        if payment.InvoiceId == invoice.Id:
            total += to_decimal(payment.Amount)
    return total


def due(invoice, payments: Iterable) -> Decimal:
    """待收金额：合同额减已收，不出现负数。作废票一律算 0。"""
    if invoice.Status == "void":
        return Decimal(0)
    remaining = to_decimal(invoice.Amount) - paid(invoice, payments)
    return remaining if remaining > 0 else Decimal(0)


def is_invoice_overdue(invoice, payments: Iterable, today) -> bool:
    """是否逾期：作废 / 已回款不算；没填回款期限不算；期限早于今天且还有欠款才算。"""
    if invoice.Status in ("void", "paid"):
        return False
    expect = _as_date(invoice.ExpectDate)
    if expect is None:
        return False
    current = _as_date(today)
    return expect < current and due(invoice, payments) > 0


def tax_of(invoice) -> Decimal:
    """税额：价税合计 - 不含税金额，保留两位（银行家舍入）。"""
    rate = to_decimal(invoice.TaxRate)
    if rate <= 0:
        return Decimal(0)
    amount = to_decimal(invoice.Amount)
    net = _round(amount / (Decimal(1) + rate / Decimal(100)), 2)
    return amount - net


def plan_due(plans: Iterable) -> Decimal:
    """待收期次合计：只算状态为 pending 的期次。"""
    total = Decimal(0)
    for plan in plans:
        if plan.Status == "pending":
            total += to_decimal(plan.Amount)
    return total


def is_plan_overdue(plan, today) -> bool:
    """期次是否逾期：只看待收期次，且应收日早于今天。"""
    if plan.Status != "pending":
        return False
    due_date = _as_date(plan.DueDate)
    if due_date is None:
        return False
    return due_date < _as_date(today)


def percent_of(plan, contract_amount) -> int | None:
    """期次占合同额的几成（整数百分比）。合同额或期次金额非正时没有意义，返回 None。"""
    contract = to_decimal(contract_amount)
    amount = to_decimal(plan.Amount)
    if contract <= 0 or amount <= 0:
        return None
    # C# 的表达式是 (Amount / contractAmount) * 100，先除后乘，顺序不能换。
    ratio = _round(amount / contract * Decimal(100), 0)
    return int(ratio)


def month_key(value) -> str:
    """月份键：yyyy-MM。"""
    if isinstance(value, datetime):
        return f"{value.year:04d}-{value.month:02d}"
    if isinstance(value, date):
        return f"{value.year:04d}-{value.month:02d}"
    text = str(value)
    return text[:7] if len(text) >= 7 else text


def sum_amounts(items: Sequence) -> Decimal:
    """一组金额求和（Decimal 口径）。"""
    total = Decimal(0)
    for item in items:
        total += to_decimal(item)
    return total
