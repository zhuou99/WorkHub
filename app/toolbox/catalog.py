"""工具目录：28 个工具的定义与检索。

对应 C# 的 WorkHub/Common/ToolCatalog.cs。

18 个 io 工具走 `run(input, option) -> str`；10 个面板工具走 `params` 字典。
选项到开关的映射是不对称的（C# 那边就是这样）：
base64/url/unicode 判 `option == "dec"`，hex/html 判 `option == "enc"`。
统一成一个方向会把四个工具翻转，所以照搬。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from app.toolbox import transforms
from app.toolbox.yaml_transforms import json_to_yaml, yaml_to_json

__all__ = ["ToolDef", "CATEGORIES", "ALL", "search", "get", "PANEL_TOOLS"]

CATEGORIES: tuple[str, ...] = ("编解码", "转换", "文本", "哈希加密", "生成器", "颜色", "翻译")


@dataclass(frozen=True)
class ToolDef:
    """工具定义。"""

    id: str
    name: str
    category: str
    icon: str
    description: str
    kind: str = "io"  # io | panel
    options: tuple[tuple[str, str], ...] = ()  # (label, value)
    run: Callable[[str, str], str] | None = None
    params: tuple[str, ...] = field(default=())  # 面板工具需要的参数名


def _io(
    tool_id: str,
    name: str,
    category: str,
    icon: str,
    description: str,
    options: tuple[tuple[str, str], ...] | None,
    run: Callable[[str, str], str],
) -> ToolDef:
    return ToolDef(tool_id, name, category, icon, description, "io", options or (), run, ())


def _panel(
    tool_id: str,
    name: str,
    category: str,
    icon: str,
    description: str,
    params: tuple[str, ...],
) -> ToolDef:
    return ToolDef(tool_id, name, category, icon, description, "panel", (), None, params)


ALL: tuple[ToolDef, ...] = (
    # ---- 编解码 ----
    _io("base64", "Base64", "编解码", "binary", "UTF-8 文本 ⇄ Base64（兼容 URL-safe 字符）",
        (("编码", "enc"), ("解码", "dec")), lambda i, o: transforms.base64_transform(i, o == "dec")),
    _io("url", "URL 编码", "编解码", "link", "percent-encode ⇄ decode",
        (("编码", "enc"), ("解码", "dec")), lambda i, o: transforms.url(i, o == "dec")),
    _io("unicode", "Unicode", "编解码", "code", "中文 ⇄ \\uXXXX 转义",
        (("转 \\uXXXX", "enc"), ("还原", "dec")), lambda i, o: transforms.unicode_escape(i, o == "dec")),
    _io("hex", "Hex", "编解码", "hash", "文本 ⇄ 十六进制字节",
        (("转 Hex", "enc"), ("转文本", "dec")), lambda i, o: transforms.hex(i, o == "enc")),
    _io("html", "HTML 实体", "编解码", "code-xml", "特殊字符 ⇄ &amp; 实体",
        (("转义", "enc"), ("还原", "dec")), lambda i, o: transforms.html_entity(i, o == "enc")),
    _io("jwt", "JWT 解析", "编解码", "shield", "拆出 Header / Payload / 过期时间（只看内容，不验签名）",
        None, lambda i, _: transforms.jwt(i)),
    # ---- 转换 ----
    _io("json", "JSON", "转换", "file-json", "格式化 / 压缩 / 字符串转义 / 校验",
        (("格式化", "pretty"), ("压缩", "min"), ("转义为字符串", "escape"), ("还原字符串", "unescape")),
        lambda i, o: transforms.json_mode(i, o)),
    _io("json2csharp", "JSON → C#", "转换", "file-code", "由 JSON 样例生成 POCO 实体类",
        None, lambda i, _: transforms.json_to_csharp(i, "Result")),
    _io("json2ts", "JSON → TypeScript", "转换", "file-code",
        "由 JSON 样例生成 interface，嵌套对象逐层建接口、null 字段标可选",
        None, lambda i, _: transforms.json_to_typescript(i, "Root")),
    _io("yaml", "YAML ⇄ JSON", "转换", "file-code",
        "YAML 与 JSON 双向；多行字符串用双引号转义输出，不会被折叠块偷偷加尾换行",
        (("YAML → JSON", "y2j"), ("JSON → YAML", "j2y")),
        lambda i, o: json_to_yaml(i) if o == "j2y" else yaml_to_json(i)),
    _io("json2xml", "JSON → XML", "转换", "file-code", "同名字段自动聚合为数组节点",
        None, lambda i, _: transforms.json_to_xml(i)),
    _io("xml2json", "XML → JSON", "转换", "file-code", "属性带 @ 前缀，重复节点成数组",
        None, lambda i, _: transforms.xml_to_json(i)),
    _panel("unit", "单位换算", "转换", "calculator", "长度/面积/体积/重量/存储/时间/速度/温度八组，一次列出该组全部单位",
           ("groupId", "fromId", "value")),
    _io("sql", "SQL 格式化", "转换", "database", "关键字大写 + 断行缩进（轻量格式化）",
        None, lambda i, _: transforms.sql_format(i)),
    _io("cron", "Cron 解析", "转换", "clock", "5/6 段表达式 → 中文说明 + 接下来 5 次触发时间",
        None, lambda i, _: transforms.cron(i)),
    _io("time", "时间戳", "转换", "calendar", "空输入=当前时间；10/13 位时间戳 ⇄ 日期",
        None, lambda i, _: transforms.time_text(i)),
    # ---- 文本 ----
    _io("naming", "命名风格", "文本", "pencil", "一词 → snake / kebab / Pascal / camel 全家桶",
        None, lambda i, _: transforms.naming(i)),
    _io("case", "大小写", "文本", "quote", "全大写 / 全小写 / 每词首字母 / 大小写互换",
        (("全部大写", "upper"), ("全部小写", "lower"), ("每词首字母大写", "title"), ("大小写互换", "swap")),
        lambda i, o: transforms.case(i, o)),
    _panel("regex", "正则测试", "文本", "search", "实时列出匹配与分组，支持忽略大小写/多行",
           ("pattern", "subject", "ignoreCase", "multiline")),
    _panel("diff", "文本比对", "文本", "columns", "逐行 Diff，增删高亮", ("left", "right")),
    _panel("count", "字数统计", "文本", "calculator", "字符 / 中文 / 词 / 行 / 字节", ("text",)),
    # ---- 哈希加密 ----
    _io("hash", "哈希摘要", "哈希加密", "hash", "MD5 / SHA1 / SHA256 / SHA512 一次全出",
        None, lambda i, _: transforms.hash_all(i)),
    _panel("hmac", "HMAC-SHA256", "哈希加密", "key", "密钥 + 数据 → Hex / Base64 签名", ("key", "data")),
    # ---- 生成器 ----
    _panel("guid", "GUID 批量", "生成器", "fingerprint", "多格式批量生成，点击复制", ("count", "format", "upper")),
    _panel("password", "随机密码", "生成器", "lock", "长度与字符集可控，含易混淆字符过滤",
           ("length", "count", "lower", "upper", "digit", "symbol", "noConfuse")),
    _panel("qr", "二维码 / 条码", "生成器", "qr-code", "文本实时生成 QR / Code128 条码", ("value", "mode", "format", "ecc")),
    # ---- 颜色 ----
    _panel("color", "颜色转换", "颜色", "palette", "取色 → HEX / RGB / HSL 互查", ("hex", "rgb")),
    # ---- 翻译 ----
    _panel("translate", "翻译", "翻译", "globe", "百度翻译 + 自己的术语表（密钥加密保存，未配也能查术语）",
           ("text", "from", "to", "forceGlossary")),
)

#: 面板工具的 id 集合
PANEL_TOOLS: frozenset[str] = frozenset(tool.id for tool in ALL if tool.kind == "panel")


def search(keyword: str | None) -> list[ToolDef]:
    """按关键字检索工具。

    C# 那边只把 Name 与 Description 转小写再匹配，Id 与 Category 是原样匹配的——
    这里照搬这个不对称口径。
    """
    if not (keyword or "").strip():
        return list(ALL)
    needle = keyword.strip().lower()
    return [
        tool
        for tool in ALL
        if needle in tool.name.lower()
        or needle in tool.id
        or needle in tool.description.lower()
        or needle in tool.category
    ]


def get(tool_id: str) -> ToolDef | None:
    """按 id 取工具定义。"""
    for tool in ALL:
        if tool.id == tool_id:
            return tool
    return None
