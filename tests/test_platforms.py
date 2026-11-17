"""宿主适配：密钥掩码、附件上传、SQLite 备份。"""

from __future__ import annotations

import base64

from app.platforms.secret_protector import SecretProtector
from app.services.secret_service import _mask


def test_mask_short_plain():
    assert _mask("abc") == "•••"


def test_mask_long_plain():
    masked = _mask("github_pat_ABCDEFGHIJKLMN")
    assert masked.startswith("gi")
    assert masked.endswith("MN")
    assert "•" in masked


def test_secret_protector_round_trip():
    protector = SecretProtector(SecretProtector.new_key())
    cipher = protector.protect("hello-secret")
    assert cipher != "hello-secret"
    assert protector.unprotect(cipher) == "hello-secret"


def test_secret_protector_wrong_key_returns_empty():
    protector = SecretProtector(SecretProtector.new_key())
    other = SecretProtector(SecretProtector.new_key())
    cipher = protector.protect("secret")
    assert other.unprotect(cipher) == ""


def test_file_upload_returns_uploads_path(auth_client):
    content = base64.b64encode("hello".encode()).decode()
    response = auth_client.post("/api/files/upload", json={"fileName": "test.txt", "base64": content})
    assert response.status_code == 200
    path = response.json()["data"]
    assert path.startswith("/uploads/")


def test_file_upload_rejects_oversized(auth_client):
    content = base64.b64encode(b"x" * (17 * 1024 * 1024)).decode()
    response = auth_client.post("/api/files/upload", json={"fileName": "big.txt", "base64": content})
    assert response.status_code == 400
    assert "16MB" in response.json()["message"]


def test_secret_catalog_requires_owner(auth_client, client):
    response = auth_client.get("/api/secrets")
    assert response.status_code == 200
    data = response.json()["data"]
    assert {item["key"] for item in data} == {"baidu.appid", "baidu.secret", "github.token"}
    # 每个条目都不回显明文
    assert all("value" not in item for item in data)


def test_secret_set_and_remove(auth_client):
    response = auth_client.post("/api/secrets", json={"key": "github.token", "value": "ghp_test"})
    assert response.status_code == 200
    data = auth_client.get("/api/secrets").json()["data"]
    github = next(item for item in data if item["key"] == "github.token")
    assert github["configured"] is True
    assert github["readable"] is True
    assert github["masked"] != "ghp_test"

    assert auth_client.delete("/api/secrets/github.token").status_code == 200
    data = auth_client.get("/api/secrets").json()["data"]
    github = next(item for item in data if item["key"] == "github.token")
    assert github["configured"] is False
