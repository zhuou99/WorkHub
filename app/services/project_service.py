"""项目台账与里程碑：对应 C# 的 WorkHub/Services/ProjectService.cs。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.models.crm import WhMilestone, WhProject, WhTask
from app.models.finance import WhExpense, WhInvoice, WhPaymentPlan
from app.schemas.common import DeleteImpact, LinkGroup
from app.schemas.crm import MilestoneIn, ProjectIn
from app.services.crud import delete_where, has_table, unbind, upsert

__all__ = ["ProjectService"]

PROJECT_FIELDS = (
    "Name", "ClientId", "Status", "Amount", "SignedDate", "StartDate", "EndDate",
    "ExpireDate", "ContractFile", "Terms", "Description",
)
MILESTONE_FIELDS = ("ProjectId", "Title", "StartDate", "DueDate", "Done", "DoneTime", "Sort")


class ProjectService:
    def __init__(self, session: Session):
        self._session = session

    def all(self) -> list[WhProject]:
        """洽谈/进行/验收/维护 排前面，完结沉底；同状态按最近改动。"""
        rows = list(self._session.execute(select(WhProject)).scalars().all())
        return sorted(rows, key=lambda item: (item.Status == "done", _stamp(item)))

    def save(self, project: ProjectIn, project_id: str | None = None) -> WhProject:
        entity = WhProject(Id=project_id or "")
        for name in PROJECT_FIELDS:
            setattr(entity, name, getattr(project, name))
        return upsert(self._session, entity, PROJECT_FIELDS)

    def preview_delete(self, project_id: str) -> DeleteImpact:
        """删项目前先看有哪些记录挂在它身上。"""
        project = self._session.get(WhProject, project_id)
        impact = DeleteImpact(Name=project.Name if project else "")
        if project is None:
            return impact

        impact.Groups.append(LinkGroup(Label="里程碑", Count=self._count(WhMilestone, WhMilestone.ProjectId == project_id), Mode="cascade"))
        impact.Groups.append(LinkGroup(Label="任务", Count=self._count(WhTask, WhTask.ProjectId == project_id)))
        impact.Groups.append(LinkGroup(Label="发票", Count=self._count(WhInvoice, WhInvoice.ProjectId == project_id)))
        impact.Groups.append(LinkGroup(Label="支出", Count=self._count(WhExpense, WhExpense.ProjectId == project_id)))
        impact.Groups.append(LinkGroup(Label="开源仓库", Count=self._count_optional("wh_repo", "wh_repo.ProjectId", project_id)))
        impact.Groups.append(LinkGroup(Label="回款计划", Count=self._count(WhPaymentPlan, WhPaymentPlan.ProjectId == project_id), Mode="cascade"))
        impact.Groups.append(LinkGroup(Label="文章", Count=self._count_optional("wh_article", "wh_article.ProjectId", project_id)))
        return impact

    def delete(self, project_id: str, detach: bool = False) -> str:
        """删除项目。里程碑跟着清；detach 为真时把任务、发票、支出、仓库的项目归属一并解绑。"""
        project = self._session.get(WhProject, project_id)
        if project is None:
            raise WorkHubError("这个项目已经不在了。")

        milestones = delete_where(self._session, WhMilestone, WhMilestone.ProjectId == project_id)
        # 回款计划拆的是这个项目的合同款，项目没了留着只会污染逾期统计，跟着一起清
        plans = delete_where(self._session, WhPaymentPlan, WhPaymentPlan.ProjectId == project_id)

        if detach:
            tasks = unbind(self._session, WhTask, WhTask.ProjectId == project_id, "ProjectId")
            invoices = unbind(self._session, WhInvoice, WhInvoice.ProjectId == project_id, "ProjectId")
            expenses = unbind(self._session, WhExpense, WhExpense.ProjectId == project_id, "ProjectId")
            tail = f"解绑 {tasks} 个任务、{invoices} 张发票、{expenses} 笔支出"
        else:
            tail = "任务与发票原样保留（项目列会显示「项目已删除」）"

        self._session.delete(project)
        self._session.commit()
        return f"已删除《{project.Name}》：清掉 {milestones} 个里程碑、{plans} 期回款计划，{tail}。"

    def all_milestones(self) -> list[WhMilestone]:
        rows = list(self._session.execute(select(WhMilestone)).scalars().all())
        return sorted(rows, key=lambda item: (item.Sort, item.CreateTime))

    def save_milestone(self, milestone: MilestoneIn, milestone_id: str | None = None) -> WhMilestone:
        entity = WhMilestone(Id=milestone_id or "")
        for name in MILESTONE_FIELDS:
            setattr(entity, name, getattr(milestone, name))
        return upsert(self._session, entity, MILESTONE_FIELDS)

    def delete_milestone(self, milestone_id: str) -> None:
        entity = self._session.get(WhMilestone, milestone_id)
        if entity is not None:
            self._session.delete(entity)
            self._session.commit()

    def _count(self, model, predicate) -> int:
        return len(list(self._session.execute(select(model).where(predicate)).scalars().all()))

    def _count_optional(self, table: str, column: str, value: str) -> int:
        """阶段 2 的表还没建时计数记 0，不报错。"""
        if not has_table(self._session, table):
            return 0
        from sqlalchemy import text

        rows = self._session.execute(text(f"SELECT COUNT(1) FROM {table} WHERE {column} = :v"), {"v": value})
        return int(rows.scalar() or 0)


def _stamp(item) -> object:
    """排序用的时间戳：ModifyTime 优先，没有就用 CreateTime。"""
    return item.ModifyTime or item.CreateTime or ""
