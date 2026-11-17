"""全站全文检索：对应 C# 的 WorkHub/Services/SearchService.cs。

SQLite FTS5 索引笔记/文章/收藏/代码片段/RSS 条目；日常增删改由各服务增量写索引
（见 search_sync），这里只留全量兜底与查询。
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.search import SearchHit, SearchIndex, SearchPart, SearchResult
from app.services import search_sync
from app.services.search_sync import one_line

__all__ = ["SearchService"]

_SOURCE = (
    "select 'note' kind, Id id, Title title, '' url, coalesce(Content, '') body, "
    "coalesce(ModifyTime, CreateTime) time from wh_note "
    "union all select 'article', Id, Title, '', coalesce(Summary, '') || ' ' || coalesce(Content, ''), "
    "coalesce(PublishTime, ModifyTime, CreateTime) from wh_article "
    "union all select 'bookmark', Id, Title, coalesce(Url, ''), coalesce(Summary, '') || ' ' || coalesce(Content, ''), "
    "coalesce(ModifyTime, CreateTime) from wh_bookmark "
    "union all select 'snippet', Id, Title, '', coalesce(Description, '') || ' ' || coalesce(Code, ''), "
    "coalesce(ModifyTime, CreateTime) from wh_snippet "
    "union all select 'rss', Id, Title, coalesce(Url, ''), coalesce(Summary, ''), "
    "coalesce(PublishedAt, CreateTime) from wh_rss_item"
)


class SearchService:
    def __init__(self, session: Session):
        self._db = session

    def get_index(self) -> SearchIndex:
        engine = search_sync.engine(self._db)
        index = SearchIndex(Engine=_engine_name(engine))
        if engine != "like":
            index.Count = self._db.execute(text("select count(*) from wh_search")).scalar() or 0
            index.Source = self._db.execute(text(f"select count(*) from ({_SOURCE}) s")).scalar() or 0
            index.Gap = abs(index.Source - index.Count)
            row = self._db.execute(text("select built_at from wh_search_state where id=1")).first()
            index.BuiltAt = row[0] if row else ""
        else:
            index.Source = self._db.execute(text(f"select count(*) from ({_SOURCE}) s")).scalar() or 0
        return index

    def rebuild(self) -> tuple[int, str]:
        engine = search_sync.engine(self._db)
        count = search_sync.rebuild_all(self._db)
        return count, _engine_name(engine)

    def search(self, keyword: str, kind: str) -> SearchResult:
        result = SearchResult()
        if not (keyword or "").strip():
            return result

        keyword = keyword.strip()
        engine = search_sync.engine(self._db)
        # trigram 至少要凑出一个三元组，两字以下的词只能走 LIKE
        use_fts = engine in ("trigram", "fts5") and len(keyword) >= 3
        result.Engine = _engine_name(engine if use_fts else "like")

        rows = self._fts(keyword, kind) if use_fts else self._like(keyword, kind)
        for row in rows:
            hit = SearchHit(
                Id=row["id"],
                Kind=row["kind"],
                Title=row["title"],
                Url=row["url"],
                Time=_short(row["time"], 16),
            )
            hit.TitleParts = _mark(hit.Title, keyword)
            hit.Parts = _window(row["snip"], keyword)
            result.Hits.append(hit)

        counts = self._fts_counts(keyword) if use_fts else self._like_counts(keyword)
        for row in counts:
            result.Kinds[row["kind"]] = int(row["c"])
        return result

    # ---------- FTS5 ----------

    def _fts(self, keyword: str, kind: str):
        match = _phrase(keyword) if not kind else f"kind:{kind} {_phrase(keyword)}"
        sql = (
            "select id, kind, title, url, time, "
            "substr(body, case when instr(lower(body), :plain) > 60 "
            "then instr(lower(body), :plain) - 60 else 1 end, 220) snip "
            "from wh_search where wh_search match :m order by rank limit 80"
        )
        rows = self._db.execute(text(sql), {"m": match, "plain": keyword.lower()}).mappings().all()
        return [dict(row) for row in rows]

    def _fts_counts(self, keyword: str):
        rows = self._db.execute(
            text("select kind, count(*) c from wh_search where wh_search match :m group by kind"),
            {"m": _phrase(keyword)},
        ).mappings().all()
        return [dict(row) for row in rows]

    # ---------- LIKE 兜底 ----------

    def _like(self, keyword: str, kind: str):
        sql = (
            f"select id, kind, title, url, time, body snip from ({_SOURCE}) s "
            "where kind like :k and (lower(title) like :p escape '\\' or lower(body) like :p escape '\\') "
            "order by time desc limit 80"
        )
        rows = self._db.execute(
            text(sql), {"k": "%" if not kind else kind, "p": _like_param(keyword.lower())}
        ).mappings().all()
        return [dict(row) for row in rows]

    def _like_counts(self, keyword: str):
        sql = (
            f"select kind, count(*) c from ({_SOURCE}) s "
            "where lower(title) like :p escape '\\' or lower(body) like :p escape '\\' group by kind"
        )
        rows = self._db.execute(text(sql), {"p": _like_param(keyword.lower())}).mappings().all()
        return [dict(row) for row in rows]


# ---------- 纯函数 ----------


def _phrase(keyword: str) -> str:
    return '"' + keyword.replace('"', '""') + '"'


def _like_param(keyword: str) -> str:
    return "%" + keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _engine_name(engine: str) -> str:
    return {
        "trigram": "FTS5 · trigram",
        "fts5": "FTS5 · 默认分词",
    }.get(engine, "LIKE 扫描")


def _short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit]


def _window(body: str, keyword: str) -> list[SearchPart]:
    """LIKE 分支没有现成片段，按关键词位置截一段上下文再切高亮。"""
    flat = one_line(body)
    if not flat:
        return []

    index = flat.lower().find(keyword.lower())
    if index < 0:
        return [SearchPart(Text=_short(flat, 160))]

    start = max(0, index - 30)
    end = min(len(flat), start + 200)
    parts: list[SearchPart] = []
    if start > 0:
        parts.append(SearchPart(Text="…"))
    parts.extend(_mark(flat[start:end], keyword))
    if end < len(flat):
        parts.append(SearchPart(Text="…"))
    return parts


def _mark(text: str, keyword: str) -> list[SearchPart]:
    """按关键词把文本切段（大小写不敏感），命中段标 Mark。"""
    if not text:
        return []
    parts: list[SearchPart] = []
    index = 0
    lowered = text.lower()
    needle = keyword.lower()
    while True:
        hit = lowered.find(needle, index) if needle else -1
        if hit < 0:
            parts.append(SearchPart(Text=text[index:]))
            break
        if hit > index:
            parts.append(SearchPart(Text=text[index:hit]))
        parts.append(SearchPart(Text=text[hit:hit + len(keyword)], Mark=True))
        index = hit + len(keyword)
    return parts
