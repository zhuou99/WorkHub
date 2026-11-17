"""内容类实体（笔记/文章/片段/收藏）的接口与索引同步。"""

from __future__ import annotations


def test_note_crud(auth_client):
    response = auth_client.post("/api/notes", json={"title": "第一篇笔记", "content": "正文", "tags": "a,b"})
    assert response.status_code == 200, response.text
    note = response.json()["data"]
    assert note["title"] == "第一篇笔记"
    assert note["pinned"] is False

    rows = auth_client.get("/api/notes").json()["data"]
    assert len(rows) == 1

    one = auth_client.get(f"/api/notes/{note['id']}").json()["data"]
    assert one["content"] == "正文"

    # 更新
    response = auth_client.post("/api/notes", json={"id": note["id"], "title": "改过", "content": "新正文", "pinned": True})
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "改过"
    assert response.json()["data"]["pinned"] is True

    assert auth_client.delete(f"/api/notes/{note['id']}").status_code == 200
    assert auth_client.get("/api/notes").json()["data"] == []


def test_note_page_paging(auth_client):
    for index in range(3):
        auth_client.post("/api/notes", json={"title": f"笔记{index}", "content": f"内容{index}"})
    response = auth_client.get("/api/notes/page", params={"pageIndex": 1, "pageSize": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["rows"]) == 2


def test_note_page_keyword_search(auth_client):
    auth_client.post("/api/notes", json={"title": "数据库", "content": "连接失败"})
    auth_client.post("/api/notes", json={"title": "别的", "content": "无关"})
    response = auth_client.get("/api/notes/page", params={"keyword": "连接"})
    assert response.json()["total"] == 1
    assert response.json()["rows"][0]["title"] == "数据库"


def test_article_crud_and_status(auth_client):
    response = auth_client.post("/api/articles", json={"title": "文章", "summary": "摘要", "content": "正文"})
    article = response.json()["data"]
    assert article["status"] == "draft"
    assert article["publishTime"] is None

    response = auth_client.post(f"/api/articles/{article['id']}/status", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "done"
    assert response.json()["data"]["publishTime"] is not None


def test_article_page_project_filter(auth_client):
    auth_client.post("/api/articles", json={"title": "A", "projectId": "p1"})
    auth_client.post("/api/articles", json={"title": "B", "projectId": "p2"})
    response = auth_client.get("/api/articles/page", params={"projectId": "p1"})
    assert response.json()["total"] == 1
    assert response.json()["rows"][0]["title"] == "A"


def test_snippet_crud(auth_client):
    response = auth_client.post("/api/snippets", json={"title": "快排", "language": "python", "code": "def qsort(): pass"})
    assert response.status_code == 200
    assert response.json()["data"]["language"] == "python"
    assert len(auth_client.get("/api/snippets").json()["data"]) == 1


def test_bookmark_save_and_delete(auth_client):
    response = auth_client.post("/api/bookmarks", json={"title": "收藏", "url": "https://example.com"})
    assert response.status_code == 200
    bookmark = response.json()["data"]
    assert bookmark["status"] == "unread"
    assert auth_client.delete(f"/api/bookmarks/{bookmark['id']}").status_code == 200


def test_note_save_with_blank_title_returns_400(auth_client):
    response = auth_client.post("/api/notes", json={"title": "  ", "content": "x"})
    assert response.status_code == 400


def test_bookmark_save_without_url_returns_400(auth_client):
    response = auth_client.post("/api/bookmarks", json={"title": "没链接", "url": ""})
    assert response.status_code == 400
