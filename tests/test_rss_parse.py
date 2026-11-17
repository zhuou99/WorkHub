"""RSS / Atom 解析：对应 C# 的 RssService.ParseItems / ReadChannel。"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from app.services.rss_service import RssService

RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>测试博客</title>
    <link>https://example.com</link>
    <description>频道描述</description>
    <item>
      <title>第一篇文章</title>
      <link>https://example.com/1</link>
      <guid>https://example.com/1</guid>
      <pubDate>Tue, 03 Dec 2024 10:00:00 GMT</pubDate>
      <description>&lt;p&gt;摘要内容&lt;/p&gt;</description>
    </item>
    <item>
      <title>第二篇</title>
      <link>https://example.com/2</link>
      <pubDate>Wed, 04 Dec 2024 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom 源</title>
  <subtitle>副标题</subtitle>
  <entry>
    <title>Atom 条目</title>
    <id>tag:example.com,2024:1</id>
    <link href="https://example.com/a1" rel="alternate"/>
    <updated>2024-12-03T10:00:00Z</updated>
    <summary>条目摘要</summary>
    <author><name>作者名</name></author>
  </entry>
</feed>
"""


def _service():
    return RssService(None, None)


def test_parse_rss_channel():
    service = _service()
    root = ET.fromstring(RSS_XML)
    title, site, desc = service._read_channel(root)
    assert title == "测试博客"
    assert site == "https://example.com"
    assert desc == "频道描述"


def test_parse_rss_items():
    service = _service()
    root = ET.fromstring(RSS_XML)
    items = service._parse_items(root, "feed-1")
    assert len(items) == 2
    assert items[0].Title == "第一篇文章"
    assert items[0].Url == "https://example.com/1"
    assert items[0].Guid == "https://example.com/1"
    assert items[0].PublishedAt is not None
    # 摘要去 HTML 标签
    assert items[0].Summary == "摘要内容"
    # 第二篇没有 guid，落到链接
    assert items[1].Guid == "https://example.com/2"


def test_parse_atom_items():
    service = _service()
    root = ET.fromstring(ATOM_XML)
    items = service._parse_items(root, "feed-2")
    assert len(items) == 1
    assert items[0].Title == "Atom 条目"
    assert items[0].Url == "https://example.com/a1"
    assert items[0].Guid == "tag:example.com,2024:1"
    assert items[0].Author == "作者名"
    assert items[0].Summary == "条目摘要"


def test_parse_atom_channel():
    service = _service()
    root = ET.fromstring(ATOM_XML)
    title, site, desc = service._read_channel(root)
    assert title == "Atom 源"
    assert desc == "副标题"
