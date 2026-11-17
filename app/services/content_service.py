"""内容类实体：笔记、文章、代码片段、收藏。

对应 C# 的 NoteService / ArticleService / SnippetService / BookmarkService。
保存走「按 Id 回读再拷贝字段」，删除后同步清索引。
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.paging import clamp_paging
from app.models.content import WhArticle, WhBookmark, WhNote, WhSnippet
from app.schemas.content import ArticleIn, BookmarkIn, NoteIn, SnippetIn
from app.services import search_sync
from app.services.crud import LOCAL, now

__all__ = ["NoteService", "ArticleService", "SnippetService", "BookmarkService"]


def _stamp(value) -> object:
    return value or ""


class NoteService:
    def __init__(self, session: Session):
        self._db = session

    def save(self, note: NoteIn) -> WhNote | None:
        if note is None or not (note.Title or "").strip():
            return None
        old = self._db.get(WhNote, note.Id) if note.Id else None
        if old is None:
            entity = WhNote(Title=note.Title, Content=note.Content, Tags=note.Tags, Pinned=note.Pinned,
                            CreateBy=LOCAL, CreateTime=now())
            self._db.add(entity)
            self._db.commit()
            search_sync.sync(self._db, search_sync.NOTE, entity.Id)
            return entity
        old.Title = note.Title
        old.Content = note.Content
        old.Tags = note.Tags
        old.Pinned = note.Pinned
        old.ModifyBy = LOCAL
        old.ModifyTime = now()
        self._db.add(old)
        self._db.commit()
        search_sync.sync(self._db, search_sync.NOTE, old.Id)
        return old

    def delete(self, note_id: str) -> None:
        if not note_id:
            return
        entity = self._db.get(WhNote, note_id)
        if entity is not None:
            self._db.delete(entity)
            self._db.commit()
        search_sync.drop(self._db, note_id)

    def get(self, note_id: str) -> WhNote | None:
        return self._db.get(WhNote, note_id)

    def get_all(self) -> list[WhNote]:
        """置顶优先、新→旧。"""
        from datetime import datetime

        rows = list(self._db.execute(select(WhNote)).scalars().all())
        return sorted(
            rows,
            key=lambda item: (bool(item.Pinned), item.CreateTime or datetime.min),
            reverse=True,
        )

    def page(self, page_index: int, page_size: int, keyword: str) -> tuple[int, list[dict]]:
        index, size = clamp_paging(page_index, page_size)
        where = ""
        params: dict = {}
        if keyword and keyword.strip():
            where = (
                "instr(lower(coalesce(Title,'')),lower(:kw)) > 0"
                " or instr(lower(coalesce(Content,'')),lower(:kw)) > 0"
                " or instr(lower(coalesce(Tags,'')),lower(:kw)) > 0"
            )
            params["kw"] = keyword
        total = self._db.execute(
            text(f"select count(*) from wh_note{' where ' + where if where else ''}"), params
        ).scalar() or 0
        sql = (
            "select Id, Title, Tags, Pinned, CreateTime, substr(Content,1,120) as Content from wh_note"
            + (f" where {where}" if where else "")
            + " order by Pinned desc, CreateTime desc, Id desc limit :lim offset :off"
        )
        rows = self._db.execute(text(sql), {**params, "lim": size, "off": (index - 1) * size}).mappings().all()
        return int(total), [dict(row) for row in rows]


class ArticleService:
    def __init__(self, session: Session):
        self._db = session

    def save(self, article: ArticleIn) -> WhArticle | None:
        if article is None or not (article.Title or "").strip():
            return None
        old = self._db.get(WhArticle, article.Id) if article.Id else None
        if old is None:
            entity = WhArticle(Title=article.Title, Summary=article.Summary, Cover=article.Cover,
                               Tags=article.Tags, ProjectId=article.ProjectId, Content=article.Content,
                               Status=article.Status, PublishTime=article.PublishTime,
                               CreateBy=LOCAL, CreateTime=now())
            self._db.add(entity)
            self._db.commit()
            search_sync.sync(self._db, search_sync.ARTICLE, entity.Id)
            return entity
        old.Title = article.Title
        old.Summary = article.Summary
        old.Cover = article.Cover
        old.Tags = article.Tags
        old.ProjectId = article.ProjectId
        old.Content = article.Content
        old.Status = article.Status
        old.PublishTime = article.PublishTime
        old.ModifyBy = LOCAL
        old.ModifyTime = now()
        self._db.add(old)
        self._db.commit()
        search_sync.sync(self._db, search_sync.ARTICLE, old.Id)
        return old

    def delete(self, article_id: str) -> None:
        if not article_id:
            return
        entity = self._db.get(WhArticle, article_id)
        if entity is not None:
            self._db.delete(entity)
            self._db.commit()
        search_sync.drop(self._db, article_id)

    def get(self, article_id: str) -> WhArticle | None:
        return self._db.get(WhArticle, article_id)

    def get_all(self) -> list[WhArticle]:
        rows = list(self._db.execute(select(WhArticle)).scalars().all())
        return sorted(rows, key=lambda item: _stamp(item.CreateTime), reverse=True)

    def set_status(self, article_id: str, status: str) -> WhArticle | None:
        article = self._db.get(WhArticle, article_id)
        if article is None:
            return None
        article.Status = status
        if status == "done":
            article.PublishTime = now()
        article.ModifyBy = LOCAL
        article.ModifyTime = now()
        self._db.add(article)
        self._db.commit()
        search_sync.sync(self._db, search_sync.ARTICLE, article_id)
        return article

    def page(self, page_index: int, page_size: int, keyword: str, project_id: str) -> tuple[int, list[dict]]:
        index, size = clamp_paging(page_index, page_size)
        conditions: list[str] = []
        params: dict = {}
        if keyword and keyword.strip():
            conditions.append(
                "(instr(lower(coalesce(Title,'')),lower(:kw)) > 0"
                " or instr(lower(coalesce(Summary,'')),lower(:kw)) > 0"
                " or instr(lower(coalesce(Content,'')),lower(:kw)) > 0"
                " or instr(lower(coalesce(Tags,'')),lower(:kw)) > 0)"
            )
            params["kw"] = keyword
        if project_id:
            conditions.append("ProjectId = :projectId")
            params["projectId"] = project_id
        where = " and ".join(conditions)
        total = self._db.execute(
            text(f"select count(*) from wh_article{' where ' + where if where else ''}"), params
        ).scalar() or 0
        sql = (
            "select Id, Title, Summary, Tags, Status, ProjectId, CreateTime, PublishTime,"
            " substr(Content,1,120) as Content from wh_article"
            + (f" where {where}" if where else "")
            + " order by CreateTime desc, Id desc limit :lim offset :off"
        )
        rows = self._db.execute(text(sql), {**params, "lim": size, "off": (index - 1) * size}).mappings().all()
        return int(total), [dict(row) for row in rows]


class SnippetService:
    def __init__(self, session: Session):
        self._db = session

    def save(self, snippet: SnippetIn) -> WhSnippet | None:
        if snippet is None or not (snippet.Title or "").strip():
            return None
        old = self._db.get(WhSnippet, snippet.Id) if snippet.Id else None
        if old is None:
            entity = WhSnippet(Title=snippet.Title, Language=snippet.Language, Code=snippet.Code,
                               Description=snippet.Description, Tags=snippet.Tags,
                               CreateBy=LOCAL, CreateTime=now())
            self._db.add(entity)
            self._db.commit()
            search_sync.sync(self._db, search_sync.SNIPPET, entity.Id)
            return entity
        old.Title = snippet.Title
        old.Language = snippet.Language
        old.Code = snippet.Code
        old.Description = snippet.Description
        old.Tags = snippet.Tags
        old.ModifyBy = LOCAL
        old.ModifyTime = now()
        self._db.add(old)
        self._db.commit()
        search_sync.sync(self._db, search_sync.SNIPPET, old.Id)
        return old

    def delete(self, snippet_id: str) -> None:
        if not snippet_id:
            return
        entity = self._db.get(WhSnippet, snippet_id)
        if entity is not None:
            self._db.delete(entity)
            self._db.commit()
        search_sync.drop(self._db, snippet_id)

    def get_all(self) -> list[WhSnippet]:
        rows = list(self._db.execute(select(WhSnippet)).scalars().all())
        return sorted(rows, key=lambda item: _stamp(item.CreateTime), reverse=True)


class BookmarkService:
    def __init__(self, session: Session, storage):
        self._db = session
        self._storage = storage

    def clip(self, url: str) -> WhBookmark:
        from app.common.html_clipper import clip, save_snapshot

        result = clip(url)
        entity = WhBookmark(
            Title=result.title, Url=url.strip(), Site=result.site, Summary=result.summary,
            Content=result.content, Snapshot=save_snapshot(self._storage, result.html),
            Status="unread", CreateBy=LOCAL, CreateTime=now(),
        )
        self._db.add(entity)
        self._db.commit()
        search_sync.sync(self._db, search_sync.BOOKMARK, entity.Id)
        return entity

    def save(self, bookmark: BookmarkIn) -> WhBookmark | None:
        if bookmark is None or not (bookmark.Title or "").strip() or not (bookmark.Url or "").strip():
            return None
        old = self._db.get(WhBookmark, bookmark.Id) if bookmark.Id else None
        if old is None:
            entity = WhBookmark(Title=bookmark.Title, Url=bookmark.Url, Site=bookmark.Site,
                                Summary=bookmark.Summary, Content=bookmark.Content, Tags=bookmark.Tags,
                                Status=bookmark.Status, Favorite=bookmark.Favorite, Snapshot=bookmark.Snapshot,
                                CreateBy=LOCAL, CreateTime=now())
            self._db.add(entity)
            self._db.commit()
            search_sync.sync(self._db, search_sync.BOOKMARK, entity.Id)
            return entity
        old.Title = bookmark.Title
        old.Url = bookmark.Url
        old.Site = bookmark.Site
        old.Summary = bookmark.Summary
        old.Content = bookmark.Content
        old.Tags = bookmark.Tags
        old.Status = bookmark.Status
        old.Favorite = bookmark.Favorite
        old.Snapshot = bookmark.Snapshot
        old.ModifyBy = LOCAL
        old.ModifyTime = now()
        self._db.add(old)
        self._db.commit()
        search_sync.sync(self._db, search_sync.BOOKMARK, old.Id)
        return old

    def delete(self, bookmark_id: str) -> None:
        if not bookmark_id:
            return
        entity = self._db.get(WhBookmark, bookmark_id)
        if entity is not None:
            self._db.delete(entity)
            self._db.commit()
        search_sync.drop(self._db, bookmark_id)

    def get_all(self) -> list[WhBookmark]:
        rows = list(self._db.execute(select(WhBookmark)).scalars().all())
        return sorted(rows, key=lambda item: _stamp(item.CreateTime), reverse=True)
