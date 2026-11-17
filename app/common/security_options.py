"""启动期传输安全边界：默认只监听回环；对外暴露必须显式满足 TLS / TLS 反代 / 人工覆盖之一。

对应 C# 的 WorkHub/Common/SecurityOptions.cs。这里只做「配置解析 + 拒绝原因生成」，
实际绑定交给 app/main.py。
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from app.common.ip_allow_list import any_match

__all__ = ["SecurityOptions", "DEFAULT_URLS"]

DEFAULT_URLS = "http://127.0.0.1:5277"


@dataclass
class SecurityOptions:
    allow_insecure_remote: bool = False
    behind_tls_proxy: bool = False
    allowed_networks: str = ""

    def is_allowed(self, remote_ip: str | None) -> bool:
        """该地址是否允许访问；白名单留空时不做限制。"""
        if not self.allowed_networks or not self.allowed_networks.strip():
            return True
        return any_match(remote_ip, self.allowed_networks)

    def validate(self, urls: str | None) -> str | None:
        """返回拒绝原因；None 表示可以启动。"""
        if has_https(urls):
            return None  # 已有 https 端点
        remote = remote_hosts(urls)
        if not remote:
            return None  # 全回环或缺省
        if self.behind_tls_proxy:
            return None  # 前置反代已终结 TLS
        if self.allow_insecure_remote:
            return None  # 人工确认过的内网明文
        return (
            f"拒绝启动：{'、'.join(remote)} 不是回环地址，而当前监听为明文 HTTP。"
            f"请任选其一：1) 改回 {DEFAULT_URLS}；2) 在 Urls 中增加 https:// 端点并配置证书；"
            "3) HTTPS 反向代理终结 TLS 后置 Security:BehindTlsProxy=true；"
            "4) 确认是可信内网时置 Security:AllowInsecureRemote=true。"
        )


def _split(urls: str | None) -> list[str]:
    if not urls or not urls.strip():
        return []
    return [part.strip() for part in urls.split(";") if part.strip()]


def has_https(urls: str | None) -> bool:
    """Urls 里是否已有 https 端点（分号分隔，忽略大小写）。"""
    return any(part.lower().startswith("https://") for part in _split(urls))


def is_loopback_urls(urls: str | None) -> bool:
    """是否全部为回环监听（localhost / 127.x / ::1；0.0.0.0、*、+ 与局域网 IP 均视为对外）。"""
    return not remote_hosts(urls)


def remote_hosts(urls: str | None) -> list[str]:
    """列出非回环主机名，供拒绝文案与日志使用。"""
    hosts: list[str] = []
    for part in _split(urls):
        if part.lower().startswith("https://"):
            continue
        host = host_of(part)
        if not host or not is_loopback_host(host):
            hosts.append(host if host else part)
    return hosts


def is_loopback_host(host: str | None) -> bool:
    """单个主机是否回环：localhost、IPv4/IPv6 回环地址（忽略方括号）。"""
    if not host or not host.strip():
        return False
    host = host.strip().strip("[]")
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def host_of(url: str) -> str:
    """从一段 URL 里取出主机名（不含端口）。"""
    scheme = url.find("://")
    authority = url[scheme + 3 :] if scheme >= 0 else url
    cut = len(authority)
    for ch in "/?#":
        index = authority.find(ch)
        if index >= 0:
            cut = min(cut, index)
    authority = authority[:cut]
    if authority.startswith("["):
        end = authority.find("]")
        return authority[1:end] if end > 0 else ""
    colon = authority.find(":")
    return authority[:colon] if colon >= 0 else authority
