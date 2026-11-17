"""客户档案与沟通留痕：对应 C# 的 WorkHub/Services/ClientService.cs。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.models.crm import WhClient, WhCommLog, WhProject
from app.models.finance import WhInvoice, WhPayment
from app.schemas.common import DeleteImpact, LinkGroup
from app.schemas.crm import ClientIn, CommLogIn
from app.services.crud import delete_where, unbind, upsert

__all__ = ["ClientService"]

CLIENT_FIELDS = (
    "Name", "Contact", "Phone", "Email", "Wechat", "Source", "Tags", "Note", "Archived",
)
LOG_FIELDS = ("ClientId", "Type", "Content", "HappenTime", "Next")


class ClientService:
    def __init__(self, session: Session):
        self._session = session

    def all(self) -> list[WhClient]:
        """全部客户；归档的排后面，同组按名称排。"""
        rows = list(self._session.execute(select(WhClient)).scalars().all())
        return sorted(rows, key=lambda item: (bool(item.Archived), item.Name or ""))

    def save(self, client: ClientIn, client_id: str | None = None) -> WhClient:
        entity = WhClient(Id=client_id or "")
        for name in CLIENT_FIELDS:
            setattr(entity, name, getattr(client, name))
        return upsert(self._session, entity, CLIENT_FIELDS)

    def preview_delete(self, client_id: str) -> DeleteImpact:
        """删客户前先看有哪些记录挂在它身上，页面据此决定是归档还是一把删干净。"""
        client = self._session.get(WhClient, client_id)
        impact = DeleteImpact(Name=client.Name if client else "")
        if client is None:
            return impact

        impact.Groups.append(LinkGroup(Label="沟通记录", Count=self._count(WhCommLog, WhCommLog.ClientId == client_id), Mode="cascade"))
        impact.Groups.append(LinkGroup(Label="项目", Count=self._count(WhProject, WhProject.ClientId == client_id)))
        impact.Groups.append(LinkGroup(Label="发票", Count=self._count(WhInvoice, WhInvoice.ClientId == client_id)))
        impact.Groups.append(LinkGroup(Label="回款", Count=self._count(WhPayment, WhPayment.ClientId == client_id)))
        return impact

    def delete(self, client_id: str, detach: bool = False) -> str:
        """删除客户。沟通记录跟着清；detach 为真时把项目、发票、回款的客户归属一并解绑。"""
        client = self._session.get(WhClient, client_id)
        if client is None:
            raise WorkHubError("这个客户已经不在了。")

        logs = delete_where(self._session, WhCommLog, WhCommLog.ClientId == client_id)

        if detach:
            projects = unbind(self._session, WhProject, WhProject.ClientId == client_id, "ClientId")
            invoices = unbind(self._session, WhInvoice, WhInvoice.ClientId == client_id, "ClientId")
            payments = unbind(self._session, WhPayment, WhPayment.ClientId == client_id, "ClientId")
            tail = f"解绑 {projects} 个项目、{invoices} 张发票、{payments} 笔回款"
        else:
            tail = "项目与发票原样保留（客户列会显示「客户已删除」）"

        self._session.delete(client)
        self._session.commit()
        return f"已删除《{client.Name}》：清掉 {logs} 条沟通记录，{tail}。"

    def all_logs(self) -> list[WhCommLog]:
        """一次取回全部沟通记录，页面按客户分组；新的在前。"""
        rows = list(self._session.execute(select(WhCommLog)).scalars().all())
        return sorted(rows, key=lambda item: item.HappenTime or item.CreateTime, reverse=True)

    def save_log(self, log: CommLogIn, log_id: str | None = None) -> WhCommLog:
        from app.services.crud import now

        entity = WhCommLog(Id=log_id or "")
        for name in LOG_FIELDS:
            setattr(entity, name, getattr(log, name))
        if entity.HappenTime is None:
            entity.HappenTime = now()
        return upsert(self._session, entity, LOG_FIELDS)

    def delete_log(self, log_id: str) -> None:
        entity = self._session.get(WhCommLog, log_id)
        if entity is not None:
            self._session.delete(entity)
            self._session.commit()

    def _count(self, model, predicate) -> int:
        return len(list(self._session.execute(select(model).where(predicate)).scalars().all()))
