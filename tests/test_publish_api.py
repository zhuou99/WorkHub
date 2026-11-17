"""导出与发布：博客园 Markdown + 公众号 HTML。"""

from __future__ import annotations


def _article(auth_client):
    response = auth_client.post(
        "/api/articles",
        json={"title": "标题", "summary": "摘要", "content": "# 一级\n\n正文 **加粗**", "tags": "a,b"},
    )
    return response.json()["data"]


def test_cnblogs_markdown(auth_client):
    article = _article(auth_client)
    response = auth_client.post("/api/publish/cnblogs", json={"articleId": article["id"]})
    assert response.status_code == 200
    text = response.json()["data"]
    assert text.startswith("<!--")
    assert "title: 标题" in text
    assert "summary: 摘要" in text
    assert "tags: a,b" in text
    assert "# 标题" in text
    assert "> 摘要" in text


def test_wechat_html_inlines_styles(auth_client):
    article = _article(auth_client)
    response = auth_client.post("/api/publish/wechat", json={"articleId": article["id"]})
    assert response.status_code == 200
    html = response.json()["data"]
    assert "<section style=" in html
    assert "<h1 style=" in html
    assert "标题" in html


def test_publish_log_round_trip(auth_client):
    article = _article(auth_client)
    response = auth_client.post(
        "/api/publish/log",
        json={"articleId": article["id"], "channel": "cnblogs", "result": "success", "detail": "ok"},
    )
    assert response.status_code == 200
    logs = auth_client.get("/api/publish/logs").json()["data"]
    assert len(logs) == 1
    assert logs[0]["channel"] == "cnblogs"


def test_publish_log_detail_truncated(auth_client):
    article = _article(auth_client)
    auth_client.post(
        "/api/publish/log",
        json={"articleId": article["id"], "channel": "wechat", "result": "failure", "detail": "x" * 600},
    )
    logs = auth_client.get("/api/publish/logs").json()["data"]
    assert len(logs[0]["detail"]) == 500
