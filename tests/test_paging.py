"""分页夹取与关键字过滤片段。

移植自 WorkHub.Tests/WritingQueryTests.cs 的分页部分。
文章 / 笔记的 SQL 形状断言随那两张表进阶段 2。
"""

from __future__ import annotations

import pytest

from app.core.paging import INT_MAX, clamp_paging, keyword_condition


@pytest.mark.parametrize(
    ("page_index", "page_size", "expected"),
    [
        (1, 20, (1, 20)),
        (3, 25, (3, 25)),
        (0, 0, (1, 1)),
        (-1, -1, (1, 1)),
        (-(2**31), -(2**31), (1, 1)),
        (1, 100, (1, 100)),
        (2, 101, (2, 100)),
        (2, INT_MAX, (2, 100)),
        (INT_MAX, 1, (INT_MAX, 1)),
        (INT_MAX, 2, (1073741824, 2)),
        (21474837, 100, (21474837, 100)),
        (21474838, 100, (21474837, 100)),
        (INT_MAX, INT_MAX, (21474837, 100)),
    ],
)
def test_clamp_paging(page_index, page_size, expected):
    assert clamp_paging(page_index, page_size) == expected


def test_clamp_paging_clamps_size_first():
    """pageSize 先夹到 [1,100]，pageIndex 再按 size 算上限——顺序不能换。"""
    index, size = clamp_paging(2, 101)
    assert size == 100
    assert index == 2


def test_keyword_condition_uses_instr_not_like():
    condition = keyword_condition(["Title", "Content"])
    assert "like" not in condition.lower()
    assert "instr(lower(coalesce(Title,'')),lower(@kw)) > 0" in condition
    assert " or " in condition


def test_keyword_condition_single_column_has_no_outer_parentheses():
    condition = keyword_condition(["Title"])
    assert condition == "instr(lower(coalesce(Title,'')),lower(@kw)) > 0"
