"""发票、回款、支出、回款计划的 schema。

读模型里的 paid / due / isOverdue / tax 是服务端现算的派生字段——
C# 那边是在页面上算的，API 没有页面，就得由服务端给。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import BaseIn, BaseOut, EntityOut, Money

__all__ = [
    "InvoiceIn",
    "InvoiceOut",
    "InvoiceView",
    "PaymentIn",
    "PaymentOut",
    "ExpenseIn",
    "ExpenseOut",
    "PlanIn",
    "PlanOut",
    "PlanView",
    "PlanStatusRequest",
    "FinanceStats",
    "MonthStat",
]


class InvoiceIn(BaseIn):
    No: str | None = Field(default=None, max_length=50)
    ClientId: str = Field(..., max_length=36)
    ProjectId: str | None = Field(default=None, max_length=36)
    Type: str | None = Field(default="general", max_length=20)
    Amount: Money = Decimal("0")
    TaxRate: Money = Decimal("0")
    IssueDate: datetime | None = None
    ExpectDate: datetime | None = None
    Status: str | None = Field(default="opened", max_length=20)
    File: str | None = Field(default=None, max_length=300)
    Note: str | None = Field(default=None, max_length=500)


class InvoiceOut(EntityOut):
    No: str | None = None
    ClientId: str = ""
    ProjectId: str | None = None
    Type: str | None = None
    Amount: Money = Decimal("0")
    TaxRate: Money = Decimal("0")
    IssueDate: datetime | None = None
    ExpectDate: datetime | None = None
    Status: str | None = None
    File: str | None = None
    Note: str | None = None


class InvoiceView(InvoiceOut):
    """带派生字段的发票。"""

    Paid: Money = Decimal("0")
    Due: Money = Decimal("0")
    IsOverdue: bool = False
    Tax: Money = Decimal("0")
    ClientName: str = ""
    ProjectName: str = ""


class PaymentIn(BaseIn):
    InvoiceId: str = Field(..., max_length=36)
    ClientId: str | None = Field(default=None, max_length=36)
    Amount: Money = Decimal("0")
    PayDate: datetime | None = None
    Method: str | None = Field(default="bank", max_length=20)
    Note: str | None = Field(default=None, max_length=500)


class PaymentOut(EntityOut):
    InvoiceId: str = ""
    ClientId: str | None = None
    Amount: Money = Decimal("0")
    PayDate: datetime | None = None
    Method: str | None = None
    Note: str | None = None


class ExpenseIn(BaseIn):
    Category: str = Field(..., max_length=40)
    Amount: Money = Decimal("0")
    HappenDate: datetime | None = None
    ProjectId: str | None = Field(default=None, max_length=36)
    Note: str | None = Field(default=None, max_length=500)


class ExpenseOut(EntityOut):
    Category: str = ""
    Amount: Money = Decimal("0")
    HappenDate: datetime | None = None
    ProjectId: str | None = None
    Note: str | None = None


class PlanIn(BaseIn):
    ProjectId: str | None = Field(default=None, max_length=36)
    InvoiceId: str | None = Field(default=None, max_length=36)
    Title: str = Field(..., max_length=100)
    Seq: int = 1
    DueDate: datetime | None = None
    Amount: Money = Decimal("0")
    Status: str | None = Field(default="pending", max_length=20)
    PaidDate: datetime | None = None
    Note: str | None = Field(default=None, max_length=500)


class PlanOut(EntityOut):
    ProjectId: str | None = None
    InvoiceId: str | None = None
    Title: str = ""
    Seq: int = 1
    DueDate: datetime | None = None
    Amount: Money = Decimal("0")
    Status: str | None = None
    PaidDate: datetime | None = None
    Note: str | None = None


class PlanView(PlanOut):
    """带派生字段的期次。"""

    IsOverdue: bool = False
    PercentOf: int | None = None
    ProjectName: str = ""


class PlanStatusRequest(BaseIn):
    Status: str = Field(..., max_length=20)


class MonthStat(BaseOut):
    """一个月的收支。"""

    Month: str = ""
    Income: Money = Decimal("0")
    Expense: Money = Decimal("0")
    Net: Money = Decimal("0")


class FinanceStats(BaseOut):
    """收支统计（对应 C# 的 Stats.razor.cs）。"""

    From: datetime | None = None
    To: datetime | None = None
    InvoiceTotal: Money = Decimal("0")
    InvoicePaid: Money = Decimal("0")
    InvoiceDue: Money = Decimal("0")
    ExpenseTotal: Money = Decimal("0")
    Net: Money = Decimal("0")
    PlanDue: Money = Decimal("0")
    Months: list[MonthStat] = []
    OverdueInvoices: list[InvoiceView] = []
    OverduePlans: list[PlanView] = []
