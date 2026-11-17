"""近 N 天小结：对应 C# 的 WorkHub/Services/ReportService.cs。

把散在各台账里的动静汇成一篇 Markdown，可落成文章草稿或笔记。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.common.finance_calc import due as invoice_due
from app.common.finance_calc import is_invoice_overdue
from app.common.labels import article_status, comm_type, money, pay_method, task_status
from app.models.content import WhArticle, WhBookmark, WhNote, WhSnippet
from app.models.crm import WhClient, WhCommLog, WhMilestone, WhProject, WhTask
from app.models.finance import WhInvoice, WhPayment
from app.models.repo import WhReleasePlan, WhRepo, WhRepoSnapshot
from app.schemas.report import WeeklyReport, WeeklySection
from app.services import search_sync
from app.services.crud import LOCAL, now

__all__ = ["ReportService"]


class ReportService:
    def __init__(self, session: Session):
        self._db = session

    def build(self, days: int) -> WeeklyReport:
        if days < 1 or days > 90:
            days = 7

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        to = today + timedelta(days=1)
        from_ = to - timedelta(days=days)

        def in_range(value) -> bool:
            return value is not None and from_ <= value < to

        rep = WeeklyReport(Days=days)
        rep.Title = f"周报 · {_md(from_)} ~ {_md(to - timedelta(days=1))}"
        rep.Range = f"{from_:%Y-%m-%d} ~ {to - timedelta(days=1):%Y-%m-%d}"

        tasks = self._all(WhTask)
        projects = self._all(WhProject)
        clients = self._all(WhClient)
        invoices = self._all(WhInvoice)
        payments = self._all(WhPayment)
        comms = self._all(WhCommLog)
        milestones = self._all(WhMilestone)
        articles = self._all(WhArticle)
        notes = self._all(WhNote)
        snippets = self._all(WhSnippet)
        bookmarks = self._all(WhBookmark)
        repos = self._all(WhRepo)
        snapshots = self._all(WhRepoSnapshot)
        plans = self._all(WhReleasePlan)

        def proj_name(pid: str) -> str:
            return next((p.Name for p in projects if p.Id == pid), "未挂项目") or "未挂项目"

        def client_name(cid: str) -> str:
            return next((c.Name for c in clients if c.Id == cid), "客户") or "客户"

        def repo_name(rid: str) -> str:
            repo = next((r for r in repos if r.Id == rid), None)
            return "仓库" if repo is None else f"{repo.Owner}/{repo.Name}"

        # —— 任务 ——
        done = [t for t in tasks if in_range(t.DoneTime) or (t.Status == "done" and in_range(t.ModifyTime))]
        added = [t for t in tasks if in_range(t.CreateTime) and t.Status != "done"]
        doing = [t for t in tasks if t.Status == "doing"]
        task_lines = []
        task_lines += [f"- 完成：{t.Title}｜{proj_name(t.ProjectId)}" for t in done]
        task_lines += [f"- 新增：{t.Title}｜{task_status(t.Status)}｜到期 {_due(t)}" for t in added]
        task_lines += [f"- 推进中：{t.Title}" for t in doing if t not in added]

        # —— 客户与里程碑 ——
        comm_lines = []
        comm_lines += [f"- {client_name(c.ClientId)}｜{comm_type(c.Type)}｜{_cut(c.Content, 60)}"
                       for c in sorted((c for c in comms if in_range(c.HappenTime)),
                                       key=lambda c: c.HappenTime, reverse=True)]
        comm_lines += [f"- 里程碑交付：{m.Title}" for m in milestones if in_range(m.DoneTime)]
        comm_lines += [f"- 里程碑临期：{m.Title}（{_md(m.DueDate)}）"
                       for m in milestones if not m.Done and m.DueDate is not None
                       and today <= m.DueDate < today + timedelta(days=days)]

        # —— 财务 ——
        billed = [iv for iv in invoices if in_range(iv.IssueDate)]
        got = [p for p in payments if in_range(p.PayDate)]
        late = [iv for iv in invoices if is_invoice_overdue(iv, payments, today)]
        money_lines = []
        money_lines += [f"- 开票 {iv.No}｜{client_name(iv.ClientId)}｜{money(iv.Amount)}"
                        for iv in sorted(billed, key=lambda iv: iv.IssueDate, reverse=True)]
        money_lines += [f"- 回款 {money(p.Amount)}｜{client_name(p.ClientId)}｜{pay_method(p.Method)}"
                        for p in sorted(got, key=lambda p: p.PayDate, reverse=True)]
        money_lines += [f"- 逾期：{iv.No}｜{client_name(iv.ClientId)}｜待收 {money(invoice_due(iv, payments))}｜约定 {_md(iv.ExpectDate)}"
                        for iv in late]

        # —— 创作 ——
        art_lines = []
        art_lines += [f"- 已发布：{a.Title}" for a in articles if in_range(a.PublishTime)]
        art_lines += [f"- 新写：{a.Title}｜{article_status(a.Status)}"
                      for a in articles if in_range(a.CreateTime) and a.Status != "done"]
        art_lines += [f"- 笔记：{n.Title}" for n in notes if in_range(n.CreateTime)]
        art_lines += [f"- 片段：{s.Title}｜{s.Language}" for s in snippets if in_range(s.CreateTime)]
        art_lines += [f"- 剪藏：{b.Title}｜{b.Site}" for b in bookmarks if in_range(b.CreateTime)]

        # —— 开源 ——
        star_lines = []
        star_delta = 0
        for repo in repos:
            series = sorted(
                (s for s in snapshots if s.RepoId == repo.Id and from_ <= s.CreateTime < to),
                key=lambda s: s.CreateTime,
            )
            if len(series) < 2:
                continue
            delta = series[-1].Stars - series[0].Stars
            star_delta += delta
            star_lines.append(f"- {repo.Owner}/{repo.Name}:★ {_signed(delta)}（现 {series[-1].Stars:,}）")
        star_lines += [f"- 发版：{repo_name(p.RepoId)} {p.Tag}"
                       for p in plans if p.Released and in_range(p.ReleaseDate)]

        # —— 下周 ——
        next_lines = []
        next_lines += [f"- {t.Title}｜到期 {_md(t.DueDate)}｜{proj_name(t.ProjectId)}"
                       for t in sorted(
                           (t for t in tasks if t.Status != "done" and t.DueDate is not None
                            and today <= t.DueDate < today + timedelta(days=7)),
                           key=lambda t: t.DueDate)]
        next_lines += [f"- 里程碑：{m.Title}（{_md(m.DueDate)}）"
                       for m in milestones if not m.Done and m.DueDate is not None
                       and today <= m.DueDate < today + timedelta(days=14)]
        next_lines += [f"- 版本计划：{repo_name(p.RepoId)} {p.Tag}（{_md(p.PlanDate)}）"
                       for p in plans if not p.Released and p.PlanDate is not None
                       and today <= p.PlanDate < today + timedelta(days=14)]

        self._add(rep, "任务", f"{len(done)} 完成 · {len(doing)} 推进中", task_lines)
        self._add(rep, "客户与交付", f"{len(comm_lines)} 条", comm_lines)
        self._add(rep, "财务", f"开票 {money(_sum(billed, 'Amount'))} · 回款 {money(_sum(got, 'Amount'))}", money_lines)
        self._add(rep, "创作", f"{len(art_lines)} 条动静", art_lines)
        self._add(rep, "开源", f"★ {_signed(star_delta)}", star_lines)
        self._add(rep, "下周要盯", f"{len(next_lines)} 件", next_lines)

        content = (sum(1 for a in articles if in_range(a.CreateTime))
                   + sum(1 for n in notes if in_range(n.CreateTime))
                   + sum(1 for s in snippets if in_range(s.CreateTime))
                   + sum(1 for b in bookmarks if in_range(b.CreateTime)))
        rep.Summary = (
            f"近 {days} 天完成 {len(done)} 项任务，开票 {money(_sum(billed, 'Amount'))}、"
            f"回款 {money(_sum(got, 'Amount'))}，新增 {content} 条内容，Star {_signed(star_delta)}。"
        )
        rep.Markdown = self._render(rep)
        return rep

    def save_as_article(self, title: str, markdown: str) -> str:
        if not (markdown or "").strip():
            raise WorkHubError("没有内容可存。")
        entity = WhArticle(
            Title=_cut(title, 300), Summary="WorkHub 自动汇总的本周小结。", Content=markdown,
            Tags="周报", Status="draft", CreateBy=LOCAL, CreateTime=now(),
        )
        self._db.add(entity)
        self._db.commit()
        search_sync.sync(self._db, search_sync.ARTICLE, entity.Id)
        return f"已存为文章草稿《{entity.Title}》，去「文章」页接着改。"

    def save_as_note(self, title: str, markdown: str) -> str:
        if not (markdown or "").strip():
            raise WorkHubError("没有内容可存。")
        entity = WhNote(Title=_cut(title, 300), Content=markdown, Tags="周报", CreateBy=LOCAL, CreateTime=now())
        self._db.add(entity)
        self._db.commit()
        search_sync.sync(self._db, search_sync.NOTE, entity.Id)
        return f"已存为笔记《{entity.Title}》。"

    # ---------- 内部 ----------

    def _all(self, model):
        return list(self._db.execute(select(model)).scalars().all())

    @staticmethod
    def _add(rep: WeeklyReport, title: str, note: str, lines: list[str]) -> None:
        if not lines:
            return
        rep.Sections.append(WeeklySection(Title=title, Note=note, Lines=lines))

    @staticmethod
    def _render(rep: WeeklyReport) -> str:
        lines = [f"# {rep.Title}", "", f"> {rep.Summary}", ""]
        for section in rep.Sections:
            lines.append(f"## {section.Title}")
            lines.append("")
            lines.extend(section.Lines)
            lines.append("")
        lines.append(f"— 由 WorkHub 于 {now():%Y-%m-%d %H:%M} 汇总，区间 {rep.Range}。")
        return "\n".join(lines)


def _md(value) -> str:
    """跨平台的 M-d（glibc 的 %-m-%-d 在 Windows 上不认）。"""
    return f"{value.month}-{value.day}"


def _due(task) -> str:
    return _md(task.DueDate) if task.DueDate else "没定期"


def _cut(text: str | None, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "…"


def _signed(value: int) -> str:
    return f"{value:+d}" if value != 0 else "0"


def _sum(items, field: str) -> Decimal:
    return sum((getattr(item, field) or Decimal(0) for item in items), Decimal(0))
