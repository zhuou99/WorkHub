"""会话：签名 Cookie。

C# 那边用的是 Known 的 AuthProvider（同源 Cookie 会话），这里用 itsdangerous 复刻：
cookie 只带用户 Id，**每个请求都重读 wh_user 行**——
禁用账号、删账号、改角色立刻生效，JWT 做不到这一点。

会话密钥首次启动时随机生成，存进 SysConfig[workhub.session.key]：
重启不失效，换机器自然失效，也不用写进 .env。
"""

from __future__ import annotations

import base64
import os
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

__all__ = ["SessionManager"]

SALT = "workhub.session"


class SessionManager:
    """签发与校验会话 Cookie。"""

    def __init__(self, secret: str, cookie_name: str = "workhub_session", max_age: int = 43200, secure: bool = False):
        self._serializer = URLSafeTimedSerializer(secret, salt=SALT)
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.secure = secure

    @staticmethod
    def new_secret() -> str:
        """生成新的会话密钥（base64 编码的 32 字节随机数）。"""
        return base64.b64encode(os.urandom(32)).decode("ascii")

    def issue(self, user_id: str) -> str:
        """签发会话串。"""
        return self._serializer.dumps({"uid": user_id})

    def read(self, raw: str | None) -> str | None:
        """解析会话串；无效或过期返回 None。"""
        if not raw:
            return None
        try:
            payload: Any = self._serializer.loads(raw, max_age=self.max_age)
        except (BadSignature, SignatureExpired):
            return None
        if isinstance(payload, dict):
            uid = payload.get("uid")
            return uid if isinstance(uid, str) else None
        return None

    def set_cookie(self, response, user_id: str) -> None:
        response.set_cookie(
            key=self.cookie_name,
            value=self.issue(user_id),
            max_age=self.max_age,
            httponly=True,
            samesite="lax",
            secure=self.secure,
            path="/",
        )

    def clear_cookie(self, response) -> None:
        response.delete_cookie(key=self.cookie_name, path="/")
