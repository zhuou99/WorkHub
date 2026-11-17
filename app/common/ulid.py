"""ULID：26 位 Crockford base32（前 10 位毫秒时间戳 + 后 16 位随机）。

对应 C# 的 WorkHub/Common/Ulid.cs。

同一毫秒内保证递增：随机部分整体 +1，这样一批 ID 的字符串序等于时间序——
只加最后一位会在进位时破掉这个性质。
"""

from __future__ import annotations

import secrets
import threading
import time
from datetime import UTC, datetime

from app.common.exceptions import InvalidOperationException

__all__ = ["ALPHABET", "monotonic", "decode_time"]

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

_gate = threading.Lock()
_last_ms = -1
_last_random = 0


def _random_80bit() -> int:
    return secrets.randbits(80)


def _encode(ms: int, random: int) -> str:
    chars = [""] * 26
    chars[0] = ALPHABET[(ms >> 45) & 7]
    for i in range(1, 10):
        chars[i] = ALPHABET[(ms >> (45 - 5 * i)) & 31]
    for i in range(16):
        chars[10 + i] = ALPHABET[(random >> (75 - 5 * i)) & 31]
    return "".join(chars)


def monotonic() -> str:
    """同一毫秒内保证递增的 ULID；时间回拨时按上一毫秒继续递增，不让序乱掉。"""
    global _last_ms, _last_random
    with _gate:
        ms = int(time.time() * 1000)
        if ms <= _last_ms:
            ms = _last_ms
        random = _last_random + 1 if ms == _last_ms else _random_80bit()
        _last_ms = ms
        _last_random = random
        return _encode(ms, random)


def decode_time(ulid: str | None) -> datetime:
    """解出 ULID 里的时间戳（UTC）；非法输入抛中文提示。

    只校验前 10 位——后 16 位是随机数，不参与时间判定。
    """
    if ulid is None or not ulid.strip() or len(ulid) != 26:
        raise InvalidOperationException(f"ULID 应该是 26 位，当前 {len(ulid) if ulid is not None else 0} 位。")
    ms = 0
    for i in range(10):
        value = ALPHABET.find(ulid[i].upper())
        if value < 0:
            raise InvalidOperationException(f"第 {i + 1} 位「{ulid[i]}」不在 Crockford base32 字母表内。")
        ms = (ms << 5) | (value & 31)
    return datetime.fromtimestamp(ms / 1000, tz=UTC)
