"""全文检索：FTS5 索引 + LIKE 兜底 + 索引状态。"""

from __future__ import annotations


def _seed(auth_client):
    auth_client.post("/api/notes", json={"title": "数据库", "content": "连接失败排查"})
    auth_client.post("/api/articles", json={"title": "发布流程", "content": "数据库备份"})
    auth_client.post("/api/snippets", json={"title": "迁移", "code": "ALTER TABLE", "language": "sql"})


def test_search_finds_note_by_trigram(auth_client):
    _seed(auth_client)
    response = auth_client.get("/api/search", params={"kw": "连接失败"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["hits"]) >= 1
    kinds = {hit["kind"] for hit in data["hits"]}
    assert "note" in kinds


def test_search_counts_by_kind(auth_client):
    _seed(auth_client)
    response = auth_client.get("/api/search", params={"kw": "数据库"})
    data = response.json()["data"]
    assert "note" in data["kinds"]
    assert "article" in data["kinds"]


def test_search_short_keyword_uses_like(auth_client):
    _seed(auth_client)
    # 两字词凑不出三元组，走 LIKE 兜底
    response = auth_client.get("/api/search", params={"kw": "失败"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["hits"]) >= 1
    assert "LIKE" in data["engine"]


def test_search_marks_keyword(auth_client):
    _seed(auth_client)
    response = auth_client.get("/api/search", params={"kw": "数据库"})
    hits = response.json()["data"]["hits"]
    assert any(part["mark"] for hit in hits for part in hit["titleParts"])


def test_search_blank_keyword_returns_empty(auth_client):
    _seed(auth_client)
    response = auth_client.get("/api/search", params={"kw": "  "})
    assert response.json()["data"]["hits"] == []


def test_search_index_status(auth_client):
    _seed(auth_client)
    response = auth_client.get("/api/search/index")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["engine"] != ""
    assert data["source"] >= 3


def test_search_rebuild(auth_client):
    _seed(auth_client)
    response = auth_client.post("/api/search/rebuild")
    assert response.status_code == 200
    assert "重建" in response.json()["message"]


def test_note_delete_removes_from_index(auth_client):
    note = auth_client.post("/api/notes", json={"title": "临时", "content": "会被删掉的内容"}).json()["data"]
    auth_client.delete(f"/api/notes/{note['id']}")
    response = auth_client.get("/api/search", params={"kw": "会被删掉"})
    assert response.json()["data"]["hits"] == []
