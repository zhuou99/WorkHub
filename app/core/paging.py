"""分页夹取与关键字过滤片段。

对应 C# 那边 Known.Data.PagingCriteria 的口径：
pageSize 先夹到 [1, 100]，pageIndex 再夹到 [1, int.MaxValue // pageSize + 1]。
顺序不能换——先夹 pageSize 才得到正确的页数上限。
"""

from __future__ import annotations

__all__ = ["INT_MAX", "clamp_paging", "keyword_condition"]

INT_MAX = 2**31 - 1


def clamp_paging(page_index: int, page_size: int) -> tuple[int, int]:
    """返回 (page_index, page_size)。"""
    size = min(100, max(1, int(page_size)))
    index = min(INT_MAX // size + 1, max(1, int(page_index)))
    return index, size


def keyword_condition(columns: list[str], parameter: str = "@kw") -> str:
    """关键字过滤片段：instr(lower(coalesce(Col,'')), lower(@kw)) > 0。

    不用 LIKE——关键字里的 % 与 _ 会被当成通配符。
    关键字原样绑定，不 trim、不转义、不拼进 SQL 文本。
    """
    parts = [f"instr(lower(coalesce({column},'')),lower({parameter})) > 0" for column in columns]
    return "(" + " or ".join(parts) + ")" if len(parts) > 1 else parts[0]
