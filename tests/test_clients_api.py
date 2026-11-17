"""客户接口：增删改、级联与解绑、删除影响预览的分组顺序。"""

from __future__ import annotations

from sqlalchemy import select

from app.models.crm import WhClient, WhCommLog
from app.models.finance import WhInvoice, WhPayment


def _create_client(client, name="甲方", **extra) -> dict:
    payload = {"name": name, **extra}
    response = client.post("/api/clients", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_create_and_list_client(auth_client):
    created = _create_client(auth_client, "甲方", contact="张三", phone="13800000000")
    assert created["name"] == "甲方"
    assert created["archived"] is False

    rows = auth_client.get("/api/clients").json()["data"]
    assert [row["name"] for row in rows] == ["甲方"]


def test_client_list_puts_archived_last(auth_client):
    _create_client(auth_client, "在用")
    _create_client(auth_client, "已归档", archived=True)
    rows = auth_client.get("/api/clients").json()["data"]
    assert [row["name"] for row in rows] == ["在用", "已归档"]


def test_comm_log_round_trip(auth_client):
    client_id = _create_client(auth_client)["id"]
    response = auth_client.post("/api/clients/logs", json={"clientId": client_id, "content": "聊了两句", "type": "phone"})
    assert response.status_code == 200
    assert response.json()["data"]["content"] == "聊了两句"

    logs = auth_client.get("/api/clients/logs").json()["data"]
    assert len(logs) == 1


def test_delete_impact_group_order(auth_client):
    client_id = _create_client(auth_client)["id"]
    auth_client.post("/api/clients/logs", json={"clientId": client_id, "content": "记录"})

    response = auth_client.get(f"/api/clients/delete-impact/{client_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert [group["label"] for group in data["groups"]] == ["沟通记录", "项目", "发票", "回款"]
    assert data["groups"][0]["mode"] == "cascade"
    assert data["groups"][0]["count"] == 1
    assert data["total"] == 1
    assert data["hasRefs"] is True


def test_delete_cascades_comm_logs_and_keeps_links(auth_client, app):
    client_id = _create_client(auth_client)["id"]
    auth_client.post("/api/clients/logs", json={"clientId": client_id, "content": "记录"})

    response = auth_client.delete(f"/api/clients/{client_id}")
    assert response.status_code == 200
    assert "已删除" in response.json()["message"]

    with app.state.sessionmaker() as session:
        assert session.execute(select(WhCommLog).where(WhCommLog.ClientId == client_id)).scalars().all() == []
        assert session.execute(select(WhClient).where(WhClient.Id == client_id)).scalars().all() == []


def test_delete_with_detach_clears_references(auth_client, app):
    """detach=true 时把挂着的发票、回款的客户归属清空，保留数据。"""
    client_id = _create_client(auth_client)["id"]
    invoice = auth_client.post(
        "/api/finance/invoices", json={"clientId": client_id, "amount": 100, "taxRate": 6}
    ).json()["data"]
    payment = auth_client.post(
        "/api/finance/payments", json={"invoiceId": invoice["id"], "clientId": client_id, "amount": 50}
    ).json()["data"]

    response = auth_client.delete(f"/api/clients/{client_id}?detach=true")
    assert response.status_code == 200

    with app.state.sessionmaker() as session:
        kept_invoice = session.execute(select(WhInvoice).where(WhInvoice.Id == invoice["id"])).scalars().first()
        kept_payment = session.execute(select(WhPayment).where(WhPayment.Id == payment["id"])).scalars().first()
        assert kept_invoice is not None and kept_invoice.ClientId == ""
        assert kept_payment is not None and kept_payment.ClientId == ""


def test_delete_without_detach_keeps_dangling_reference(auth_client, app):
    client_id = _create_client(auth_client)["id"]
    invoice = auth_client.post(
        "/api/finance/invoices", json={"clientId": client_id, "amount": 100, "taxRate": 6}
    ).json()["data"]

    auth_client.delete(f"/api/clients/{client_id}?detach=false")

    with app.state.sessionmaker() as session:
        kept = session.execute(select(WhInvoice).where(WhInvoice.Id == invoice["id"])).scalars().first()
        assert kept is not None and kept.ClientId == client_id
