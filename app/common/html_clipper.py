"""网页快照与正文抽取：对应 C# 的 WorkHub/Common/HtmlClipper.cs。

抓一个链接 → 取标题/摘要/正文（HTML → Markdown）+ 原文快照。
正文抽取用 lxml（等价 HtmlAgilityPack），规则照搬原实现。
"""

from __future__ import annotations

import html as _html
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
from lxml import etree, html as lhtml

__all__ = ["ClipResult", "clip", "to_markdown", "pick_main", "visible_text"]

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_ACCEPT = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"

_DROP_TAGS = ("script", "style", "noscript", "iframe", "svg", "canvas", "form", "button",
              "nav", "header", "footer", "aside", "video", "audio", "picture", "figure")

_HTML_LIMIT = 1_000_000
_MD_LIMIT = 500_000
_SPACES = re.compile(r"\s+")


@dataclass
class ClipResult:
    title: str = ""
    site: str = ""
    summary: str | None = None
    content: str | None = None
    html: str = ""


def clip(url: str, client: httpx.Client | None = None) -> ClipResult:
    """抓取链接并抽取正文。失败抛异常由调用方提示。"""
    from app.common.exceptions import WorkHubError

    base = url.strip()
    if not base.startswith(("http://", "https://")):
        raise WorkHubError("链接不是合法的 http(s) 地址。")

    owns_client = client is None
    client = client or httpx.Client(timeout=15.0, follow_redirects=True)
    try:
        try:
            resp = client.get(base, headers={"User-Agent": _UA, "Accept": _ACCEPT})
        except httpx.HTTPError as exc:
            raise WorkHubError(f"抓取失败：{exc}") from exc
        if resp.status_code >= 400:
            raise WorkHubError(f"HTTP {resp.status_code}")

        raw = resp.text
        html_text = raw[:_HTML_LIMIT]
        final_url = str(resp.url) if resp.url else base

        tree = _parse(html_text)
        site = _host(final_url)

        title = _meta(tree, "og:title") or _first_text(tree, "//title")
        title = _truncate(_clean(title) or _host(final_url), 300)
        summary = _meta(tree, "og:description") or _meta(tree, "description", name=True)
        summary = _truncate(_clean(summary), 500) if summary else None
        content = to_markdown(pick_main(tree, final_url)) if tree is not None else None

        return ClipResult(title=title, site=site, summary=summary, content=content, html=html_text)
    finally:
        if owns_client:
            client.close()


def _parse(html_text: str):
    try:
        return lhtml.fromstring(html_text)
    except (etree.ParserError, ValueError):
        return None


def _host(url: str) -> str:
    from urllib.parse import urlsplit

    host = urlsplit(url).hostname or ""
    return host[4:] if host.lower().startswith("www.") else host


def _meta(tree, key: str, name: bool = False) -> str | None:
    if tree is None:
        return None
    if name:
        matches = tree.xpath(f"//meta[@name='{key}']/@content")
    else:
        matches = tree.xpath(f"//meta[@property='{key}']/@content")
    return matches[0] if matches else None


def _first_text(tree, xpath: str) -> str | None:
    if tree is None:
        return None
    matches = tree.xpath(xpath + "/text()")
    return matches[0] if matches else None


def save_snapshot(storage, html_text: str) -> str | None:
    """把原文快照存进附件根，返回站内地址；空白返回 None。"""
    if not html_text:
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"snapshot-{stamp}-{uuid.uuid4().hex[:12]}.html"
    return storage.save(name, html_text.encode("utf-8"))


# ---------- 正文抽取 ----------


def pick_main(root, base_uri: str):
    """选正文容器：优先语义标签与常见 id/class，其次取可见文本最长且不足全文 90% 的 div。"""
    if root is None:
        return None
    candidates = [
        root.xpath("//article"),
        root.xpath("//main"),
        root.xpath("//div[@id='content' or @id='article' or @id='main']"),
        root.xpath("//div[contains(@class,'article') or contains(@class,'post') or contains(@class,'content')]"),
    ]
    for group in candidates:
        for node in group:
            if len(visible_text(node)) > 200:
                return node

    root_len = len(visible_text(root))
    best = None
    best_len = 0
    for div in root.xpath("//div"):
        length = len(visible_text(div))
        if length < root_len * 0.9 and length > best_len:
            best_len = length
            best = div
    if best is not None:
        return best
    body = root.xpath("//body")
    return body[0] if body else root


def visible_text(node) -> str:
    """去掉导航/脚本后取可见文本（压平空白）。"""
    if node is None:
        return ""
    clone = _strip(node)
    text = "".join(clone.itertext())
    return _clean(_html.unescape(text).replace("\r", ""))


