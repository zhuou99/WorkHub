"""SysConfig KV 存取。

对应 Known 的 db.GetConfigAsync / SaveConfigAsync：永远按 AppId="WorkHub" 作用域读写。
值是 JSON 字符串，键名与 C# 那边完全一致，方便直接读老库。
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.sysconfig import SysConfig

__all__ = ["ConfigStore", "pick"]


class ConfigStore:
    """SysConfig 的读写门面。"""

    APP_ID = "WorkHub"

    def __init__(self, session: Session):
        self._session = session

    def get(self, key: str) -> str | None:
        row = self._session.execute(
            select(SysConfig.ConfigValue).where(
                SysConfig.AppId == self.APP_ID,
                SysConfig.ConfigKey == key,
            )
        ).first()
        return row[0] if row else None

    def set(self, key: str, value: str | None) -> None:
        """写入（不存在则插入，存在则更新）。"""
        existing = self._session.get(SysConfig, (self.APP_ID, key))
        if existing is not None:
            existing.ConfigValue = value
        else:
            self._session.add(SysConfig(AppId=self.APP_ID, ConfigKey=key, ConfigValue=value))
        self._session.commit()

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> None:
        self._session.execute(
            delete(SysConfig).where(
                SysConfig.AppId == self.APP_ID,
                SysConfig.ConfigKey == key,
            )
        )
        self._session.commit()

    def get_json(self, key: str, default: Any = None) -> Any:
        """读 JSON。值坏了或读不出来就返回默认值——读配置失败不该把登录挡住。"""
        raw = self.get(key)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return default

    def set_json(self, key: str, value: Any) -> None:
        """写 JSON。键名保持原样（PascalCase），与 C# 侧 Utils.ToJson 的形状一致。"""
        self.set(key, json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def pick(data: dict, *names: str, default: Any = None) -> Any:
    """按多个候选键名取值（大小写都试）。

    C# 那边写进 SysConfig 的 JSON 是 PascalCase（{"Failures":0,"LockedUntil":null}），
    旧数据要能读懂，所以读取时大小写都认。
    """
    if not isinstance(data, dict):
        return default
    for name in names:
        if name in data:
            return data[name]
    lowered = {str(key).lower(): value for key, value in data.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return default
