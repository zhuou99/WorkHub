"""外部服务密钥的存取：对应 C# 的 WorkHub/Common/Secrets.cs。

明文交给 SecretProtector 加密后写进 SysConfig；明文读取只给进程内的服务调用，
绝不通过 HTTP 暴露出去。
"""

from __future__ import annotations

from app.services.config_service import ConfigStore

__all__ = ["PREFIX", "get_secret", "set_secret", "exists_secret", "remove_secret"]

#: SysConfig 键前缀，与业务配置隔开。
PREFIX = "secret."


def get_secret(config: ConfigStore, protector, key: str) -> str:
    """取明文密钥，未配置或解不开返回空串。"""
    return protector.unprotect(config.get(PREFIX + key))


def set_secret(config: ConfigStore, protector, key: str, plain: str) -> None:
    """写入密钥（明文入参，落库前加密）。"""
    config.set(PREFIX + key, protector.protect(plain))


def exists_secret(config: ConfigStore, key: str) -> bool:
    return config.exists(PREFIX + key)


def remove_secret(config: ConfigStore, key: str) -> None:
    config.delete(PREFIX + key)
