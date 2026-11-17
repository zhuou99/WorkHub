"""发票 / 回款 / 支出 / 回款计划四本台账。

对应 C# 的 WorkHub/Services/FinanceService.cs。
统计口径由 app/common/finance_calc.py 现算，不在服务里存派生字段。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.finance_calc import (
    due,
    is_invoice_overdue,
    is_plan_overdue,
    paid,
    percent_of,
    plan_due,
    tax_of,
)
from app.common.labels import name_of_client, name_of_project
from app.models.crm import WhClient, WhProject
from app.models.finance import WhExpense, WhInvoice, WhPayment, WhPaymentPlan
from app.schemas.finance import ExpenseIn, InvoiceIn, PaymentIn, PlanIn
from app.services.crud import LOCAL, delete_where, now, unbind, upsert

__all__ = ["FinanceService"]

INVOICE_FIELDS = (
    "No", "ClientId", "ProjectId", "Type", "Amount", "TaxRate", "IssueDate", "ExpectDate",
    "Status", "File", "Note",
)
PAYMENT_FIELDS = ("InvoiceId", "ClientId", "Amount", "PayDate", "Method", "Note")
EXPENSE_FIELDS = ("Category", "Amount", "HappenDate", "ProjectId", "Note")
PLAN_FIELDS = ("ProjectId", "InvoiceId", "Title", "Seq", "DueDate", "Amount", "Status", "PaidDate", "Note")


class FinanceService:
    def __init__(self, session: Session):
        self._session = session

    # ---------- 发票 ----------

    def all_invoices(self) -> list[WhInvoice]:
        rows = list(self._session.execute(select(WhInvoice)).scalars().all())
        return sorted(rows, key=lambda item: item.IssueDate or item.CreateTime, reverse=True)

    def save_invoice(self, invoice: InvoiceIn, invoice_id: str | None = None) -> WhInvoice:
        entity = WhInvoice(Id=invoice_id or "")
        for name in INVOICE_FIELDS:
            setattr(entity, name, getattr(invoice, name))
        return upsert(self._session, entity, INVOICE_FIELDS)

    def delete_invoice(self, invoice_id: str) -> None:
        """删发票连带清掉它的回款记录。"""
        delete_where(self._session, WhPayment, WhPayment.InvoiceId == invoice_id)
        # 挂在这张票上的期次计划保留，只是解掉发票引用，否则计划页会出现指向空票的行
        unbind(self._session, WhPaymentPlan, WhPaymentPlan.InvoiceId == invoice_id, "InvoiceId")
        entity = self._session.get(WhInvoice, invoice_id)
        if entity is not None:
            self._session.delete(entity)
            self._session.commit()

    # ---------- 回款 ----------

    def all_payments(self) -> list[WhPayment]:
        rows = list(self._session.execute(select(WhPayment)).scalars().all())
        return sorted(rows, key=lambda item: item.PayDate or item.CreateTime, reverse=True)

    def save_payment(self, payment: PaymentIn, payment_id: str | None = None) -> WhPayment:
        entity = WhPayment(Id=payment_id or "")
        for name in PAYMENT_FIELDS:
            setattr(entity, name, getattr(payment, name))
        if entity.PayDate is None:
            entity.PayDate = now()
        return upsert(self._session, entity, PAYMENT_FIELDS)

    def delete_payment(self, payment_id: str) -> None:
        entity = self._session.get(WhPayment, payment_id)
        if entity is not None:
            self._session.delete(entity)
            self._session.commit()

    # ---------- 支出 ----------

    def all_expenses(self) -> list[WhExpense]:
        rows = list(self._session.execute(select(WhExpense)).scalars().all())
        return sorted(rows, key=lambda item: item.HappenDate or item.CreateTime, reverse=True)

    def save_expense(self, expense: ExpenseIn, expense_id: str | None = None) -> WhExpense:
        entity = WhExpense(Id=expense_id or "")
        for name in EXPENSE_FIELDS:
            setattr(entity, name, getattr(expense, name))
        if entity.HappenDate is None:
            entity.HappenDate = now().replace(hour=0, minute=0, second=0, microsecond=0)
        return upsert(self._session, entity, EXPENSE_FIELDS)

    def delete_expense(self, expense_id: str) -> None:
        entity = self._session.get(WhExpense, expense_id)
        if entity is not None:
            self._session.delete(entity)
            self._session.commit()

    # ---------- 回款计划 ----------

    def all_plans(self) -> list[WhPaymentPlan]:
        """该收的排前面、按应收日就近；收满与减免的沉底，打开页面先看到要办的。"""
        rows = list(self._session.execute(select(WhPaymentPlan)).scalars().all())
        return sorted(
            rows,
            key=lambda item: (
                item.Status != "pending",
                item.DueDate or now().replace(hour=0, minute=0, second=0, microsecond=0),
                item.ProjectId or "",
                item.Seq,
            ),
        )

    def save_plan(self, plan: PlanIn, plan_id: str | None = None) -> WhPaymentPlan:
        entity = WhPaymentPlan(Id=plan_id or "")
        for name in PLAN_FIELDS:
            setattr(entity, name, getattr(plan, name))
        return upsert(self._session, entity, PLAN_FIELDS)

    def delete_plan(self, plan_id: str) -> None:
        entity = self._session.get(WhPaymentPlan, plan_id)
        if entity is not None:
            self._session.delete(entity)
            self._session.commit()

    def set_plan_status(self, plan_id: str, status: str) -> WhPaymentPlan | None:
        """改一期计划的状态：标 paid 时记下实收日期。

        不自动生成回款记录——到账金额以发票台账为准，这边只负责「哪一期该收、收没收到」。
        """
        plan = self._session.get(WhPaymentPlan, plan_id)
        if plan is None:
            return None
        plan.Status = status
        # 收回来啦就盖个实收日期；改回待收或作废则要清掉，别留个上次的日期骗人
        plan.PaidDate = now().replace(hour=0, minute=0, second=0, microsecond=0) if status == "paid" else None
        plan.ModifyBy = LOCAL
        plan.ModifyTime = now()
        self._session.add(plan)
        self._session.commit()
        return plan

    # ---------- 派生数据 ----------

    def invoice_view(self, invoice: WhInvoice, payments: list[WhPayment], clients: list[WhClient], projects: list[WhProject]):
        """发票 + 派生字段（已收 / 待收 / 逾期 / 税额 / 客户名 / 项目名）。"""
        from app.schemas.finance import InvoiceView

        today = now()
        return InvoiceView(
            Id=invoice.Id,
            CreateBy=invoice.CreateBy or "",
            CreateTime=invoice.CreateTime,
            ModifyBy=invoice.ModifyBy,
            ModifyTime=invoice.ModifyTime,
            Version=invoice.Version or 1,
            No=invoice.No,
            ClientId=invoice.ClientId or "",
            ProjectId=invoice.ProjectId,
            Type=invoice.Type,
            Amount=invoice.Amount or Decimal(0),
            TaxRate=invoice.TaxRate or Decimal(0),
            IssueDate=invoice.IssueDate,
            ExpectDate=invoice.ExpectDate,
            Status=invoice.Status,
            File=invoice.File,
            Note=invoice.Note,
            Paid=paid(invoice, payments),
            Due=due(invoice, payments),
            IsOverdue=is_invoice_overdue(invoice, payments, today),
            Tax=tax_of(invoice),
            ClientName=name_of_client(clients, invoice.ClientId),
            ProjectName=name_of_project(projects, invoice.ProjectId),
        )

    def plan_view(self, plan: WhPaymentPlan, projects: list[WhProject]):
        """期次 + 派生字段（逾期 / 占合同额几成 / 项目名）。"""
        from app.schemas.finance import PlanView

        contract = Decimal(0)
        if plan.ProjectId:
            project = next((item for item in projects if item.Id == plan.ProjectId), None)
            contract = (project.Amount if project else Decimal(0)) or Decimal(0)
        return PlanView(
            Id=plan.Id,
            CreateBy=plan.CreateBy or "",
            CreateTime=plan.CreateTime,
            ModifyBy=plan.ModifyBy,
            ModifyTime=plan.ModifyTime,
            Version=plan.Version or 1,
            ProjectId=plan.ProjectId,
            InvoiceId=plan.InvoiceId,
            Title=plan.Title or "",
            Seq=plan.Seq or 1,
            DueDate=plan.DueDate,
            Amount=plan.Amount or Decimal(0),
            Status=plan.Status,
            PaidDate=plan.PaidDate,
            Note=plan.Note,
            IsOverdue=is_plan_overdue(plan, now()),
            PercentOf=percent_of(plan, contract),
            ProjectName=name_of_project(projects, plan.ProjectId),
        )

    def stats(self, start=None, end=None) -> dict:
        """收支统计（对应 C# 的 Stats.razor.cs）。"""
        from collections import defaultdict

        from app.common.finance_calc import month_key
        from app.schemas.finance import FinanceStats, MonthStat

        invoices = self.all_invoices()
        payments = self.all_payments()
        expenses = self.all_expenses()
        plans = self.all_plans()
        clients = list(self._session.execute(select(WhClient)).scalars().all())
        projects = list(self._session.execute(select(WhProject)).scalars().all())

        buckets: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"income": Decimal(0), "expense": Decimal(0)})
        for payment in payments:
            moment = payment.PayDate or payment.CreateTime
            if moment is None or not _in_range(moment, start, end):
                continue
            buckets[month_key(moment)]["income"] += payment.Amount or Decimal(0)
        for expense in expenses:
            moment = expense.HappenDate or expense.CreateTime
            if moment is None or not _in_range(moment, start, end):
                continue
            buckets[month_key(moment)]["expense"] += expense.Amount or Decimal(0)

        months = [
            MonthStat(
                Month=key,
                Income=value["income"],
                Expense=value["expense"],
                Net=value["income"] - value["expense"],
            )
            for key, value in sorted(buckets.items())
        ]

        invoice_views = [self.invoice_view(item, payments, clients, projects) for item in invoices]
        plan_views = [self.plan_view(item, projects) for item in plans]

        return FinanceStats(
            From=start,
            To=end,
            InvoiceTotal=sum((item.Amount or Decimal(0)) for item in invoices if item.Status != "void"),
            InvoicePaid=sum((view.Paid for view in invoice_views), Decimal(0)),
            InvoiceDue=sum((view.Due for view in invoice_views), Decimal(0)),
            ExpenseTotal=sum((item.Amount or Decimal(0)) for item in expenses),
            Net=sum((item.Amount or Decimal(0)) for item in payments) - sum((item.Amount or Decimal(0)) for item in expenses),
            PlanDue=plan_due(plans),
            Months=months,
            OverdueInvoices=[view for view in invoice_views if view.IsOverdue],
            OverduePlans=[view for view in plan_views if view.IsOverdue],
        )


def _in_range(moment, start, end) -> bool:
    if start is not None and moment < start:
        return False
    if end is not None and moment > end:
        return False
    return True
