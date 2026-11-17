"""开源仓库镜像与 GitHub 同步：对应 C# 的 WorkHub/Services/RepoService.cs。

API 全部可降级：没网/没额度就把上一次快照留着显示，不糊弄成 0。
Token 走 SecretProtector 加密存 SysConfig。
"""

from __future__ import annotations

import json
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.common.secrets import get_secret
from app.models.repo import WhReleasePlan, WhRepo, WhRepoSnapshot
from app.schemas.repo import ReleasePlanIn, RepoIn
from app.services.crud import LOCAL, now

__all__ = ["RepoService"]

_API = "https://api.github.com"
_KEEP_SNAPSHOTS = 120


class RepoService:
    def __init__(self, session: Session, config, protector):
        self._db = session
        self._config = config
        self._protector = protector
        self._http = httpx.Client(timeout=20.0)

    def board(self) -> dict:
        repos = sorted(self._all_repos(), key=lambda item: (item.Owner or "", item.Name or ""))
        snapshots = sorted(self._all_snapshots(), key=lambda item: item.CreateTime or now())
        plans = sorted(self._all_plans(), key=lambda item: (bool(item.Released), item.PlanDate or now()))
        return {
            "repos": repos,
            "snapshots": snapshots,
            "plans": plans,
            "hasToken": bool(get_secret(self._config, self._protector, "github.token")),
        }

    def save(self, repo: RepoIn) -> str:
        if repo is None or not (repo.Owner or "").strip() or not (repo.Name or "").strip():
            raise WorkHubError("所有者与仓库名都要填（如 knownliu/eims）。")

        owner = repo.Owner.strip().strip("/")
        name = repo.Name.strip().strip("/")
        # 有人会把整条浏览器地址粘进来，顺手拆成 owner/name
        if "/" in name:
            parts = f"{owner}/{name}".split("/")
            owner = parts[-2] if len(parts) >= 2 else owner
            name = parts[-1] if parts else name

        url = repo.Url
        if not (url or "").strip():
            url = f"https://github.com/{owner}/{name}"

        old = self._db.get(WhRepo, repo.Id) if repo.Id else None
        if old is None:
            old = WhRepo(Owner=owner, Name=name, Description=repo.Description, Url=url,
                         Homepage=repo.Homepage, ProjectId=repo.ProjectId, Note=repo.Note,
                         CreateBy=LOCAL, CreateTime=now())
            self._db.add(old)
        else:
            old.Owner = owner
            old.Name = name
            old.Description = repo.Description
            old.Url = url
            old.Homepage = repo.Homepage
            old.ProjectId = repo.ProjectId
            old.Note = repo.Note
            old.ModifyBy = LOCAL
            old.ModifyTime = now()
        self._db.add(old)
        self._db.commit()
        return "仓库已保存，点「同步」拉最新数据。"

    def delete(self, repo_id: str) -> None:
        if not repo_id:
            return
        repo = self._db.get(WhRepo, repo_id)
        if repo is not None:
            self._db.delete(repo)
        for snapshot in [item for item in self._all_snapshots() if item.RepoId == repo_id]:
            self._db.delete(snapshot)
        for plan in [item for item in self._all_plans() if item.RepoId == repo_id]:
            self._db.delete(plan)
        self._db.commit()

    def sync(self, repo_id: str) -> str:
        repo = self._db.get(WhRepo, repo_id)
        if repo is None:
            raise WorkHubError("仓库不存在，可能刚被删掉。")
        return self._pull(repo)

    def sync_all(self) -> str:
        repos = self._all_repos()
        ok = 0
        fails: list[str] = []
        for repo in repos:
            try:
                self._pull(repo)
                ok += 1
            except WorkHubError as exc:
                fails.append(f"{repo.Owner}/{repo.Name}：{exc}")
        if not fails:
            return f"同步完成 · {ok} 个仓库"
        raise WorkHubError(f"{ok} 个成功，{len(fails)} 个失败：{'；'.join(fails[:3])}")

    def save_plan(self, plan: ReleasePlanIn) -> str:
        if plan is None or not (plan.RepoId or "").strip() or not (plan.Tag or "").strip():
            raise WorkHubError("仓库和版本号都要填。")
        tag = plan.Tag.strip()
        old = self._db.get(WhReleasePlan, plan.Id) if plan.Id else None
        if old is None:
            old = WhReleasePlan(RepoId=plan.RepoId, Tag=tag, PlanDate=plan.PlanDate, Notes=plan.Notes,
                                CreateBy=LOCAL, CreateTime=now())
            self._db.add(old)
        else:
            old.RepoId = plan.RepoId
            old.Tag = tag
            old.PlanDate = plan.PlanDate
            old.Notes = plan.Notes
            old.ModifyBy = LOCAL
            old.ModifyTime = now()
        self._db.add(old)
        self._db.commit()
        return "发布计划已记下。"

    def toggle_plan(self, plan_id: str) -> str:
        plan = self._db.get(WhReleasePlan, plan_id)
        if plan is None:
            raise WorkHubError("计划不存在。")
        plan.Released = not plan.Released
        plan.ReleaseDate = now() if plan.Released else None
        plan.ModifyBy = LOCAL
        plan.ModifyTime = now()
        self._db.add(plan)
        self._db.commit()
        return f"已标记 {plan.Tag} 发布。" if plan.Released else f"已取消 {plan.Tag} 的发布标记。"

    def delete_plan(self, plan_id: str) -> None:
        plan = self._db.get(WhReleasePlan, plan_id)
        if plan is not None:
            self._db.delete(plan)
            self._db.commit()

    # ---------- 内部 ----------

    def _all_repos(self) -> list[WhRepo]:
        return list(self._db.execute(select(WhRepo)).scalars().all())

    def _all_snapshots(self) -> list[WhRepoSnapshot]:
        return list(self._db.execute(select(WhRepoSnapshot)).scalars().all())

    def _all_plans(self) -> list[WhReleasePlan]:
        return list(self._db.execute(select(WhReleasePlan)).scalars().all())

    def _pull(self, repo: WhRepo) -> str:
        token = get_secret(self._config, self._protector, "github.token")
        headers = {
            "User-Agent": "WorkHub/1.0",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            resp = self._http.get(f"{_API}/repos/{repo.Owner}/{repo.Name}", headers=headers)
        except httpx.HTTPError as exc:
            raise WorkHubError(f"连不上 GitHub：{exc}") from exc

        if resp.status_code == 404:
            raise WorkHubError(f"{repo.Owner}/{repo.Name} 不存在；私有仓库要配 GitHub Token。")
        if resp.status_code in (403, 429):
            if not token:
                raise WorkHubError("GitHub 匿名额度用完（60 次/小时）；配个 Token 能到 5000 次/小时。")
            raise WorkHubError("GitHub 拒绝了请求（Token 失效或权限不足），先检查设置里的 Token。")
        if resp.status_code >= 400:
            raise WorkHubError(f"GitHub HTTP {resp.status_code}")

        data = json.loads(resp.text)
        repo.Stars = _get_int(data, "stargazers_count")
        repo.Forks = _get_int(data, "forks_count")
        repo.OpenIssues = _get_int(data, "open_issues_count")
        repo.Language = _get_str(data, "language")
        repo.Homepage = _get_str(data, "homepage") or repo.Homepage
        repo.Url = _get_str(data, "html_url") or repo.Url
        repo.Description = _get_str(data, "description") or repo.Description
        repo.Topics = _get_topics(data)
        repo.PushedAt = _get_date(data, "pushed_at")
        repo.SyncTime = now()
        repo.ModifyBy = LOCAL
        repo.ModifyTime = now()

        latest = self._fetch_latest_release(repo, token)
        if latest is not None:
            repo.LastRelease, repo.LastReleaseAt = latest

        self._db.add(repo)
        self._db.commit()
        self._add_snapshot(repo)
        return f"{repo.Owner}/{repo.Name} · {repo.Stars} Star"

    def _fetch_latest_release(self, repo: WhRepo, token: str) -> tuple[str, datetime] | None:
        headers = {"User-Agent": "WorkHub/1.0", "Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = self._http.get(f"{_API}/repos/{repo.Owner}/{repo.Name}/releases/latest", headers=headers)
            if resp.status_code >= 400:
                return None
            data = json.loads(resp.text)
            tag = _get_str(data, "tag_name")
            if not tag:
                return None
            return tag, _get_date(data, "published_at") or now()
        except (httpx.HTTPError, json.JSONDecodeError):
            # 没发过 Release 是常态（404），不该把整个同步搞失败
            return None

    def _add_snapshot(self, repo: WhRepo) -> None:
        self._db.add(WhRepoSnapshot(
            RepoId=repo.Id, Stars=repo.Stars, Forks=repo.Forks, OpenIssues=repo.OpenIssues,
            CreateBy=LOCAL, CreateTime=now(),
        ))
        self._db.commit()
        current = sorted(
            [item for item in self._all_snapshots() if item.RepoId == repo.Id],
            key=lambda item: item.CreateTime or now(),
            reverse=True,
        )
        for old in current[_KEEP_SNAPSHOTS:]:
            self._db.delete(old)
        self._db.commit()


def _get_str(data: dict, name: str) -> str | None:
    value = data.get(name)
    return value if isinstance(value, str) else None


def _get_int(data: dict, name: str) -> int:
    value = data.get(name)
    return value if isinstance(value, int) else 0


def _get_date(data: dict, name: str) -> datetime | None:
    text = _get_str(data, name)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _get_topics(data: dict) -> str | None:
    topics = data.get("topics")
    if not isinstance(topics, list):
        return None
    cleaned = [item for item in topics if isinstance(item, str) and item]
    return ",".join(cleaned) if cleaned else None
