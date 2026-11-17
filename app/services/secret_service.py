"""密钥管理：对应 C# 的 WorkHub/Services/SecretService.cs。

只暴露「有哪些、能不能解、录入/清除」，不提供任何取明文的口子。
"""

from __future__ import annotations

from app.common.exceptions import WorkHubError
from app.common.secrets import PREFIX, remove_secret, set_secret
from app.services.audit_service import AuditService
from app.services.config_service import ConfigStore

__all__ = ["SecretService"]

_CATALOG = (
    ("baidu.appid", "百度翻译 AppID", "工具箱「翻译」", "如 1234567890123456", True),
    ("baidu.secret", "百度翻译密钥", "工具箱「翻译」", "密钥串，只加密存本机", True),
    ("github.token", "GitHub Token", "开源项目拉取额度（可选，不填用匿名额度 60 次/小时）", "ghp_… / github_pat_…", False),
)


class SecretService:
    def __init__(self, config: ConfigStore, audit: AuditService, protector):
        self._config = config
        self._audit = audit
        self._protector = protector

    def get_all(self) -> list[dict]:
        result = []
        for key, name, usage, placeholder, required in _CATALOG:
            encrypted = self._config.get(PREFIX + key)
            plain = self._protector.unprotect(encrypted) if encrypted else ""
            result.append({
                "key": key,
                "name": name,
                "usage": usage,
                "placeholder": placeholder,
                "required": required,
                "configured": bool(encrypted),
                "readable": bool(encrypted) and bool(plain),
                "masked": _mask(plain),
            })
        return result

    def set(self, key: str, value: str) -> str:
        definition = next((item for item in _CATALOG if item[0] == key), None)
        if definition is None:
            raise WorkHubError("未知的密钥项。")
        if not (value or "").strip():
            raise WorkHubError("内容不能为空。")
        set_secret(self._config, self._protector, key, value)
        self._audit.write("settings", "secret-set", True, f"{definition[1]}已加密保存")
        return f"{definition[1]}已加密保存。"

    def remove(self, key: str) -> str:
        definition = next((item for item in _CATALOG if item[0] == key), None)
        if definition is None:
            raise WorkHubError("未知的密钥项。")
        # 必需项也允许清除：清掉只是让翻译功能回到「未配置」提示
        remove_secret(self._config, key)
        self._audit.write("settings", "secret-remove", True, f"已清除{definition[1]}")
        return f"已清除{definition[1]}。"


def _mask(plain: str) -> str:
    """掩码：留头 2 位与后 2 位方便辨认是哪把钥匙，中间打点。"""
    if not plain:
        return ""
    if len(plain) <= 6:
        return "•" * len(plain)
    return f"{plain[:2]}{'•' * min(12, len(plain) - 4)}{plain[-2:]}"
