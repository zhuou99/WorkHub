"""访问白名单匹配：支持精确 IP 与 IPv4 CIDR（如 10.0.0.0/8），IPv6 只做精确匹配。

对应 C# 的 WorkHub/Common/IpAllowList.cs。纯函数，不读配置、不碰网络。
"""

from __future__ import annotations

import ipaddress

__all__ = ["normalize", "is_match", "any_match", "is_loopback"]


def normalize(ip: str | None) -> str:
    """去掉空白、IPv6 方括号与「IP:端口」的端口后缀。"""
    s = (ip or "").strip()
    if not s:
        return ""

    if s.startswith("["):
        end = s.find("]")
        if end > 1:
            return s[1:end].strip()

    # 只在「整串不是合法 IP」时才考虑端口后缀，避免把 IPv6 的冒号切坏。
    if not _parse(s):
        colon = s.rfind(":")
        if colon > 0 and _is_int(s[colon + 1 :]):
            s = s[:colon]
    return s


def _is_int(text: str) -> bool:
    text = text.strip()
    if text.startswith("+") or text.startswith("-"):
        text = text[1:]
    return text.isdigit()


def _parse(text: str):
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        return None


def _in_cidr(target, network, prefix: int) -> bool:
    """按字节比对。网络地址按「写的样子」比，不做掩码归一：
    10.0.0.1 与 10.0.0.0/32 不命中，10.0.0.0 与 10.0.0.0/32 命中。"""
    t = target.packed
    n = network.packed
    full = prefix // 8
    rest = prefix % 8
    if t[:full] != n[:full]:
        return False
    if rest == 0:
        return True
    mask = (0xFF << (8 - rest)) & 0xFF
    return (t[full] & mask) == (n[full] & mask)


def is_match(remote_ip: str | None, entry: str | None) -> bool:
    """单条规则是否命中；非法规则按不命中处理。"""
    ip = normalize(remote_ip)
    rule = (entry or "").strip()
    if not ip or not rule:
        return False

    if "/" in rule:
        parts = [p.strip() for p in rule.split("/")]
        if len(parts) != 2:
            return False
        network = _parse(normalize(parts[0]))
        if network is None or not isinstance(network, ipaddress.IPv4Address):
            return False
        if not _is_int(parts[1]):
            return False
        prefix = int(parts[1])
        if prefix < 0 or prefix > 32:
            return False
        target = _parse(ip)
        if target is None or not isinstance(target, ipaddress.IPv4Address):
            return False
        return _in_cidr(target, network, prefix)

    a = _parse(ip)
    b = _parse(normalize(rule))
    return a is not None and b is not None and a == b


def any_match(remote_ip: str | None, rules: str | None) -> bool:
    """逗号/分号分隔的规则列表，任一命中即放行。"""
    if not rules or not rules.strip():
        return False
    for rule in rules.replace(";", ",").split(","):
        rule = rule.strip()
        if not rule:
            continue
        if is_match(remote_ip, rule):
            return True
    return False


def is_loopback(ip: str | None) -> bool:
    """是否回环地址（127.x / ::1）。"""
    address = _parse(normalize(ip))
    return address is not None and address.is_loopback
