"""Seed the P0-D AI employee roster into dev.db.

Implements SPEC-P0-REPAIR section 8: a 7-person roster across 5
departments, all bound to the local Ollama provider (qwen2.5:3b) and
set to status=active.

The script is idempotent: employees are matched by name; existing rows
are updated in place, missing rows are created. It can be re-run at
any time to restore the target roster.

provider_config persistence note: the ORM round-trip
(converters.model_to_employee) reconstructs provider_config from the
provider/model columns, so both columns AND the config JSON column are
written to keep the database self-describing.

Usage:
    python scripts/seed_workforce_roster.py            # default dev.db
    python scripts/seed_workforce_roster.py other.db   # explicit sqlite file
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROVIDER = "ollama"
MODEL = "qwen2.5:3b"
PROVIDER_CONFIG = {"provider": PROVIDER, "model": MODEL}

# Target roster per SPEC-P0-REPAIR section 8.
# agent_type must be one of the 6 internal agents (src/ai/agents.py);
# the provider_config override at execution time replaces the
# provider/model, so the agent type only selects the agent profile.
ROSTER = [
    {
        "name": "鎏灏核心助理",
        "department": "ceo_office",
        "position": "ceo_assistant",
        "agent_type": "gpt",
        "description": "老板的核心助理，负责战略决策支持与任务统筹，绑定本地 Ollama 模型。",
    },
    {
        "name": "Gemini - Research Officer",
        "department": "research",
        "position": "market_researcher",
        "agent_type": "gemini",
        "description": "市场调研专员，负责目标市场分析与竞争对手研究。",
    },
    {
        "name": "Kimi - Chinese Research Officer",
        "department": "research",
        "position": "product_researcher",
        "agent_type": "kimi",
        "description": "产品调研专员，负责中文产品资料研究与选品分析。",
    },
    {
        "name": "Qwen - Marketing Specialist",
        "department": "marketing",
        "position": "marketing_specialist",
        "agent_type": "deepseek",
        "description": "营销专员，负责营销内容创作、社媒帖子与推广文案。",
    },
    {
        "name": "金牌外贸销售",
        "department": "sales",
        "position": "sales_representative",
        "agent_type": "grok",
        "description": "外贸销售代表，负责客户开发与询盘跟进。",
    },
    {
        "name": "AI 谈判专家",
        "department": "sales",
        "position": "account_manager",
        "agent_type": "gemini",
        "description": "大客户经理，负责商务谈判与客户关系维护。",
    },
    {
        "name": "跨境运营顾问",
        "department": "operations",
        "position": "operations_coordinator",
        "agent_type": "kimi",
        "description": "跨境运营协调员，负责订单履约与运营流程协调。",
    },
]


def seed(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    try:
        now = "2026-08-30 00:00:00"
        for emp in ROSTER:
            row = con.execute(
                "SELECT id FROM ai_employees WHERE name = ?", (emp["name"],)
            ).fetchone()
            if row:
                con.execute(
                    """
                    UPDATE ai_employees
                    SET department = ?, position = ?, description = ?,
                        agent_type = ?, provider = ?, model = ?, config = ?,
                        status = 'active', updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        emp["department"],
                        emp["position"],
                        emp["description"],
                        emp["agent_type"],
                        PROVIDER,
                        MODEL,
                        json.dumps(PROVIDER_CONFIG),
                        now,
                        row[0],
                    ),
                )
                action = "updated"
            else:
                con.execute(
                    """
                    INSERT INTO ai_employees
                        (id, name, department, position, description, agent_type,
                         provider, model, config, status, meta, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        str(__import__("uuid").uuid4()),
                        emp["name"],
                        emp["department"],
                        emp["position"],
                        emp["description"],
                        emp["agent_type"],
                        PROVIDER,
                        MODEL,
                        json.dumps(PROVIDER_CONFIG),
                        json.dumps({}),
                        now,
                        now,
                    ),
                )
                action = "created"
            print(f"  {action}: {emp['name']} ({emp['department']}/{emp['position']})")
        con.commit()
    finally:
        con.close()


def verify(db_path: str) -> bool:
    """All 7 roster employees active and bound to ollama."""
    con = sqlite3.connect(db_path)
    try:
        ok = True
        for emp in ROSTER:
            row = con.execute(
                "SELECT status, provider, model, config FROM ai_employees WHERE name = ?",
                (emp["name"],),
            ).fetchone()
            if not row:
                print(f"  MISSING: {emp['name']}")
                ok = False
                continue
            status, provider, model, config = row
            cfg = json.loads(config) if config else {}
            bound = (
                status == "active"
                and provider == PROVIDER
                and model == MODEL
                and cfg.get("provider") == PROVIDER
                and cfg.get("model") == MODEL
            )
            if not bound:
                print(f"  NOT BOUND: {emp['name']} -> status={status} provider={provider} model={model}")
                ok = False
        return ok
    finally:
        con.close()


def main() -> int:
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        from src.core.config import get_settings

        db_path = get_settings().database_url.split("///")[-1]

    if not Path(db_path).exists():
        print(f"FAIL: database file not found: {db_path}")
        return 2

    sys.path.insert(0, str(PROJECT_ROOT))

    print(f"Seeding workforce roster into {db_path}")
    seed(db_path)
    print("Verifying...")
    if verify(db_path):
        print("OK: 7 employees active, all bound to ollama/qwen2.5:3b")
        return 0
    print("FAIL: roster verification failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
