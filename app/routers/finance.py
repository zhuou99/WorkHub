"""财务路由：发票、回款、支出、回款计划、收支统计。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.result import Result
from app.deps import get_db, require_user, require_write
from app.models.crm import WhClient, WhProject
from app.schemas.auth import UserInfo
from app.schemas.finance import (
    ExpenseIn,
    ExpenseOut,
    FinanceStats,
    InvoiceIn,
    InvoiceView,
    PaymentIn,
    PaymentOut,
    PlanIn,
    PlanStatusRequest,
    PlanView,
)
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/api/finance", tags=["财务"])


def _service(db: Session = Depends(get_db)) -> FinanceService:
    return FinanceService(db)


def _payment_out(payment) -> PaymentOut:
    return PaymentOut(
        Id=payment.Id,
        CreateBy=payment.CreateBy or "",
        CreateTime=payment.CreateTime,
        ModifyBy=payment.ModifyBy,
        ModifyTime=payment.ModifyTime,
        Version=payment.Version or 1,
        InvoiceId=payment.InvoiceId or "",
        ClientId=payment.ClientId,
        Amount=payment.Amount or Decimal(0),
        PayDate=payment.PayDate,
        Method=payment.Method,
        Note=payment.Note,
    )


def _expense_out(expense) -> ExpenseOut:
    return ExpenseOut(
        Id=expense.Id,
        CreateBy=expense.CreateBy or "",
        CreateTime=expense.CreateTime,
        ModifyBy=expense.ModifyBy,
        ModifyTime=expense.ModifyTime,
        Version=expense.Version or 1,
        Category=expense.Category or "",
        Amount=expense.Amount or Decimal(0),
        HappenDate=expense.HappenDate,
        ProjectId=expense.ProjectId,
        Note=expense.Note,
    )


# ---------- 发票 ----------


@router.get("/invoices", response_model=Result[list[InvoiceView]], summary="发票台账")
def list_invoices(service: FinanceService = Depends(_service), _: UserInfo = Depends(require_user)):
    from sqlalchemy import select

    payments = service.all_payments()
    clients = list(service._session.execute(select(WhClient)).scalars().all())
    projects = list(service._session.execute(select(WhProject)).scalars().all())
    return Result(data=[service.invoice_view(item, payments, clients, projects) for item in service.all_invoices()])


@router.post("/invoices", response_model=Result[InvoiceView], summary="新增或修改发票")
def save_invoice(
    payload: InvoiceIn,
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    from sqlalchemy import select

    invoice = service.save_invoice(payload)
    payments = service.all_payments()
    clients = list(service._session.execute(select(WhClient)).scalars().all())
    projects = list(service._session.execute(select(WhProject)).scalars().all())
    return Result(data=service.invoice_view(invoice, payments, clients, projects), message="已保存。")


@router.delete("/invoices/{invoice_id}", response_model=Result[None], summary="删除发票")
def delete_invoice(
    invoice_id: str,
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    service.delete_invoice(invoice_id)
    return Result(message="已删除。")


# ---------- 回款 ----------


@router.get("/payments", response_model=Result[list[PaymentOut]], summary="回款流水")
def list_payments(service: FinanceService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_payment_out(item) for item in service.all_payments()])


@router.post("/payments", response_model=Result[PaymentOut], summary="新增或修改回款")
def save_payment(
    payload: PaymentIn,
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=_payment_out(service.save_payment(payload)), message="已保存。")


@router.delete("/payments/{payment_id}", response_model=Result[None], summary="删除回款")
def delete_payment(
    payment_id: str,
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    service.delete_payment(payment_id)
    return Result(message="已删除。")


# ---------- 支出 ----------


@router.get("/expenses", response_model=Result[list[ExpenseOut]], summary="支出流水")
def list_expenses(service: FinanceService = Depends(_service), _: UserInfo = Depends(require_user)):
    return Result(data=[_expense_out(item) for item in service.all_expenses()])


@router.post("/expenses", response_model=Result[ExpenseOut], summary="新增或修改支出")
def save_expense(
    payload: ExpenseIn,
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    return Result(data=_expense_out(service.save_expense(payload)), message="已保存。")


@router.delete("/expenses/{expense_id}", response_model=Result[None], summary="删除支出")
def delete_expense(
    expense_id: str,
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    service.delete_expense(expense_id)
    return Result(message="已删除。")


# ---------- 回款计划 ----------


@router.get("/plans", response_model=Result[list[PlanView]], summary="回款计划")
def list_plans(service: FinanceService = Depends(_service), _: UserInfo = Depends(require_user)):
    from sqlalchemy import select

    projects = list(service._session.execute(select(WhProject)).scalars().all())
    return Result(data=[service.plan_view(item, projects) for item in service.all_plans()])


@router.post("/plans", response_model=Result[PlanView], summary="新增或修改期次")
def save_plan(payload: PlanIn, service: FinanceService = Depends(_service), _: UserInfo = Depends(require_write)):
    from sqlalchemy import select

    plan = service.save_plan(payload)
    projects = list(service._session.execute(select(WhProject)).scalars().all())
    return Result(data=service.plan_view(plan, projects), message="已保存。")


@router.post("/plans/{plan_id}/status", response_model=Result[PlanView], summary="改期次状态")
def set_plan_status(
    plan_id: str,
    payload: PlanStatusRequest,
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_write),
):
    from fastapi import HTTPException
    from sqlalchemy import select

    plan = service.set_plan_status(plan_id, payload.Status)
    if plan is None:
        raise HTTPException(status_code=404, detail="这一期已经不在了。")
    projects = list(service._session.execute(select(WhProject)).scalars().all())
    return Result(data=service.plan_view(plan, projects), message="已更新。")


@router.delete("/plans/{plan_id}", response_model=Result[None], summary="删除期次")
def delete_plan(plan_id: str, service: FinanceService = Depends(_service), _: UserInfo = Depends(require_write)):
    service.delete_plan(plan_id)
    return Result(message="已删除。")


# ---------- 统计 ----------


@router.get("/stats", response_model=Result[FinanceStats], summary="收支统计")
def stats(
    start: datetime | None = Query(None, alias="from"),
    end: datetime | None = Query(None, alias="to"),
    service: FinanceService = Depends(_service),
    _: UserInfo = Depends(require_user),
):
    return Result(data=service.stats(start, end))
