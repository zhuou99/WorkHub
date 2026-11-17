"""统一响应信封。

C# 那边所有 [WebApi] 契约都返回 Known.Result（{ code, message, data }）或
Known.PagingResult（多一个 total 与 rows）。这里沿用同样的形状，
但 HTTP 状态码用真实状态码：业务失败 400、未登录 401、角色不足 403。
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

__all__ = ["Result", "PagingResult"]


class Result(BaseModel, Generic[T]):
    """成功与业务失败共用一个信封。"""

    code: int = 200
    message: str = ""
    data: T | None = None


class PagingResult(BaseModel, Generic[T]):
    """分页结果。"""

    code: int = 200
    message: str = ""
    total: int = 0
    rows: list[T] = []
