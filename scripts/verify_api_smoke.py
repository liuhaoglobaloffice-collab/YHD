# -*- coding: utf-8 -*-
"""LiuHao AI OS —— 部署后 API 冒烟验证脚本（Y1.0 交付工具）。

用法:
    python scripts/verify_api_smoke.py --username USER --password PASS \
        [--base http://localhost:8000]

覆盖前端所有核心页面依赖的 API：Auth / Dashboard / AI Employees / Goals /
Workflows / Tasks / Knowledge(含语义检索 POST) / Audit / Approvals / Provider /
CRM / 子账号(安全) / Business Metrics / Health / Costs / Roles / Permissions /
Quotes / Platforms，以及根路径 Prometheus /metrics 文本端点。

退出码 0 = 全部通过；1 = 存在失败。
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def req(method, url, body=None, token=None, timeout=60, raw=False):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return (resp.status, text) if raw else (resp.status, json.loads(text))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8")
        if raw:
            return e.code, text
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, {"error": text[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


def summarize(payload):
    if isinstance(payload, list):
        return f"list[{len(payload)}]"
    if isinstance(payload, dict):
        keys = list(payload.keys())[:8]
        items = payload.get("items")
        if isinstance(items, list):
            return f"dict(total={payload.get('total')}, items={len(items)}) keys={keys}"
        return f"dict keys={keys}"
    return type(payload).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    base = args.base.rstrip("/")
    api = base + "/api/v1"

    st, r = req("POST", api + "/auth/login",
                {"username": args.username, "password": args.password})
    if st != 200:
        print(f"[FATAL] login failed: {st} {r}")
        return 1
    token = r["access_token"]
    print(f"[OK ] login: token_len={len(token)}")

    # (method, path, body, label)
    checks = [
        ("GET", "/auth/me", None, "Auth/Session"),
        ("GET", "/dashboard/overview", None, "Dashboard overview"),
        ("GET", "/dashboard/system-health", None, "Dashboard system-health"),
        ("GET", "/dashboard/alerts", None, "Dashboard alerts"),
        ("GET", "/dashboard/live-activity", None, "Dashboard live-activity"),
        ("GET", "/dashboard/recent-activity", None, "Dashboard recent-activity"),
        ("GET", "/workforce/employees", None, "AI Employees"),
        ("GET", "/goals", None, "Goals"),
        ("GET", "/workflows", None, "Workflows"),
        ("GET", "/tasks", None, "Tasks"),
        ("GET", "/knowledge/documents", None, "Knowledge documents"),
        ("GET", "/knowledge/memory", None, "Knowledge memories"),
        ("POST", "/knowledge/retrieval/search",
         {"query": "美国市场", "sources": ["document", "memory"], "limit": 5},
         "Knowledge semantic search"),
        ("GET", "/audit", None, "Audit logs"),
        ("GET", "/approvals", None, "Approvals"),
        ("GET", "/provider/status", None, "Provider/Models status"),
        ("GET", "/workforce/provider/status", None, "Workforce provider status"),
        ("GET", "/crm/leads", None, "CRM leads"),
        ("GET", "/crm/leads/stats", None, "CRM leads stats"),
        ("GET", "/accounts/sub-accounts", None, "Sub-accounts (Security)"),
        ("GET", "/business/metrics", None, "Business metrics"),
        ("GET", "/health/system", None, "System health info"),
        ("GET", "/workforce/costs/summary", None, "AI costs summary"),
        ("GET", "/roles", None, "Roles"),
        ("GET", "/permissions", None, "Permissions"),
        ("GET", "/quotes", None, "Quotes list"),
        ("GET", "/platforms/accounts", None, "Platforms accounts list"),
    ]

    passed = failed = 0
    for method, path, body, label in checks:
        st, payload = req(method, api + path, body=body, token=token)
        ok = st == 200
        passed += ok
        failed += (not ok)
        detail = summarize(payload) if ok else json.dumps(payload, ensure_ascii=False)[:160]
        print(f"[{'OK ' if ok else 'FAIL'}] {st} {label:30s} {path:38s} {detail}")

    # Prometheus 指标端点挂在服务器根路径（text/plain）
    st_m, text_m = req("GET", base + "/metrics", token=token, raw=True)
    ok_m = st_m == 200 and "provider_model_" in text_m
    passed += ok_m
    failed += (not ok_m)
    print(f"[{'OK ' if ok_m else 'FAIL'}] {st_m} {'Prometheus /metrics':30s} {'/metrics':38s} "
          f"{text_m[:80].replace(chr(10), ' | ') if ok_m else text_m[:160]}")

    print(f"\n=== {passed} passed, {failed} failed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
