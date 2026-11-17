"""异常处理：把各类错误统一渲染成 { code, message, data } 信封。

不用 FastAPI 默认的 {"detail": ...}，前端只要认一个信封。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.exceptions import WorkHubError

logger = logging.getLogger("workhub.error")

__all__ = ["register_exception_handlers"]


def _envelope(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None}


def register_exception_handlers(app: FastAPI) -> None:
    """把异常处理挂到 app 上。"""

    @app.exception_handler(WorkHubError)
    async def _business_error(request: Request, exc: WorkHubError):
        """纯逻辑层抛出的输入不合法：400，并把中文文案原样带回。"""
        return JSONResponse(status_code=400, content=_envelope(400, str(exc)))

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败。"
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc.status_code, detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", [])[1:]) or "请求体"
        message = f"{location}：{first.get('msg', '参数不合法。')}"
        return JSONResponse(status_code=422, content=_envelope(422, message))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        logger.exception("未处理异常 %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_envelope(500, "服务器处理失败，请查看 Logs 下的日志。"))
