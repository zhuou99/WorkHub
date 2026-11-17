"""财务口径：作废票、超额、逾期、计划口径与税额拆分。

移植自 WorkHub.Tests/FinanceCalcTests.cs。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.common.finance_calc import due, is_invoice_overdue, is_plan_overdue, paid, percent_of, plan_due, tax_of
from app.models.finance import WhInvoice, WhPayment, WhPaymentPlan

TODAY = datetime(2026, 11, 6)


def invoice(status="opened", amount=Decimal("1000"), expect=None, tax_rate=Decimal("0")):
    return WhInvoice(
        Id="inv-1",
        Status=status,
        Amount=Decimal(amount),
        ExpectDate=expect,
        TaxRate=Decimal(tax_rate),
    )


def payment(invoice_id, amount):
    return WhPayment(Id=f"pay-{invoice_id}-{amount}", InvoiceId=invoice_id, Amount=Decimal(amount))


def test_paid_sums_payments_of_invoice_only():
    inv = invoice()
    payments = [payment("inv-1", 400), payment("inv-1", 300), payment("inv-2", 500)]
    assert paid(inv, payments) == Decimal(700)


def test_paid_void_invoice_is_zero():
    assert paid(invoice("void"), [payment("inv-1", 400)]) == Decimal(0)


def test_due_is_amount_minus_paid_and_never_negative():
    inv = invoice()
    assert due(inv, [payment("inv-1", 700)]) == Decimal(300)
    assert due(inv, [payment("inv-1", 1500)]) == Decimal(0)
    assert due(invoice("void"), [payment("inv-1", 0)]) == Decimal(0)


def test_is_overdue_only_past_expect_date_with_remainder():
    past = TODAY - timedelta(days=1)
    future = TODAY + timedelta(days=1)

    assert is_invoice_overdue(invoice("opened", Decimal("1000"), past), [], TODAY) is True
    assert is_invoice_overdue(invoice("opened", Decimal("1000"), future), [], TODAY) is False
    assert is_invoice_overdue(invoice("opened", Decimal("1000"), None), [], TODAY) is False
    assert is_invoice_overdue(invoice("paid", Decimal("1000"), past), [], TODAY) is False
    assert is_invoice_overdue(invoice("void", Decimal("1000"), past), [], TODAY) is False
    assert is_invoice_overdue(invoice("opened", Decimal("1000"), past), [payment("inv-1", 1000)], TODAY) is False


def test_plan_due_counts_pending_only():
    plans = [
        WhPaymentPlan(Id="p1", Amount=Decimal(100), Status="pending"),
        WhPaymentPlan(Id="p2", Amount=Decimal(200), Status="pending"),
        WhPaymentPlan(Id="p3", Amount=Decimal(300), Status="paid"),
        WhPaymentPlan(Id="p4", Amount=Decimal(50), Status="skipped"),
    ]
    assert plan_due(plans) == Decimal(300)


def test_plan_is_overdue_only_pending_past_due_date():
    past = TODAY - timedelta(days=1)
    assert is_plan_overdue(WhPaymentPlan(DueDate=past, Status="pending"), TODAY) is True
    assert is_plan_overdue(WhPaymentPlan(DueDate=past, Status="skipped"), TODAY) is False
    assert is_plan_overdue(WhPaymentPlan(DueDate=TODAY, Status="pending"), TODAY) is False
    assert is_plan_overdue(WhPaymentPlan(DueDate=None, Status="pending"), TODAY) is False


def test_percent_of_returns_null_when_contract_or_amount_missing():
    assert percent_of(WhPaymentPlan(Amount=Decimal(300)), Decimal(1000)) == 30
    assert percent_of(WhPaymentPlan(Amount=Decimal("333.33")), Decimal(1000)) == 33
    assert percent_of(WhPaymentPlan(Amount=Decimal(300)), Decimal(0)) is None
    assert percent_of(WhPaymentPlan(Amount=Decimal(0)), Decimal(1000)) is None


def test_tax_of_splits_tax_from_gross():
    assert tax_of(invoice(tax_rate=0)) == Decimal(0)
    assert tax_of(invoice(amount=Decimal(1000), tax_rate=6)) == Decimal("56.60")
    assert tax_of(invoice(amount=Decimal(1060), tax_rate=6)) == Decimal(60)


def test_tax_of_uses_bankers_rounding():
    """Math.Round(decimal) 是银行家舍入：2.125 → 2.12，不是 2.13。"""
    # 不含税金额恰好是 2.125（= 2.2525 / 1.06），中点落在两位小数的第三位。
    assert tax_of(invoice(amount=Decimal("2.2525"), tax_rate=6)) == Decimal("0.1325")
