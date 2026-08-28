"""End-to-end test for meetings API."""
import httpx
import sys

BASE = "http://localhost:8000/api/v1"
passed = 0
failed = 0


def check(name, status, expected=200):
    global passed, failed
    if status == expected:
        print(f"  PASS: {name} (status={status})")
        passed += 1
    else:
        print(f"  FAIL: {name} (expected={expected}, got={status})")
        failed += 1


# 1. Login
print("=== 1. Auth Login ===")
r = httpx.post(f"{BASE}/auth/login", json={"username": "testuser", "password": "testpass123"}, timeout=10)
check("login", r.status_code)
token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

# 2. List meetings (empty)
print("\n=== 2. List Meetings (empty) ===")
r = httpx.get(f"{BASE}/meetings", headers=headers, timeout=10)
check("list meetings", r.status_code)
data = r.json()
print(f"  Total: {data['total']}")
assert data["total"] == 0

# 3. Create meeting
print("\n=== 3. Create Meeting ===")
r = httpx.post(f"{BASE}/meetings", headers=headers, json={"title": "Sprint 23 周会", "date": "2026-08-26"}, timeout=10)
check("create meeting", r.status_code, expected=201)
meeting = r.json()
print(f"  Meeting: {meeting['title']} (id={meeting['id'][:8]}...)")
meeting_id = meeting["id"]

# 4. Get meeting
print("\n=== 4. Get Meeting ===")
r = httpx.get(f"{BASE}/meetings/{meeting_id}", headers=headers, timeout=10)
check("get meeting", r.status_code)
print(f"  Status: {r.json()['status']}")

# 5. Send messages
print("\n=== 5. Send Messages ===")
r = httpx.post(f"{BASE}/meetings/{meeting_id}/messages", headers=headers,
    json={"sender": "系统", "role": "admin", "content": "📋 Sprint 23 周会已开始"}, timeout=10)
check("send message 1", r.status_code, expected=201)
print(f"  Message 1: {r.json()['content'][:30]}...")

r = httpx.post(f"{BASE}/meetings/{meeting_id}/messages", headers=headers,
    json={"sender": "Research Agent", "role": "member", "content": "本周完成了市场竞品分析报告"}, timeout=10)
check("send message 2", r.status_code, expected=201)

r = httpx.post(f"{BASE}/meetings/{meeting_id}/messages", headers=headers,
    json={"sender": "Sales Agent", "role": "member", "content": "本周新增2个潜在客户"}, timeout=10)
check("send message 3", r.status_code, expected=201)

# 6. List messages
print("\n=== 6. List Messages ===")
r = httpx.get(f"{BASE}/meetings/{meeting_id}/messages", headers=headers, timeout=10)
check("list messages", r.status_code)
msgs = r.json()
print(f"  Total messages: {msgs['total']}")
for m in msgs["messages"]:
    print(f"    [{m['time']}] {m['sender']}: {m['content'][:30]}...")

# 7. Generate summary
print("\n=== 7. Generate Summary ===")
r = httpx.post(f"{BASE}/meetings/{meeting_id}/summary", headers=headers, timeout=10)
check("generate summary", r.status_code)
summary = r.json()
print(f"  Summary: {summary['summary'][:100]}...")

# 8. List meetings again
print("\n=== 8. List Meetings (after create) ===")
r = httpx.get(f"{BASE}/meetings", headers=headers, timeout=10)
check("list meetings", r.status_code)
data = r.json()
print(f"  Total: {data['total']}")
assert data["total"] == 1

# 9. Delete meeting
print("\n=== 9. Delete Meeting ===")
r = httpx.delete(f"{BASE}/meetings/{meeting_id}", headers=headers, timeout=10)
check("delete meeting", r.status_code, expected=204)

# 10. Verify deleted
print("\n=== 10. Verify Deleted ===")
r = httpx.get(f"{BASE}/meetings", headers=headers, timeout=10)
check("list meetings after delete", r.status_code)
data = r.json()
print(f"  Total: {data['total']}")
assert data["total"] == 0

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
else:
    print("All meetings API tests passed!")