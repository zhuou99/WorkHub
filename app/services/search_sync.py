"""wh_search 索引的写入侧：对应 C# 的 WorkHub/Common/SearchSync.cs。

引擎探测、各来源取文、增量落索引都收在这儿。业务服务保存/删除后只需 sync/drop 一句。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.content import WhArticle, WhBookmark, WhNote, WhSnippet
from app.models.rss import WhRssFeed, WhRssItem

__all__ = ["Doc", "engine", "sync", "drop", "rebuild_all", "sync_kind", "collect", "one_line", "NOTE", "ARTICLE", "BOOKMARK", "SNIPPET", "RSS"]

logger = logging.getLogger("workhub.search")

NOTE = "note"
ARTICLE = "article"
BOOKMARK = "bookmark"
SNIPPET = "snippet"
RSS = "rss"

_SPACES = re.compile(r"\s+")

# 引擎探测结果按数据库连接缓存：同一连接只探一次，不同库（测试里）互不污染。
_engine_cache: dict[int, str] = {}


@dataclass
class Doc:
    id: str
    kind: str
    title: str = ""
    url: str = ""
    body: str = ""
    tags: str = ""
    time: str = ""


def engine(db: Session) -> str:
    """建表并返回引擎名：trigram → fts5 → like 三级降级。"""
    key = id(db.get_bind())
    cached = _engine_cache.get(key)
    if cached:
        return cached

    ddl = db.execute(text("select sql from sqlite_master where type='table' and name='wh_search'")).scalar()
    if ddl and "fts5" in ddl and "url unindexed" in ddl:
        result = "trigram" if "trigram" in ddl else "fts5"
        _engine_cache[key] = result
        return result

    # 旧版索引表没有 url 列，删掉重建一次即可
    if ddl:
        db.execute(text("drop table wh_search"))
    db.execute(text("create table if not exists wh_search_state(id integer primary key, built_at text, engine text)"))
    cols = "id unindexed, kind, title, body, tags, url unindexed, time unindexed"
    try:
        db.execute(text(f"create virtual table wh_search using fts5({cols}, tokenize='trigram')"))
        result = "trigram"
    except Exception:
        try:
            db.execute(text(f"create virtual table wh_search using fts5({cols})"))
            result = "fts5"
        except Exception:
            result = "like"
    db.commit()
    _engine_cache[key] = result
    return result


def rebuild_all(db: Session) -> int:
    """整库重建：清空索引再把五类来源全写一遍，返回应有的条数。"""
    docs = collect(db)
    if engine(db) == "like":
        return len(docs)
    db.execute(text("delete from wh_search"))
    for doc in docs:
        _insert(db, doc)
    _touch(db)
    db.commit()
    return len(docs)


def sync(db: Session, kind: str, doc_id: str) -> None:
    """按 Id 把源记录的最新内容写进索引；源不在了就当删除。"""
    _safe(db, doc_id, lambda: _write(db, _pick(db, kind, doc_id), doc_id))


def drop(db: Session, doc_id: str) -> None:
    """源记录被删掉了，索引里那行也跟着走。"""
    _safe(db, doc_id, lambda: _write(db, None, doc_id))


def sync_kind(db: Session, kind: str) -> None:
    """整类重建。"""
    def action():
        db.execute(text("delete from wh_search where kind = :k"), {"k": kind})
        for doc in collect(db, kind):
            _insert(db, doc)
        _touch(db)
        db.commit()

    _safe(db, kind, action)


def _safe(db: Session, doc_id: str, action) -> None:
    """索引写失败不该把业务保存一起带倒。"""
    if not doc_id:
        return
    try:
        if engine(db) == "like":
            return
        action()
    except Exception as exc:
        db.rollback()
        logger.error("search index sync failed (%s): %s", doc_id, exc)


def _write(db: Session, doc: Doc | None, doc_id: str) -> None:
    db.execute(text("delete from wh_search where id = :id"), {"id": doc_id})
    if doc is not None:
        _insert(db, doc)
    _touch(db)
    db.commit()


def _insert(db: Session, doc: Doc) -> None:
    db.execute(
        text(
            "insert into wh_search(id, kind, title, body, tags, url, time) "
            "values (:id, :kind, :title, :body, :tags, :url, :time)"
        ),
        {
            "id": doc.id,
            "kind": doc.kind,
            "title": doc.title or "",
            "body": one_line(doc.body),
            "tags": doc.tags or "",
            "url": doc.url or "",
            "time": doc.time,
        },
    )


def _touch(db: Session) -> None:
    db.execute(
        text("insert or replace into wh_search_state(id, built_at, engine) values (1, :t, :e)"),
        {"t": _stamp_now(), "e": engine(db)},
    )


def _stamp_now() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _pick(db: Session, kind: str, doc_id: str) -> Doc | None:
    if kind == NOTE:
        return _of_note(db.get(WhNote, doc_id))
    if kind == ARTICLE:
        return _of_article(db.get(WhArticle, doc_id))
    if kind == BOOKMARK:
        return _of_bookmark(db.get(WhBookmark, doc_id))
    if kind == SNIPPET:
        return _of_snippet(db.get(WhSnippet, doc_id))
    if kind == RSS:
        item = db.get(WhRssItem, doc_id)
        if item is None:
            return None
        feed = db.get(WhRssFeed, item.FeedId)
        return _of_rss(item, feed.Title if feed else "")
    return None


def collect(db: Session, kind: str | None = None) -> list[Doc]:
    """取源数据；kind 为空是全部。"""
    docs: list[Doc] = []

    if kind in (None, NOTE):
        for item in db.execute(select(WhNote)).scalars():
            docs.append(_of_note(item))
    if kind in (None, ARTICLE):
        for item in db.execute(select(WhArticle)).scalars():
            docs.append(_of_article(item))
    if kind in (None, BOOKMARK):
        for item in db.execute(select(WhBookmark)).scalars():
            docs.append(_of_bookmark(item))
    if kind in (None, SNIPPET):
        for item in db.execute(select(WhSnippet)).scalars():
            docs.append(_of_snippet(item))
    if kind in (None, RSS):
        names = {feed.Id: feed.Title for feed in db.execute(select(WhRssFeed)).scalars()}
        for item in db.execute(select(WhRssItem)).scalars():
            docs.append(_of_rss(item, names.get(item.FeedId, "")))
    return docs


def _of_note(item: WhNote | None) -> Doc | None:
    if item is None:
        return None
    return Doc(item.Id, NOTE, item.Title or "", "", item.Content or "", item.Tags or "", _stamp(item))


def _of_article(item: WhArticle | None) -> Doc | None:
    if item is None:
        return None
    body = f"{item.Summary or ''} \n {item.Content or ''}"
    return Doc(item.Id, ARTICLE, item.Title or "", "", body, item.Tags or "", _stamp(item, item.PublishTime))


def _of_bookmark(item: WhBookmark | None) -> Doc | None:
    if item is None:
        return None
    body = f"{item.Summary or ''} \n {item.Content or ''}"
    tags = f"{item.Tags or ''} {item.Site or ''}"
    return Doc(item.Id, BOOKMARK, item.Title or "", item.Url or "", body, tags, _stamp(item))


def _of_snippet(item: WhSnippet | None) -> Doc | None:
    if item is None:
        return None
    body = f"{item.Description or ''} \n {item.Code or ''}"
    tags = f"{item.Tags or ''} {item.Language or ''}"
    return Doc(item.Id, SNIPPET, item.Title or "", "", body, tags, _stamp(item))


def _of_rss(item: WhRssItem, feed_title: str) -> Doc | None:
    if item is None:
        return None
    body = f"{item.Summary or ''} \n {item.Author or ''}"
    return Doc(item.Id, RSS, item.Title or "", item.Url or "", body, feed_title or "", _stamp(item, item.PublishedAt))


def _stamp(item, prefer=None) -> str:
    """取时间列并格式化成 yyyy-MM-dd HH:mm:ss。"""
    moment = prefer or item.ModifyTime or item.CreateTime
    if moment is None:
        return ""
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def one_line(text: str | None) -> str:
    """FTS5 存的是压平后的正文，检索页截上下文也按同一套来。"""
    if not text:
        return ""
    return _SPACES.sub(" ", text).strip()
