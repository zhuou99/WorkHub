"""PBKDF2-SHA256 口令散列：随机盐 16B、10 万次迭代，存储格式 base64(salt).base64(key)。

对应 C# 的 WorkHub/Common/Hasher.cs。旧库的散列格式一致，可以直接拿来校验。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os

__all__ = ["ITERATIONS", "hash_password", "verify_password"]

ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """生成新散列。"""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=32)
    return f"{base64.b64encode(salt).decode('ascii')}.{base64.b64encode(key).decode('ascii')}"


def verify_password(password: str, stored: str | None) -> bool:
    """校验口令。散列格式不对一律当作不通过，不抛异常。"""
    if not stored:
        return False
    parts = stored.split(".", 1)
    if len(parts) != 2:
        return False
    try:
        salt = base64.b64decode(parts[0], validate=True)
        key = base64.b64decode(parts[1], validate=True)
    except (binascii.Error, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=len(key))
    return hmac.compare_digest(actual, key)
