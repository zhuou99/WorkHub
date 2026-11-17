"""运行错误的文本收敛规则。

对应 C# 的 WorkHub/Common/ErrorLogRules.cs。

消息截 300、详情截 4000：异常堆栈动辄上千行，原样入库会把库迅速撑大；
截断后仍保留「发生在哪、什么类型」，需要完整堆栈时再翻日志文件。
"""

from __future__ import annotations

__all__ = ["trim", "title"]


def trim(value: str | None, limit: int) -> str | None:
    """收敛到 limit 个字符，超长时截断并追加「…」（因此结果最长是 limit + 1）。

    None / 空串原样返回；limit 非正时只保留「…」这一截断标记。
    """
    if not value:
        return value
    n = max(0, limit)
    return value if len(value) <= n else value[:n] + "…"


def title(ex: BaseException | None) -> str:
    """一句话标题：异常类型 + 消息首行。

    不展开内部异常——完整链条由 traceback 写进详情。
    """
    if ex is None:
        return "未知错误"
    type_name = type(ex).__name__
    first = _first_line(str(ex))
    return type_name if not first else f"{type_name}: {first}"


def _first_line(message: str | None) -> str | None:
    if not message:
        return None
    return message.split("\r")[0].split("\n")[0].strip()
