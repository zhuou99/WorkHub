"""导出与发布留痕：对应 C# 的 WorkHub/Services/PublishService.cs。

博客园走 Markdown 粘贴，公众号走内联样式 HTML，均不调任何平台 API。
"""

from __future__ import annotations

import re

import markdown as _markdown
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import WhPublishLog
from app.services.crud import LOCAL, now

__all__ = ["PublishService"]


class PublishService:
    def __init__(self, session: Session):
        self._db = session

    def cnblogs_markdown(self, article) -> str:
        """博客园导出：front-matter 注释 + 标题 + 摘要 + 正文。"""
        lines = ["<!--", f"title: {article.Title}"]
        if (article.Summary or "").strip():
            lines.append(f"summary: {article.Summary}")
        if (article.Tags or "").strip():
            lines.append(f"tags: {article.Tags}")
        lines.append(f"date: {now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("-->")
        lines.append("")
        lines.append(f"# {article.Title}")
        lines.append("")
        if (article.Summary or "").strip():
            lines.append(f"> {article.Summary}")
            lines.append("")
        lines.append(article.Content or "")
        return "\n".join(lines)

    def wechat_html(self, article) -> str:
        """公众号导出：Markdown 渲染成 HTML 后逐标签注入内联样式。"""
        body = _inline_styles(_markdown.markdown(article.Content or ""))
        out = [
            '<section style="font-family:-apple-system,BlinkMacSystemFont,\'Helvetica Neue\','
            "'PingFang SC','Microsoft YaHei',sans-serif;"
            'font-size:16px;line-height:1.75;color:#3f3f3f;letter-spacing:.5px;word-break:break-word;">',
            '<h1 style="font-size:22px;font-weight:700;line-height:1.4;margin:0 0 12px;color:#262626;">'
            f"{_escape_text(article.Title)}</h1>",
        ]
        if (article.Summary or "").strip():
            out.append('<p style="margin:0 0 20px;font-size:14px;color:#888;line-height:1.6;">'
                       f"{_escape_text(article.Summary)}</p>")
        if (article.Cover or "").strip():
            out.append('<p style="margin:0 0 20px;text-align:center;"><img src="'
                       f'{_escape_attr(article.Cover)}" alt="" '
                       'style="max-width:100%;display:block;margin:0 auto;border-radius:6px;" /></p>')
        out.append(body)
        out.append("</section>")
        return "".join(out)

    def log(self, article, channel: str, result: str, detail: str | None) -> None:
        self._db.add(WhPublishLog(
            ArticleId=getattr(article, "Id", None),
            ArticleTitle=getattr(article, "Title", None),
            Channel=channel,
            Result=result,
            Detail=detail[:500] if detail and len(detail) > 500 else detail,
            CreateBy=LOCAL,
            CreateTime=now(),
        ))
        self._db.commit()

    def get_all_logs(self) -> list[WhPublishLog]:
        rows = list(self._db.execute(select(WhPublishLog)).scalars().all())
        return sorted(rows, key=lambda item: item.CreateTime or now(), reverse=True)

    def clear_logs(self) -> None:
        for log in list(self._db.execute(select(WhPublishLog)).scalars().all()):
            self._db.delete(log)
        self._db.commit()

    def delete_log(self, log_id: str) -> None:
        log = self._db.get(WhPublishLog, log_id)
        if log is not None:
            self._db.delete(log)
            self._db.commit()


_TAG_STYLES = {
    "h1": "font-size:22px;font-weight:700;line-height:1.4;margin:24px 0 12px;color:#262626;",
    "h2": "font-size:20px;font-weight:700;line-height:1.4;margin:28px 0 12px;padding-left:10px;border-left:4px solid #07c160;color:#262626;",
    "h3": "font-size:18px;font-weight:700;line-height:1.5;margin:24px 0 10px;color:#262626;",
    "h4": "font-size:16px;font-weight:700;line-height:1.5;margin:20px 0 8px;color:#262626;",
    "h5": "font-size:15px;font-weight:700;margin:16px 0 8px;color:#262626;",
    "h6": "font-size:14px;font-weight:700;margin:16px 0 8px;color:#595959;",
    "p": "margin:0 0 16px;",
    "blockquote": "margin:0 0 16px;padding:10px 14px;border-left:3px solid #07c160;background:#f7f7f7;color:#595959;font-size:15px;",
    "ul": "margin:0 0 16px;padding-left:24px;",
    "ol": "margin:0 0 16px;padding-left:24px;",
    "li": "margin:4px 0;",
    "table": "border-collapse:collapse;margin:0 0 16px;font-size:14px;width:100%;",
    "th": "border:1px solid #e0e0e0;padding:6px 10px;background:#f5f5f5;font-weight:700;",
    "td": "border:1px solid #e0e0e0;padding:6px 10px;",
    "a": "color:#576b95;text-decoration:none;border-bottom:1px solid #576b95;",
    "strong": "color:#262626;",
    "img": "max-width:100%;display:block;margin:12px auto;border-radius:6px;",
    "hr": "margin:24px 0;border:0;border-top:1px solid #e5e5e5;",
    "pre": "margin:0 0 16px;padding:12px 14px;background:#f7f7f7;border-radius:6px;overflow-x:auto;font-size:13px;line-height:1.6;white-space:pre-wrap;tab-size:4;",
    "code": "font-family:Menlo,Consolas,'Courier New',monospace;background:#f2f2f2;padding:2px 5px;border-radius:4px;font-size:13.6px;color:#c7254e;",
}

_OPEN_TAG = re.compile(
    r"<(h[1-6]|hr|p|blockquote|ul|ol|li|table|thead|tbody|tr|th|td|a|em|strong|del|code|pre|img|input)\b([^>]*?/?>)",
    re.IGNORECASE,
)


def _inline_styles(html: str) -> str:
    """把每个开标签补上内联 style；已有 style 则并到它前面。"""
    pres: list[tuple[int, int]] = []
    at = html.find("<pre")
    while at >= 0:
        close = html.find("</pre>", at)
        if close > at:
            pres.append((at, close))
        at = html.find("<pre", at + 4)

    def replace(match: re.Match) -> str:
        tag = match.group(1).lower()
        style = _TAG_STYLES.get(tag)
        if style is None:
            return match.group(0)
        if tag == "code":
            for i, (start, end) in enumerate(pres):
                if match.start() > start and match.start() < end:
                    style += "background:none;padding:0;color:inherit;"
                    pres.pop(i)
                    break

        attrs = match.group(2)[1:].rstrip(">/").strip()
        attrs = re.sub(r'class="[^"]*"', "", attrs).strip()
        if not attrs:
            return f'<{tag} style="{style}">'
        at_style = attrs.lower().find('style="')
        if at_style >= 0:
            return f'<{tag} {attrs[:at_style]}style="{style}{attrs[at_style + 7:]}'
        return f'<{tag} {attrs} style="{style}">'

    return _OPEN_TAG.sub(replace, html)


def _escape_text(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    return _escape_text(text).replace('"', "&quot;")