def _strip(node):
    """深拷贝并移除 DropTags。"""
    clone = lhtml.fromstring(etree.tostring(node))
    for tag in _DROP_TAGS:
        for el in clone.xpath(f"//{tag}"):
            el.getparent().remove(el)
    return clone


# ---------- HTML → Markdown ----------

_HEADINGS = {"h1": 2, "h2": 3, "h3": 4, "h4": 5, "h5": 6, "h6": 6}


def to_markdown(node) -> str:
    """HTML → Markdown。"""
    if node is None:
        return ""
    clone = _strip(node)
    out: list[str] = []
    _render_block(clone, out, 0)
    text = _squeeze_lines("".join(out))
    return text[:_MD_LIMIT]


def _render_block(node, out: list[str], depth: int) -> None:
    tag = node.tag if isinstance(node.tag, str) else ""
    if tag in _HEADINGS:
        level = min(_HEADINGS[tag], 6)
        out.append("\n" + "#" * level + " " + _inline(node) + "\n\n")
        return
    if tag == "p":
        out.append(_inline(node) + "\n\n")
        return
    if tag == "br":
        out.append("\n")
        return
    if tag == "hr":
        out.append("\n---\n\n")
        return
    if tag == "pre":
        code = node.xpath(".//code") or [node]
        text = _html.unescape("".join(code[0].itertext())).strip("\n")
        out.append("\n```\n" + text + "\n```\n\n")
        return
    if tag == "blockquote":
        inner = _squeeze_lines(_inline(node))
        for line in inner.splitlines():
            if line.strip():
                out.append("> " + line.strip() + "\n")
        out.append("\n")
        return
    if tag in ("ul", "ol"):
        for child in node:
            if not isinstance(child.tag, str):
                continue
            if child.tag == "li":
                marker = "- " if tag == "ul" else f"{_list_index(node, child)}. "
                out.append("  " * depth + marker + _inline(child) + "\n")
            elif child.tag in ("ul", "ol"):
                _render_block(child, out, depth + 1)
        out.append("\n")
        return
    if tag == "table":
        _render_table(node, out)
        return
    if tag in ("a", "strong", "b", "em", "i", "code", "span", "div", "section",
               "article", "main", "figure", "img"):
        _render_mixed(node, out)
        return
    _render_block_default(node, out)


def _render_block_default(node, out: list[str]) -> None:
    for child in node:
        if isinstance(child.tag, str):
            _render_block(child, out, 0)
        else:
            text = _clean(child)
            if text:
                out.append(text)


def _render_mixed(node, out: list[str]) -> None:
    tag = node.tag if isinstance(node.tag, str) else ""
    if tag == "img":
        src = node.get("data-src") or node.get("src") or ""
        alt = node.get("alt") or ""
        out.append(f"\n\n![{alt}]({_abs(src, None)})\n\n")
        return
    if tag == "a":
        label = _inline(node).strip()
        href = node.get("href") or ""
        if label and _abs(href, None):
            out.append(f"[{label}]({_abs(href, None)})")
        elif label:
            out.append(label)
        return
    if tag == "code":
        out.append("`" + _inline(node) + "`")
        return
    if tag in ("strong", "b"):
        out.append("**" + _inline(node) + "**")
        return
    if tag in ("em", "i"):
        out.append("*" + _inline(node) + "*")
        return
    # 其余：透传子节点
    for child in node:
        if isinstance(child.tag, str):
            _render_mixed(child, out)
        else:
            text = _clean(child)
            if text:
                out.append(text)
    if tag in ("div", "section", "article", "main", "figure", "span"):
        out.append("\n")


def _render_table(node, out: list[str]) -> None:
    rows = node.xpath(".//tr")
    for idx, tr in enumerate(rows):
        cells = ["".join(cell.itertext()).replace("|", "\\|").strip() for cell in tr.xpath("./th|./td")]
        out.append("| " + " | ".join(cells) + " |\n")
        if idx == 0:
            out.append("|" + " --- |" * len(cells) + "\n")


def _list_index(parent, li) -> int:
    index = 1
    for child in parent:
        if child is li:
            return index
        if isinstance(child.tag, str) and child.tag == "li":
            index += 1
    return index


def _inline(node) -> str:
    """取节点的纯文本并压平空白。"""
    text = "".join(node.itertext())
    return _html.unescape(_clean(text))


def _abs(url: str, base: str | None) -> str | None:
    """空白或 data: 地址返回 None；否则解析成绝对地址。"""
    if not url or url.startswith("data:"):
        return None
    if base:
        return urljoin(base, url)
    return url


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return _SPACES.sub(" ", _html.unescape(text).replace("\r", " ").replace("\n", " ")).strip()


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def _squeeze_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def one_line(text: str | None) -> str:
    """压平空白成单行（检索上下文与索引共用）。"""
    if not text:
        return ""
    return _SPACES.sub(" ", text).strip()
