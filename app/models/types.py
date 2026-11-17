"""列类型：把 .NET 的存储口径搬到 Python 侧。

三个要点：
- 金额列在库里存 REAL（与旧库一致，float(Decimal("56.60")) == 56.6，存进去的字节相同），
  但 Python 侧一律拿到 Decimal，精度由领域层的 Decimal 运算与银行家舍入保证。
- datetime 列在库里存 TEXT（与旧库一致），Python 侧拿到 datetime。
- bool 列在库里存 INTEGER（与旧库一致），Python 侧拿到 bool。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Float, Integer, Text
from sqlalchemy.types import TypeDecorator


class Real(Float):
    """DDL 里写 REAL 而不是 FLOAT —— 与旧库逐字一致（亲和性相同，都是 REAL 亲和）。"""

    __visit_name__ = "REAL"


class DecimalAsFloat(TypeDecorator):
    """Decimal ↔ REAL。库里是 float，Python 侧是 Decimal。"""

    impl = Real
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return float(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # repr(float) 是最短往返表示，与 .NET 的 Convert.ToDecimal(double) 口径一致。
        return Decimal(repr(value))


class BoolAsInteger(TypeDecorator):
    """bool ↔ INTEGER。与旧库的 integer 列一致，不引入 BOOLEAN 亲和性。"""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return 1 if value else 0

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return bool(value)


class TextDateTime(TypeDecorator):
    """datetime ↔ TEXT。兼容 'Z' 后缀、缺时间、.NET 的 7 位小数。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S.%f")
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        # .NET 的 ticks 是 7 位小数，Python 只认 6 位，多出来的截掉。
        if "." in text:
            head, _, tail = text.partition(".")
            digits = ""
            for ch in tail:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if len(digits) > 6:
                text = f"{head}.{digits[:6]}{tail[len(digits):]}"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None
