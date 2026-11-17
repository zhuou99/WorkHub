"""备份与恢复：run / list / delete / options。"""

from __future__ import annotations


def test_backup_run_and_list(auth_client):
    response = auth_client.post("/api/backup/run")
    assert response.status_code == 200, response.text
    assert "已备份" in response.json()["message"]

    response = auth_client.get("/api/backup/list")
    assert response.status_code == 200
    backups = response.json()["data"]
    assert len(backups) == 1
    assert backups[0]["name"].startswith("workhub-backup-")


def test_backup_options_round_trip(auth_client):
    response = auth_client.post("/api/backup/options", json={"keep": 20})
    assert response.status_code == 200

    options = auth_client.get("/api/backup/options").json()["data"]
    assert options["keep"] == 20


def test_backup_options_rejects_bad_keep(auth_client):
    response = auth_client.post("/api/backup/options", json={"keep": 0})
    assert response.status_code == 400


def test_backup_delete_rejects_bad_name(auth_client):
    response = auth_client.delete("/api/backup/evil.zip")
    assert response.status_code == 400
    assert "文件名不对" in response.json()["message"]


def test_backup_delete_and_missing(auth_client):
    response = auth_client.delete("/api/backup/workhub-backup-20260101-000000.zip")
    assert response.status_code == 400
    assert "已经不在了" in response.json()["message"]
