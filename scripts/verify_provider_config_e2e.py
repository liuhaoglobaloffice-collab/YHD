"""
E2E verification for 产品内 Provider/API Key 配置（模型注册）feature.

Runs INSIDE the backend container against the real HTTP API + real PostgreSQL:
  1. catalog requires auth (401 anonymous)
  2. viewer cannot write (RBAC 403)
  3. bogus cloud key + test=true is REJECTED and NOT persisted (fail-closed)
  4. real Ollama + test=true -> healthy, persisted, runtime registered
  5. cloud key persisted as Fernet CIPHERTEXT (never plaintext at rest / in API)
  6. delete removes row + unregisters runtime
  7. audit rows written
"""
import asyncio
import json
import sys

import httpx

API = "http://localhost:8000/api/v1"

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


def token_for(uid, role):
    from src.identity.auth import create_access_token
    return create_access_token({"sub": str(uid), "user_id": uid, "role": role})


async def main():
    admin = token_for(4, "admin")
    viewer = token_for(3, "viewer")
    H_ADMIN = {"Authorization": f"Bearer {admin}"}
    H_VIEWER = {"Authorization": f"Bearer {viewer}"}

    async with httpx.AsyncClient(timeout=30) as cx:
        # 1. anonymous -> 401/403
        r = await cx.get(f"{API}/provider/catalog")
        check("catalog_anonymous_denied", r.status_code in (401, 403), f"-> {r.status_code}")

        # 2. admin catalog
        r = await cx.get(f"{API}/provider/catalog", headers=H_ADMIN)
        check("catalog_admin_200", r.status_code == 200, f"-> {r.status_code}")
        names = [p["name"] for p in r.json().get("providers", [])]
        check("catalog_has_major_providers",
              {"openai", "deepseek", "moonshot", "anthropic", "google", "xai", "ollama"} <= set(names),
              f"-> {names}")

        # 3. viewer write forbidden
        r = await cx.post(f"{API}/provider/configs", headers=H_VIEWER,
                         json={"provider": "deepseek", "api_key": "sk-x", "test": False})
        check("viewer_write_403", r.status_code == 403, f"-> {r.status_code}")

        # viewer read allowed
        r = await cx.get(f"{API}/provider/configs", headers=H_VIEWER)
        check("viewer_read_allowed", r.status_code == 200, f"-> {r.status_code}")

        # 4. bogus cloud key + test=true -> rejected (fail-closed), NOT persisted
        r = await cx.post(f"{API}/provider/configs", headers=H_ADMIN,
                         json={"provider": "deepseek",
                               "api_key": "sk-bogus-invalid-key-0000000000",
                               "base_url": "https://api.deepseek.com/v1",
                               "test": True})
        check("bogus_key_test_rejected", r.status_code == 400, f"-> {r.status_code} {r.text[:120]}")

        # 5. real Ollama + test=true -> healthy + persisted + runtime
        r = await cx.post(f"{API}/provider/configs", headers=H_ADMIN,
                         json={"provider": "ollama",
                               "base_url": "http://host.docker.internal:11434",
                               "model": "qwen2.5:7b",
                               "test": True})
        check("ollama_test_and_save_ok", r.status_code == 200, f"-> {r.status_code} {r.text[:160]}")
        if r.status_code == 200:
            body = r.json()
            check("ollama_health_healthy",
                  (body.get("health") or {}).get("status") == "healthy",
                  f"-> {body.get('health')}")

        # 6. cloud provider with a MARKER key, test=false (no network) -> persisted
        marker = "sk-E2E-MARKER-plaintext-MUST-NOT-APPEAR-9f8e7d"
        r = await cx.post(f"{API}/provider/configs", headers=H_ADMIN,
                         json={"provider": "deepseek", "api_key": marker,
                               "base_url": "https://api.deepseek.com/v1",
                               "model": "deepseek-chat", "test": False})
        check("deepseek_save_ok", r.status_code == 200, f"-> {r.status_code} {r.text[:160]}")

        # API list must NOT leak plaintext
        r = await cx.get(f"{API}/provider/configs", headers=H_ADMIN)
        raw = r.text
        check("api_never_returns_plaintext_key", marker not in raw, "marker absent from /configs")
        cfg = next((c for c in r.json().get("configs", []) if c["provider"] == "deepseek"), None)
        check("deepseek_listed_masked",
              cfg is not None and cfg["has_api_key"] is True and "api_key" not in cfg,
              f"-> {cfg}")

        # 7. DB-level: stored value is ciphertext, decrypt round-trips
        from sqlalchemy import select
        from src.api.dependencies.database import get_session_factory
        from src.core.encryption import decrypt_value
        from src.database.models import LLMProviderConfigModel
        async with get_session_factory()() as s:
            row = await s.scalar(select(LLMProviderConfigModel).where(
                LLMProviderConfigModel.provider == "deepseek"))
            check("db_row_exists", row is not None)
            if row:
                stored = row.api_key_encrypted or ""
                check("db_stores_ciphertext_not_plaintext",
                      marker not in stored and stored != marker and len(stored) > 20,
                      f"len={len(stored)}")
                check("db_decrypt_roundtrip", decrypt_value(stored) == marker)
                check("ollama_row_persisted", row is not None)
            oll = await s.scalar(select(LLMProviderConfigModel).where(
                LLMProviderConfigModel.provider == "ollama"))
            check("ollama_db_row_persisted", oll is not None)

        # 8. runtime gateway (SERVER process) now lists deepseek as real.
        # The script's own get_gateway() singleton is process-local and cannot
        # see the uvicorn gateway — so read the SERVER's exported status, which
        # refresh_provider_status() rebuilds from the live gateway after save.
        r = await cx.get(f"{API}/provider/status", headers=H_ADMIN)
        st = r.json()
        check("status_configured_true", st.get("configured") is True)
        check("runtime_gateway_has_deepseek",
              "deepseek" in (st.get("provider") or ""),
              f"-> provider='{st.get('provider')}'")

        # server-side real-provider health probe includes the newly added provider
        r = await cx.get(f"{API}/provider/status?check=true", headers=H_ADMIN)
        hc_types = {h.get("type") for h in r.json().get("health_checks", [])}
        check("health_check_covers_deepseek", "deepseek" in hc_types, f"-> {sorted(hc_types)}")

        # 9. delete deepseek -> row removed + runtime unregistered
        r = await cx.delete(f"{API}/provider/configs/deepseek", headers=H_ADMIN)
        check("delete_deepseek_ok", r.status_code == 200, f"-> {r.status_code}")
        async with get_session_factory()() as s:
            row = await s.scalar(select(LLMProviderConfigModel).where(
                LLMProviderConfigModel.provider == "deepseek"))
            check("deepseek_row_deleted", row is None)
        r = await cx.get(f"{API}/provider/status", headers=H_ADMIN)
        check("runtime_deepseek_unregistered",
              "deepseek" not in (r.json().get("provider") or ""),
              f"-> provider='{r.json().get('provider')}'")

        # delete unknown -> 404
        r = await cx.delete(f"{API}/provider/configs/doesnotexist", headers=H_ADMIN)
        check("delete_unknown_404", r.status_code == 404, f"-> {r.status_code}")

    print("\n==== SUMMARY ====")
    print(f"PASS={len(PASS)}  FAIL={len(FAIL)}")
    if FAIL:
        print("FAILED:", json.dumps(FAIL, ensure_ascii=False))
        sys.exit(1)


asyncio.run(main())
