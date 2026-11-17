"""RSS / Atom 订阅：对应 C# 的 WorkHub/Services/RssService.cs。

解析只用标准库（xml.etree），抓取失败一律退回上次数据，不把页面搞成空白。
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

import httpx
from lxml import html as lhtml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import WorkHubError
from app.models.content import WhBookmark
from app.models.rss import WhRssFeed, WhRssItem
from app.services import search_sync
from app.services.crud import LOCAL, now

__all__ = ["RssService"]

_UA = "WorkHub/1.0 (+personal reader)"
_ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
_GUESS_PATHS = ["/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml", "/index.xml", "/feed/", "/blog/feed"]
_KEEP_ITEMS = 200
_SPACES = re.compile(r"\s+")


class RssService:
    def __init__(self, session: Session, storage):
        self._db = session
        self._storage = storage
        self._http = httpx.Client(timeout=25.0, follow_redirects=True)

    # ---------- 读 ----------

    def board(self) -> dict:
        feeds = sorted(self._all_feeds(), key=lambda item: (item.Title or ""))
        items = self._all_items()
        starred = sum(1 for item in items if item.Starred)
        unread: dict[str, int] = {}
        for item in items:
            if not item.Read:
                unread[item.FeedId] = unread.get(item.FeedId, 0) + 1
        unread[""] = sum(1 for item in items if not item.Read)
        return {"feeds": feeds, "starred": starred, "unread": unread}

    def items(self, feed_id: str) -> list[WhRssItem]:
        items = [item for item in self._all_items() if item.FeedId == feed_id] if feed_id else self._all_items()
        return sorted(items, key=lambda item: item.PublishedAt or item.CreateTime or now(), reverse=True)

    # ---------- 订阅管理 ----------

    def add_feed(self, url: str) -> str:
        if not (url or "").strip():
            raise WorkHubError("先给一个地址：feed 链接或者站点首页都行。")

        url = url.strip()
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        if any(feed.Url.lower() == url.lower() for feed in self._all_feeds()):
            raise WorkHubError("已经订过了。")

        feed_url, error = self._resolve_feed(url)
        if feed_url is None:
            raise WorkHubError(error)

        feed = WhRssFeed(
            Title=_shorten(self._host(feed_url), 300),
            Url=feed_url,
            SiteUrl=self._host(url),
            CreateBy=LOCAL,
            CreateTime=now(),
        )
        self._db.add(feed)
        self._db.commit()

        ok, new_count, message = self._sync_core(feed)
        if not ok:
            return f"已订阅 {feed.Title}，但第一次同步没成功：{message}"
        return f"已订阅 {feed.Title}，抓到 {new_count} 条。" if new_count > 0 else f"已订阅 {feed.Title}，暂时还没有条目。"

    def sync(self, feed_id: str) -> str:
        feed = self._db.get(WhRssFeed, feed_id)
        if feed is None:
            raise WorkHubError("订阅源不存在，可能刚被删掉。")
        ok, new_count, message = self._sync_core(feed)
        if not ok:
            raise WorkHubError(message)
        return f"{feed.Title}：没有新条目。" if new_count == 0 else f"{feed.Title}：新增 {new_count} 条。"

    def sync_all(self) -> str:
        feeds = [feed for feed in self._all_feeds() if not feed.Paused]
        if not feeds:
            raise WorkHubError("还没有可同步的订阅源。")
        total = 0
        fails: list[str] = []
        for feed in feeds:
            ok, new_count, message = self._sync_core(feed)
            if ok:
                total += new_count
            else:
                fails.append(f"{feed.Title}：{message}")
        if not fails:
            return f"同步完成 · {len(feeds)} 个源，新增 {total} 条"
        raise WorkHubError(f"{len(feeds) - len(fails)} 个源成功，新增 {total} 条；{'；'.join(fails[:3])}")

    def toggle_pause(self, feed_id: str) -> str:
        feed = self._db.get(WhRssFeed, feed_id)
        if feed is None:
            raise WorkHubError("订阅源不存在。")
        feed.Paused = not feed.Paused
        self._save_feed(feed)
        return f"已暂停 {feed.Title}，「全部同步」会跳过它。" if feed.Paused else f"恢复订阅 {feed.Title}。"

    def delete_feed(self, feed_id: str) -> None:
        if not feed_id:
            return
        for item in [it for it in self._all_items() if it.FeedId == feed_id]:
            self._db.delete(item)
            self._db.commit()
            search_sync.drop(self._db, item.Id)
        feed = self._db.get(WhRssFeed, feed_id)
        if feed is not None:
            self._db.delete(feed)
            self._db.commit()

    # ---------- 条目操作 ----------

    def set_read(self, item_id: str, read: bool) -> str:
        item = self._db.get(WhRssItem, item_id)
        if item is None:
            raise WorkHubError("条目不存在。")
        item.Read = read
        self._save_item(item)
        return "标为已读。" if read else "恢复成未读。"

    def read_all(self, feed_id: str) -> str:
        items = [item for item in self._all_items() if item.FeedId == feed_id] if feed_id else self._all_items()
        n = 0
        for item in items:
            if not item.Read:
                item.Read = True
                self._save_item(item)
                n += 1
        return "本来就没有未读。" if n == 0 else f"清了 {n} 条未读。"

    def toggle_star(self, item_id: str) -> str:
        item = self._db.get(WhRssItem, item_id)
        if item is None:
            raise WorkHubError("条目不存在。")
        item.Starred = not item.Starred
        if item.Starred:
            item.Read = True
        self._save_item(item)
        return f"记下了《{item.Title}》。" if item.Starred else "取消收藏。"

    def delete_item(self, item_id: str) -> str:
        item = self._db.get(WhRssItem, item_id)
        if item is None:
            raise WorkHubError("条目不存在。")
        self._db.delete(item)
        self._db.commit()
        search_sync.drop(self._db, item_id)
        return f"已删掉《{item.Title}》。"

    def clip(self, item_id: str) -> str:
        from app.common.html_clipper import clip, save_snapshot

        item = self._db.get(WhRssItem, item_id)
        if item is None:
            raise WorkHubError("条目不存在。")
        if not (item.Url or "").strip():
            raise WorkHubError("这条没有链接，剪不了。")
        try:
            result = clip(item.Url, client=self._http)
            bookmark = WhBookmark(
                Title=result.title, Url=item.Url, Site=result.site, Summary=result.summary,
                Content=result.content, Snapshot=save_snapshot(self._storage, result.html),
                Status="unread", CreateBy=LOCAL, CreateTime=now(),
            )
            self._db.add(bookmark)
            self._db.commit()
            search_sync.sync(self._db, search_sync.BOOKMARK, bookmark.Id)
            item.Read = True
            self._save_item(item)
            return "已存进「我的收藏」。"
        except WorkHubError:
            raise
        except Exception as exc:
            raise WorkHubError(f"抓正文失败：{exc}") from exc

    # ---------- 内部 ----------

    def _all_feeds(self) -> list[WhRssFeed]:
        return list(self._db.execute(select(WhRssFeed)).scalars().all())

    def _all_items(self) -> list[WhRssItem]:
        return list(self._db.execute(select(WhRssItem)).scalars().all())

    def _save_feed(self, feed: WhRssFeed) -> None:
        tracked = self._db.get(WhRssFeed, feed.Id)
        if tracked is None:
            return
        tracked.Title = feed.Title
        tracked.SiteUrl = feed.SiteUrl
        tracked.Description = feed.Description
        tracked.ETag = feed.ETag
        tracked.Paused = feed.Paused
        tracked.LastFetchAt = now()
        tracked.LastError = feed.LastError
        tracked.ModifyBy = LOCAL
        tracked.ModifyTime = now()
        self._db.add(tracked)
        self._db.commit()

    def _save_item(self, item: WhRssItem) -> None:
        item.ModifyBy = LOCAL
        item.ModifyTime = now()
        self._db.add(item)
        self._db.commit()

    def _sync_core(self, feed: WhRssFeed) -> tuple[bool, int, str]:
        body, etag = self._fetch(feed)
        if body is None:
            self._fail(feed, "没抓到内容（网络不通、被挡了，或地址不是 feed）。")
            return False, 0, "没抓到内容（网络不通、被挡了，或地址不是 feed）。"
        if body == "":
            feed.ETag = etag or feed.ETag
            self._save_feed(feed)
            return True, 0, "没有变化"

        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            self._fail(feed, "不是合法的 XML，可能地址指向的是网页。")
            return False, 0, "不是合法的 XML，可能地址指向的是网页。"

        parsed = self._parse_items(root, feed.Id)
        channel_title, channel_site, channel_desc = self._read_channel(root)

        if not parsed:
            self._fail(feed, "解析成功但一条都没有，可能这个 feed 只给了索引。")
            return False, 0, "解析成功但一条都没有，可能这个 feed 只给了索引。"

        known = [item for item in self._all_items() if item.FeedId == feed.Id]
        seen = {_key_of(item) for item in known if _key_of(item)}

        added = 0
        for item in parsed:
            key = _key_of(item)
            if not key or key in seen:
                continue
            seen.add(key)
            item.CreateBy = LOCAL
            item.CreateTime = now()
            self._db.add(item)
            self._db.commit()
            search_sync.sync(self._db, search_sync.RSS, item.Id)
            added += 1

        # 裁掉太老的
        current = sorted(
            [item for item in self._all_items() if item.FeedId == feed.Id],
            key=lambda item: item.PublishedAt or item.CreateTime or now(),
            reverse=True,
        )
        for old in current[_KEEP_ITEMS:]:
            self._db.delete(old)
            self._db.commit()
            search_sync.drop(self._db, old.Id)

        if channel_title and channel_title.strip():
            feed.Title = _shorten(channel_title, 300)
        if _is_page_url(channel_site):
            feed.SiteUrl = _shorten(channel_site, 1000)
        if channel_desc and channel_desc.strip():
            feed.Description = _shorten(channel_desc, 1000)
        feed.ETag = etag or feed.ETag
        feed.LastError = None
        self._save_feed(feed)
        return True, added, f"{added} 条"

    def _fail(self, feed: WhRssFeed, message: str) -> None:
        feed.LastError = _shorten(message, 500)
        self._save_feed(feed)

    def _fetch(self, feed: WhRssFeed) -> tuple[str | None, str | None]:
        try:
            headers = {"User-Agent": _UA, "Accept": _ACCEPT}
            if feed.ETag:
                headers["If-None-Match"] = feed.ETag
            resp = self._http.get(feed.Url, headers=headers)
            if resp.status_code == 304:
                return "", feed.ETag
            if resp.status_code >= 400:
                return None, None
            return resp.text, resp.headers.get("etag")
        except httpx.HTTPError:
            return None, None

    def _resolve_feed(self, url: str) -> tuple[str | None, str | None]:
        try:
            resp = self._http.get(url, headers={"User-Agent": _UA, "Accept": _ACCEPT})
            if resp.status_code >= 400:
                return None, f"HTTP {resp.status_code}"
            body = resp.text
        except httpx.HTTPError as exc:
            return None, f"连不上 {self._host(url)}：{exc}"

        if _is_feed(body):
            return url, None

        try:
            doc = lhtml.fromstring(body)
        except Exception:
            doc = None
        if doc is not None:
            for node in doc.xpath("//link[@rel and @href]"):
                rel = (node.get("rel") or "").lower()
                type_ = (node.get("type") or "").lower()
                if rel == "alternate" and ("rss" in type_ or "atom" in type_ or "xml" in type_):
                    return _abs(node.get("href") or "", url), None

        for path in _GUESS_PATHS:
            candidate = _abs(path, url)
            if candidate and self._probe(candidate) is not None:
                return candidate, None

        return None, "既不是 feed，页面里也没找到订阅链接（RSS/Atom）。把 feed.xml 的完整地址贴进来试试。"

    def _probe(self, url: str) -> str | None:
        try:
            resp = self._http.get(url, headers={"User-Agent": _UA, "Accept": _ACCEPT})
            if resp.status_code >= 400:
                return None
            return resp.text if _is_feed(resp.text) else None
        except httpx.HTTPError:
            return None

    # ---------- 解析 ----------

    def _read_channel(self, root) -> tuple[str, str, str]:
        channel = _pick(root, "channel")
        if channel is None:
            channel = root
        desc_el = _pick(channel, "description")
        if desc_el is None:
            desc_el = _pick(root, "subtitle")
        return (
            _text(_pick(channel, "title")) or "",
            _link_of(_pick(channel, "link")) or "",
            _text(desc_el) or "",
        )

    def _parse_items(self, root, feed_id: str) -> list[WhRssItem]:
        items: list[WhRssItem] = []
        for el in root.iter():
            if _local(el.tag) not in ("item", "entry"):
                continue
            title = _text(_pick(el, "title")) or "（无标题）"
            items.append(WhRssItem(
                FeedId=feed_id,
                Title=_shorten(title, 500),
                Url=_shorten(_link_of(_pick(el, "link")) or _text(_pick(el, "link")) or "", 1000),
                Guid=_shorten(_text(_pick_any(el, "guid", "id")) or _link_of(_pick(el, "link")) or "", 300),
                Author=_shorten(_author_of(el) or "", 200),
                Summary=_shorten(_plaintext(_text(_pick_any(el, "content", "encoded", "summary", "description"))) or "", 2000),
                PublishedAt=_date_of(_pick_any(el, "pubDate", "published", "updated")),
            ))
        # 去重：item 与 entry 可能被 root.iter 重复命中（嵌套），按对象去重
        return items


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _pick(parent, local_name: str):
    if parent is None:
        return None
    for child in parent:
        if _local(child.tag) == local_name:
            return child
    return None


def _pick_any(parent, *local_names: str):
    """按名字依次取第一个存在的子元素（不依赖元素真值判断）。"""
    if parent is None:
        return None
    for name in local_names:
        child = _pick(parent, name)
        if child is not None:
            return child
    return None


def _text(el) -> str | None:
    if el is None or not (el.text or "").strip():
        return None
    return el.text.strip()


def _link_of(link) -> str | None:
    if link is None:
        return None
    text = _text(link)
    if text and text.strip():
        return text
    alt = next((child for child in link if (child.get("rel") or "") == "alternate"), link)
    return alt.get("href")


def _author_of(el) -> str | None:
    direct = _text(_pick(el, "creator"))
    if direct:
        return direct
    author = _pick(el, "author")
    if author is None:
        return None
    return _text(_pick(author, "name")) or _text(author)


def _date_of(el) -> datetime | None:
    from email.utils import parsedate_to_datetime

    text = _text(el)
    if text is None:
        return None
    # RFC 2822（RSS 的 pubDate）
    try:
        return parsedate_to_datetime(text).replace(tzinfo=None)
    except (TypeError, ValueError):
        pass
    # ISO 8601（Atom 的 published/updated）
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _plaintext(html: str | None) -> str | None:
    if not html or not html.strip():
        return None
    try:
        doc = lhtml.fromstring(html)
        text = "".join(doc.itertext())
    except Exception:
        text = html
    import html as _h

    return _SPACES.sub(" ", _h.unescape(text)).strip()


def _is_feed(text: str) -> bool:
    if not text or not text.strip():
        return False
    head = text.lstrip("﻿ \t\r\n")[:4000]
    return "<rss" in head or "<feed" in head or "<rdf:RDF" in head


def _is_page_url(url: str) -> bool:
    if not url or not url.strip():
        return False
    path = urlsplit(url).path.rstrip("/")
    return (
        len(path) <= 1
        or not (path.endswith(".atom") or path.endswith(".xml") or path.endswith("/rss")
                or path.endswith("/feed") or "/rss/" in path)
    )


def _abs(href: str, base: str) -> str | None:
    if not href or not href.strip():
        return None
    try:
        return urljoin(base, href)
    except ValueError:
        return href


def _host(url: str) -> str:
    try:
        return urlsplit(url).hostname or url
    except ValueError:
        return url


def _shorten(text: str, limit: int) -> str:
    return text if not text or len(text) <= limit else text[:limit]


def _key_of(item: WhRssItem) -> str:
    """判重键：feed 给的 guid 优先，没有就用链接。"""
    return (item.Guid or "").strip() or (item.Url or "").strip()
