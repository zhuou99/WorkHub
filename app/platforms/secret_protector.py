"""外部服务密钥的加解密：对应 C# 的 ISecretProtector。

C# 走 Windows DPAPI（当前用户范围）；Python 侧用 Fernet 对称加密，
密钥首次启动生成后存进 SysConfig——换机器后自然解不开，语义与 DPAPI 对齐。
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

__all__ = ["SecretProtector"]


class SecretProtector:
    def __init__(self, key: str | None):
        self._fernet = Fernet(key.encode("ascii")) if key else None

    @staticmethod
    def new_key() -> str:
        return Fernet.generate_key().decode("ascii")

    def protect(self, plain: str) -> str:
        """明文入参，落库前加密。"""
        if self._fernet is None or not plain:
            return ""
        return self._fernet.encrypt(plain.encode("utf-8")).decode("ascii")

    def unprotect(self, encrypted: str | None) -> str:
        """解密；失败（换机器、密文损坏）返回空串，由调用方提示重新录入。"""
        if not encrypted or self._fernet is None:
            return ""
        try:
            return self._fernet.decrypt(encrypted.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeDecodeError):
            return ""
