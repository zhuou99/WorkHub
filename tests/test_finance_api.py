"""财务接口：四本台账、派生口径、删除发票的连带处理。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.finance import WhInvoice, WhPayment, WhPaymentPlan


def _invoice(client, **extra) -> dict:
    payload = {"clientId": "c1", "amount": 1000, "taxRate": 6, **extra}
    response = client.post("/api/finance/invoices", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_invoice_tax_is_split(auth_client):
    invoice = _invoice(auth_client, amount=1000, taxRate=6)
    assert invoice["tax"] == 56.6
    assert invoice["paid"] == 0
    assert invoice["due"] == 1000
    assert invoice["isOverdue"] is False


def test_invoice_without_tax_rate(auth_client):
    invoice = _invoice(auth_client, amount=1060, taxRate=0)
    assert invoice["tax"] == 0


def test_payment_reduces_due(auth_client):
    invoice = _invoice(auth_client)
    auth_client.post("/api/finance/payments", json={"invoiceId": invoice["id"], "amount": 400})
    rows = auth_client.get("/api/finance/invoices").json()["data"]
    assert rows[0]["paid"] == 400
    assert rows[0]["due"] == 600


def test_overdue_invoice(auth_client):
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    invoice = _invoice(auth_client, expectDate=yesterday)
    assert invoice["isOverdue"] is True


def test_paid_invoice_is_not_overdue(auth_client):
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    invoice = _invoice(auth_client, expectDate=yesterday)
    auth_client.post("/api/finance/payments", json={"invoiceId": invoice["id"], "amount": 1000})
    rows = auth_client.get("/api/finance/invoices").json()["data"]
    assert rows[0]["isOverdue"] is False
    assert rows[0]["due"] == 0


def test_invoice_delete_removes_payments_but_keeps_plans(auth_client, app):
    invoice = _invoice(auth_client)
    payment = auth_client.post("/api/finance/payments", json={"invoiceId": invoice["id"], "amount": 100}).json()["data"]
    plan = auth_client.post(
        "/api/finance/plans", json={"invoiceId": invoice["id"], "title": "首款", "amount": 500}
    ).json()["data"]

    assert auth_client.delete(f"/api/finance/invoices/{invoice['id']}").status_code == 200

    with app.state.sessionmaker() as session:
        assert session.execute(select(WhPayment).where(WhPayment.Id == payment["id"])).scalars().all() == []
        assert session.execute(select(WhInvoice).where(WhInvoice.Id == invoice["id"])).scalars().all() == []
        kept_plan = session.execute(select(WhPaymentPlan).where(WhPaymentPlan.Id == plan["id"])).scalars().first()
        assert kept_plan is not None and kept_plan.InvoiceId == ""


def test_plan_status_paid_sets_paid_date(auth_client):
    plan = auth_client.post("/api/finance/plans", json={"title": "首款", "amount": 500}).json()["data"]
    assert plan["status"] == "pending"
    assert plan["paidDate"] is None

    response = auth_client.post(f"/api/finance/plans/{plan['id']}/status", json={"status": "paid"})
    assert response.status_code == 200
    assert response.json()["data"]["paidDate"] is not None


def test_plan_status_back_to_pending_clears_paid_date(auth_client):
    plan = auth_client.post("/api/finance/plans", json={"title": "首款", "amount": 500}).json()["data"]
    auth_client.post(f"/api/finance/plans/{plan['id']}/status", json={"status": "paid"})
    response = auth_client.post(f"/api/finance/plans/{plan['id']}/status", json={"status": "pending"})
    assert response.json()["data"]["paidDate"] is None


def test_plan_percent_of_contract(auth_client):
    project = auth_client.post("/api/projects", json={"name": "官网改造", "amount": 10000}).json()["data"]
    plan = auth_client.post(
        "/api/finance/plans", json={"projectId": project["id"], "title": "首款", "amount": 3000}
    ).json()["data"]
    assert plan["percentOf"] == 30
    assert plan["projectName"] == "官网改造"


def test_overdue_plan(auth_client):
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    plan = auth_client.post(
        "/api/finance/plans", json={"title": "首款", "amount": 500, "dueDate": yesterday}
    ).json()["data"]
    assert plan["isOverdue"] is True


def test_expense_round_trip(auth_client):
    response = auth_client.post("/api/finance/expenses", json={"category": "差旅", "amount": 128.5})
    assert response.status_code == 200
    assert response.json()["data"]["category"] == "差旅"
    assert auth_client.get("/api/finance/expenses").json()["data"][0]["amount"] == 128.5


def test_stats_aggregates(auth_client):
    _invoice(auth_client, amount=1000, taxRate=6)
    auth_client.post("/api/finance/payments", json={"invoiceId": "x", "amount": 400})
    auth_client.post("/api/finance/expenses", json={"category": "差旅", "amount": 100})

    response = auth_client.get("/api/finance/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["expenseTotal"] == 100
    assert len(data["months"]) == 1
    assert data["months"][0]["income"] == 400
    assert data["months"][0]["expense"] == 100
    assert data["months"][0]["net"] == 300
