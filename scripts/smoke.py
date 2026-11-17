"""全链路冒烟：对着跑起来的服务走一遍主要流程。

用法：
    python -m uvicorn app.main:app --host 127.0.0.1 --port 5277
    python scripts/smoke.py

每步打印一行 PASS / FAIL，最后汇总。
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import httpx

BASE = os.environ.get("WORKHUB_BASE", "http://127.0.0.1:5277")
USER = "admin"
PASSWORD = "admin123"

passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label} {detail}")


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=20.0) as client:
        print("== 健康检查 ==")
        response = client.get("/health")
        check("GET /health", response.status_code == 200, response.text)
        check("status == ok", response.json().get("status") == "ok", response.text)

        print("== 登录保护 ==")
        guard = client.get("/api/auth/guard").json()["data"]
        check("remainingTries == 5", guard.get("remainingTries") == 5, str(guard))

        print("== 登录 ==")
        response = client.post("/api/auth/login", json={"userName": USER, "password": PASSWORD})
        check("POST /api/auth/login", response.status_code == 200, response.text)
        me = client.get("/api/auth/me").json()["data"]
        check("角色是 Owner", me.get("role") == "Owner", str(me))

        print("== 客户 ==")
        response = client.post("/api/clients", json={"name": "冒烟客户", "contact": "张三"})
        check("POST /api/clients", response.status_code == 200, response.text)
        client_id = response.json()["data"]["id"]
        check("客户列表有 1 条", len(client.get("/api/clients").json()["data"]) == 1)

        print("== 项目 ==")
        response = client.post("/api/projects", json={"name": "冒烟项目", "amount": 10000, "clientId": client_id})
        check("POST /api/projects", response.status_code == 200, response.text)
        project_id = response.json()["data"]["id"]

        print("== 财务 ==")
        response = client.post(
            "/api/finance/invoices",
            json={"clientId": client_id, "projectId": project_id, "amount": 1000, "taxRate": 6},
        )
        check("POST /api/finance/invoices", response.status_code == 200, response.text)
        invoice = response.json()["data"]
        check("税额 56.6", abs(invoice["tax"] - 56.6) < 1e-9, str(invoice["tax"]))
        invoice_id = invoice["id"]

        response = client.post("/api/finance/payments", json={"invoiceId": invoice_id, "amount": 400})
        check("POST /api/finance/payments", response.status_code == 200, response.text)
        invoice = client.get("/api/finance/invoices").json()["data"][0]
        check("已收 400", invoice["paid"] == 400, str(invoice["paid"]))
        check("待收 600", invoice["due"] == 600, str(invoice["due"]))

        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        response = client.post(
            "/api/finance/plans",
            json={"projectId": project_id, "title": "首款", "amount": 3000, "dueDate": yesterday},
        )
        check("POST /api/finance/plans", response.status_code == 200, response.text)
        check("期次逾期", response.json()["data"]["isOverdue"] is True, response.text)
        check("期次占合同 30%", response.json()["data"]["percentOf"] == 30, response.text)

        print("== 任务 ==")
        response = client.post("/api/tasks", json={"title": "冒烟任务", "projectId": project_id})
        check("POST /api/tasks", response.status_code == 200, response.text)
        task_id = response.json()["data"]["id"]
        response = client.post(f"/api/tasks/{task_id}/move", json={"status": "done"})
        check("移到已完成", response.status_code == 200, response.text)
        check("补上完成时间", response.json()["data"]["doneTime"] is not None, response.text)

        print("== 删除影响预览 ==")
        response = client.get(f"/api/projects/delete-impact/{project_id}")
        check("GET delete-impact", response.status_code == 200, response.text)
        labels = [group["label"] for group in response.json()["data"]["groups"]]
        check(
            "分组顺序正确",
            labels == ["里程碑", "任务", "发票", "支出", "开源仓库", "回款计划", "文章"],
            str(labels),
        )

        print("== 工具台 ==")
        tools = client.get("/api/tools").json()["data"]
        check("28 个工具", len(tools) == 28, str(len(tools)))
        response = client.post("/api/tools/base64/run", json={"input": "中文", "option": "enc"})
        check("Base64 编码", response.json()["data"]["output"] == "5Lit5paH", response.text)
        response = client.post("/api/tools/cron/run", json={"input": "*/5 * * * *"})
        check("Cron 解析", "每 5 分" in response.json()["data"]["output"], response.text)

        print("== 内容与检索（阶段 2）==")
        response = client.post("/api/notes", json={"title": "冒烟笔记", "content": "全文检索的数据库连接失败排查"})
        check("POST /api/notes", response.status_code == 200, response.text)
        response = client.get("/api/search", params={"kw": "连接失败"})
        hits = response.json()["data"]["hits"]
        check("检索命中笔记", len(hits) >= 1, str(hits))
        response = client.get("/api/search/index")
        check("索引引擎", "FTS5" in response.json()["data"]["engine"], response.text)
        response = client.get("/api/report", params={"days": 7})
        check("周报生成", response.json()["data"]["markdown"].startswith("# 周报"), response.text)
        response = client.get("/api/secrets")
        check("密钥目录", len(response.json()["data"]) == 3, response.text)

        print("== 登出 ==")
        check("POST /api/auth/logout", client.post("/api/auth/logout").status_code == 200)
        check("登出后 401", client.get("/api/auth/me").status_code == 401)

    print()
    print(f"共 {passed + failed} 步：通过 {passed}，失败 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
