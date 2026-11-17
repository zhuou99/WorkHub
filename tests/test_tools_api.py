"""工具台接口：目录、检索、执行、历史。"""

from __future__ import annotations


def test_catalog_lists_28_tools(auth_client):
    response = auth_client.get("/api/tools")
    assert response.status_code == 200
    tools = response.json()["data"]
    assert len(tools) == 28
    assert any(tool["id"] == "base64" for tool in tools)


def test_catalog_search(auth_client):
    response = auth_client.get("/api/tools", params={"keyword": "json2ts"})
    assert response.status_code == 200
    assert [tool["id"] for tool in response.json()["data"]] == ["json2ts"]


def test_run_io_tool(auth_client):
    response = auth_client.post("/api/tools/base64/run", json={"input": "中文", "option": "enc"})
    assert response.status_code == 200
    assert response.json()["data"]["output"] == "5Lit5paH"


def test_run_hex_tool_uses_enc_flag(auth_client):
    response = auth_client.post("/api/tools/hex/run", json={"input": "AB", "option": "enc"})
    assert response.json()["data"]["output"] == "41 42"


def test_run_tool_with_error_returns_400(auth_client):
    response = auth_client.post("/api/tools/hex/run", json={"input": "41 4", "option": "dec"})
    assert response.status_code == 400
    assert "十六进制字节对" in response.json()["message"]


def test_run_unknown_tool_returns_400(auth_client):
    response = auth_client.post("/api/tools/nope/run", json={"input": "x"})
    assert response.status_code == 400


def test_run_panel_tool(auth_client):
    response = auth_client.post(
        "/api/tools/unit/run", json={"params": {"groupId": "data", "fromId": "GiB", "value": 1}}
    )
    assert response.status_code == 200
    units = {row["id"]: row["text"] for row in response.json()["data"]["data"]["units"]}
    assert units["B"] == "1,073,741,824"


def test_run_diff_tool(auth_client):
    response = auth_client.post("/api/tools/diff/run", json={"params": {"left": "a\nb", "right": "a\nc"}})
    assert response.status_code == 200
    data = response.json()["data"]["data"]
    assert data["add"] == 1
    assert data["del"] == 1


def test_run_translate_tool_reports_phase_two(auth_client):
    response = auth_client.post("/api/tools/translate/run", json={"params": {"text": "hi"}})
    assert response.status_code == 400
    assert "阶段 2" in response.json()["message"]


def test_tool_history_is_recorded_and_capped(auth_client):
    for index in range(12):
        auth_client.post("/api/tools/base64/record", json={"toolName": "Base64", "input": f"值{index}"})

    rows = auth_client.get("/api/tools/base64/history").json()["data"]
    assert len(rows) == 10
    assert rows[0]["input"] == "值11"


def test_tool_history_deduplicates_last_input(auth_client):
    auth_client.post("/api/tools/base64/record", json={"toolName": "Base64", "input": "同一个"})
    auth_client.post("/api/tools/base64/record", json={"toolName": "Base64", "input": "同一个"})
    rows = auth_client.get("/api/tools/base64/history").json()["data"]
    assert len(rows) == 1


def test_tool_history_truncates_long_input(auth_client):
    auth_client.post("/api/tools/base64/record", json={"toolName": "Base64", "input": "x" * 2000})
    rows = auth_client.get("/api/tools/base64/history").json()["data"]
    assert rows[0]["input"].endswith("…（已截断）")
    assert len(rows[0]["input"]) == 1800 + len("…（已截断）")


def test_tool_history_keeps_only_30_per_tool(auth_client):
    for index in range(35):
        auth_client.post("/api/tools/base64/record", json={"toolName": "Base64", "input": f"值{index}"})
    rows = auth_client.get("/api/tools/prefs").json()["data"]
    assert len(rows) == 30


def test_viewer_can_run_tools(auth_client):
    """万能工具台是只读页，Viewer 也能用。"""
    auth_client.post("/api/users", json={"userName": "viewer1", "password": "secret123", "role": "Viewer"})
    from fastapi.testclient import TestClient

    with TestClient(auth_client.app) as other:
        assert other.post("/api/auth/login", json={"userName": "viewer1", "password": "secret123"}).status_code == 200
        response = other.post("/api/tools/base64/run", json={"input": "中文", "option": "enc"})
        assert response.status_code == 200
        assert response.json()["data"]["output"] == "5Lit5paH"
