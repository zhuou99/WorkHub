"""纯逻辑层抛出的异常。

C# 侧用 FormatException / InvalidOperationException 表达「输入不合法」，
这里沿用同样的类名：异常类型名会直接进入 wh_error.Message 与界面提示
（见 app/common/error_log_rules.py 的 title()），改名会让文案与旧库对不上。
"""


class WorkHubError(Exception):
    """业务错误基类：消息是给人看的中文文案。"""


class FormatException(WorkHubError):
    """对应 C# 的 FormatException：输入格式不对。"""


class InvalidOperationException(WorkHubError):
    """对应 C# 的 InvalidOperationException：状态或参数不允许。"""


__all__ = ["WorkHubError", "FormatException", "InvalidOperationException"]
