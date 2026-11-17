"""发票、回款、支出、分期回款计划四张台账。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin
from app.models.types import DecimalAsFloat, TextDateTime


class WhInvoice(EntityBaseMixin, Base):
    """已收金额由 WhPayment 汇总得出，逾期按约定回款日动态判定。"""

    __tablename__ = "wh_invoice"

    No: Mapped[str | None] = mapped_column("No", Text, nullable=True)
    ClientId: Mapped[str] = mapped_column("ClientId", Text, nullable=False)
    ProjectId: Mapped[str | None] = mapped_column("ProjectId", Text, nullable=True)
    Type: Mapped[str | None] = mapped_column("Type", Text, nullable=True, default="general")
    Amount: Mapped[Decimal] = mapped_column("Amount", DecimalAsFloat(), nullable=False, default=Decimal("0"))
    TaxRate: Mapped[Decimal] = mapped_column("TaxRate", DecimalAsFloat(), nullable=False, default=Decimal("0"))
    IssueDate: Mapped[datetime | None] = mapped_column("IssueDate", TextDateTime(), nullable=True)
    ExpectDate: Mapped[datetime | None] = mapped_column("ExpectDate", TextDateTime(), nullable=True)
    Status: Mapped[str | None] = mapped_column("Status", Text, nullable=True, default="opened")
    File: Mapped[str | None] = mapped_column("File", Text, nullable=True)
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)


class WhPayment(EntityBaseMixin, Base):
    """回款登记：一笔实际到账，可分期多次；挂在发票上便于逐票核对。"""

    __tablename__ = "wh_payment"

    InvoiceId: Mapped[str] = mapped_column("InvoiceId", Text, nullable=False)
    ClientId: Mapped[str | None] = mapped_column("ClientId", Text, nullable=True)
    Amount: Mapped[Decimal] = mapped_column("Amount", DecimalAsFloat(), nullable=False, default=Decimal("0"))
    PayDate: Mapped[datetime] = mapped_column("PayDate", TextDateTime(), nullable=False)
    Method: Mapped[str | None] = mapped_column("Method", Text, nullable=True, default="bank")
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)


class WhExpense(EntityBaseMixin, Base):
    """支出流水：给收支统计补上成本一侧，可选挂到项目。"""

    __tablename__ = "wh_expense"

    Category: Mapped[str] = mapped_column("Category", Text, nullable=False)
    Amount: Mapped[Decimal] = mapped_column("Amount", DecimalAsFloat(), nullable=False, default=Decimal("0"))
    HappenDate: Mapped[datetime] = mapped_column("HappenDate", TextDateTime(), nullable=False)
    ProjectId: Mapped[str | None] = mapped_column("ProjectId", Text, nullable=True)
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)


class WhPaymentPlan(EntityBaseMixin, Base):
    """分期回款计划：把合同额拆成「首款 30% → 验收 40% → 尾款 30%」这样的期次。"""

    __tablename__ = "wh_payment_plan"

    ProjectId: Mapped[str | None] = mapped_column("ProjectId", Text, nullable=True)
    InvoiceId: Mapped[str | None] = mapped_column("InvoiceId", Text, nullable=True)
    Title: Mapped[str] = mapped_column("Title", Text, nullable=False)
    Seq: Mapped[int] = mapped_column("Seq", Integer, nullable=False, default=1)
    DueDate: Mapped[datetime | None] = mapped_column("DueDate", TextDateTime(), nullable=True)
    Amount: Mapped[Decimal] = mapped_column("Amount", DecimalAsFloat(), nullable=False, default=Decimal("0"))
    Status: Mapped[str | None] = mapped_column("Status", Text, nullable=True, default="pending")
    PaidDate: Mapped[datetime | None] = mapped_column("PaidDate", TextDateTime(), nullable=True)
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)
