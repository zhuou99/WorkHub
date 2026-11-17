"""工具执行入口：按工具 id 分派到 io 工具或面板工具。

放在 toolbox 层而不是 HTTP 层，是为了能脱离 FastAPI 单测。
"""

from __future__ import annotations

from typing import Any

from app.common.exceptions import WorkHubError
from app.toolbox import panels
from app.toolbox.catalog import ToolDef, get

__all__ = ["ToolRunResult", "run_tool"]


class ToolRunResult(dict):
    """工具执行结果：文本输出 + 结构化数据。"""


def run_tool(tool_id: str, text: str = "", option: str = "", params: dict[str, Any] | None = None) -> ToolRunResult:
    """执行一个工具。

    io 工具用 (text, option)；面板工具用 params。
    """
    tool: ToolDef | None = get(tool_id)
    if tool is None:
        raise WorkHubError(f"没有这个工具：{tool_id}")

    values = params or {}

    if tool.kind == "io":
        if tool.run is None:
            raise WorkHubError(f"工具 {tool_id} 缺少执行逻辑。")
        return ToolRunResult(output=tool.run(text, option), data=None)

    return _run_panel(tool_id, values)


def _run_panel(tool_id: str, values: dict[str, Any]) -> ToolRunResult:
    if tool_id == "unit":
        data = panels.unit_convert(
            str(values.get("groupId") or "data"),
            str(values.get("fromId") or ""),
            values.get("value", 0),
        )
        return ToolRunResult(output="", data=data)

    if tool_id == "regex":
        data = panels.regex_test(
            str(values.get("pattern") or ""),
            str(values.get("subject") or ""),
            bool(values.get("ignoreCase")),
            bool(values.get("multiline")),
        )
        return ToolRunResult(output="", data=data)

    if tool_id == "diff":
        data = panels.diff_text(str(values.get("left") or ""), str(values.get("right") or ""))
        return ToolRunResult(output="", data=data)

    if tool_id == "count":
        data = panels.count_text(str(values.get("text") or ""))
        return ToolRunResult(output="", data=data)

    if tool_id == "hmac":
        output = panels.hmac_sign(str(values.get("key") or ""), str(values.get("data") or ""))
        return ToolRunResult(output=output, data=None)

    if tool_id == "guid":
        data = panels.guid_batch(
            int(values.get("count") or 5),
            str(values.get("format") or "D"),
            bool(values.get("upper")),
        )
        return ToolRunResult(output="", data=data)

    if tool_id == "password":
        data = panels.password_batch(
            int(values.get("length") or 16),
            int(values.get("count") or 5),
            bool(values.get("lower", True)),
            bool(values.get("upper", True)),
            bool(values.get("digit", True)),
            bool(values.get("symbol", False)),
            bool(values.get("noConfuse", True)),
        )
        return ToolRunResult(output="", data=data)

    if tool_id == "qr":
        data = panels.qr_code(
            str(values.get("value") or ""),
            str(values.get("mode") or "qr"),
            str(values.get("format") or "code128"),
            str(values.get("ecc") or "M"),
        )
        return ToolRunResult(output="", data=data)

    if tool_id == "color":
        data = panels.color_convert(values.get("hex"), values.get("rgb"))
        return ToolRunResult(output="", data=data)

    if tool_id == "translate":
        raise WorkHubError("翻译能力在阶段 2 启用（要接百度翻译与术语表）。")

    raise WorkHubError(f"工具 {tool_id} 还没有实现。")
