"""ULID：26 位、Crockford 字母表、同毫秒单调递增、时间可解回。

移植自 WorkHub.Tests/UlidTests.cs。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.common.exceptions import InvalidOperationException
from app.common.ulid import ALPHABET, decode_time, monotonic


def test_monotonic_produces_sortable_ids():
    previous = ""
    for i in range(100):
        id_ = monotonic()
        assert len(id_) == 26
        assert all(ch in ALPHABET for ch in id_)
        assert previous < id_, f"第 {i + 1} 个 ULID 未递增：{previous} → {id_}"
        previous = id_


def test_decode_time_returns_generation_moment():
    id_ = monotonic()
    before = datetime.now(UTC) - timedelta(seconds=2)
    decoded = decode_time(id_)
    after = datetime.now(UTC) + timedelta(seconds=2)
    assert before <= decoded <= after


def test_decode_time_rejects_wrong_length():
    with pytest.raises(InvalidOperationException) as exc:
        decode_time("ABC")
    assert "26 位" in str(exc.value)


def test_decode_time_rejects_illegal_character():
    # DecodeTime 只解码前 10 位时间戳，非法字符要放在这一段才会被校验
    bad = "I" + "0" * 25
    with pytest.raises(InvalidOperationException) as exc:
        decode_time(bad)
    assert "Crockford" in str(exc.value)


def test_monotonic_increments_across_full_80_bits():
    """随机部分整体 +1：最后一位必须严格前进，不能只加末位 base32 数字。"""
    ids = [monotonic() for _ in range(500)]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
