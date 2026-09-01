"""
Y1 Progress Calculator
- Scans repository for capability evidence
- Runs targeted pytest for capability test sets when present
- Performs runtime checks (import app and health endpoints)
- Checks frontend build artifacts
- Computes Y1 progress using fixed weights and G0-G6 gates

Usage:
    python scripts/y1_progress.py

Outputs a human-readable audit table and JSON summary at docs/Y1_EVIDENCE.json
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

# Capability definitions and weights (sum must be 100)
CAPABILITIES = {
    "Goal / Task / Workflow": 15,
    "Execution / Verification / Audit": 12,
    "Knowledge / RAG": 12,
    "AI Employee / Agent": 10,
    "Memory": 8,
    "Model Manager": 8,
    "Communication": 7,
    "Translation": 5,
    "Device / Watch / Robot / Machine Duck": 8,
    "UI / API End-to-End": 7,
    "Reliability / Security / Recovery": 8,
}

# Mapping of capability -> evidence patterns (code globs, unit test globs, integration test globs)
EVIDENCE_MAP = {
    "Goal / Task / Workflow": {
        "code": ["src/ai/goal_service.py", "src/workflow/**", "src/tasks/**"],
        "unit_tests": ["tests/workflow/**", "tests/api/test_workflow_*.py"],
        "integration_tests": ["tests/integration/test_workflow_executor.py", "tests/integration/test_e2e_chain.py"],
        "persistence_tests": ["tests/integration/test_e2e_chain.py"],
    },
    "Execution / Verification / Audit": {
        "code": ["src/identity/audit.py", "src/workflow/**", "src/ai/recovery.py"],
        "unit_tests": ["tests/scheduler/**", "tests/integration/test_failure_recovery_chain.py"],
        "integration_tests": ["tests/integration/test_failure_recovery_chain.py"],
        "persistence_tests": ["tests/integration/test_failure_recovery_chain.py"],
    },
    "Knowledge / RAG": {
        "code": ["src/knowledge/**"],
        "unit_tests": ["tests/knowledge/**"],
        "integration_tests": ["tests/integration/test_rag_pipeline.py", "tests/knowledge/**"],
        "persistence_tests": ["tests/knowledge/test_knowledge_routes_use_persistent_vector_store.py", "tests/knowledge/test_meeting_summary_uses_shared_vector_store.py"],
    },
    "AI Employee / Agent": {
        "code": ["src/workforce/**", "src/ai/**"],
        "unit_tests": ["tests/workforce/**", "tests/ai/**"],
        "integration_tests": ["tests/integration/test_workflow_executor.py", "tests/integration/test_e2e_chain.py"],
        "persistence_tests": ["tests/integration/test_e2e_chain.py"],
    },
    "Memory": {
        "code": ["src/knowledge/memory.py", "src/knowledge/enterprise_memory.py", "src/ai/memory_store.py"],
        "unit_tests": ["tests/api/test_memory_crud.py"],
        "integration_tests": ["tests/integration/test_e2e_chain.py"],
        "persistence_tests": ["tests/api/test_memory_crud.py"],
    },
    "Model Manager": {
        "code": ["src/ai/model_manager.py", "src/ai/providers.py"],
        "unit_tests": ["tests/ai/test_model_manager.py"],
        "integration_tests": [],
        "persistence_tests": [],
    },
    "Communication": {
        "code": ["src/integrations/**"],
        "unit_tests": ["tests/integration/test_platform_execution_mode.py"],
        "integration_tests": ["tests/integration/test_platform_execution_mode.py"],
        "persistence_tests": [],
    },
    "Translation": {
        "code": ["src/integrations/translation.py"],
        "unit_tests": [],
        "integration_tests": [],
        "persistence_tests": [],
    },
    "Device / Watch / Robot / Machine Duck": {
        "code": ["src/devices/**", "src/device/**", "src/robot/**", "src/integrations/device/**"],
        "unit_tests": [],
        "integration_tests": [],
        "persistence_tests": [],
    },
    "UI / API End-to-End": {
        "code": ["frontend/**", "src/api/**"],
        "unit_tests": ["tests/frontend/**"],
        "integration_tests": ["tests/integration/test_e2e_chain.py"],
        "persistence_tests": [],
    },
    "Reliability / Security / Recovery": {
        "code": ["src/security/**", "src/ai/recovery.py"],
        "unit_tests": ["tests/sre/**"],
        "integration_tests": [],
        "persistence_tests": [],
    },
}

# Helper utilities
from glob import glob


def path_exists_any(patterns: List[str]) -> bool:
    for p in patterns:
        matches = glob(str(ROOT / p), recursive=True)
        if matches:
            return True
    return False


def run_pytest_for_patterns(patterns: List[str]) -> bool:
    # Collect existing test files from patterns
    files = []
    for p in patterns:
        files.extend(glob(str(ROOT / p), recursive=True))
    if not files:
        return False
    # Run pytest for these files
    try:
        cmd = [sys.executable, "-m", "pytest", "-q"] + files
        print("Running pytest:", cmd)
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(res.stdout)
        return res.returncode == 0
    except Exception as e:
        print("pytest run failed:", e)
        return False


# Runtime checks

def runtime_health_check() -> bool:
    try:
        # Import the FastAPI app and use TestClient
        from fastapi.testclient import TestClient
        from src.api.app import app
        client = TestClient(app)
        r = client.get("/")
        ok = r.status_code == 200
        print("Root route / status:", r.status_code)
        # try health ping
        ping = client.get("/api/v1/health/ping")
        print("Health ping status:", ping.status_code)
        return ok and ping.status_code == 200
    except Exception as e:
        print("runtime_health_check failed:", e)
        return False


def frontend_build_check() -> bool:
    dist = ROOT / "frontend" / "dist"
    return dist.exists() and any(dist.iterdir())


def assess_capability(name: str, weight: int) -> Dict:
    mapping = EVIDENCE_MAP.get(name, {})
    result = {"G0": True}

    # G1: Implementation - code files exist
    code_patterns = mapping.get("code", [])
    result["G1"] = path_exists_any(code_patterns)

    # G2: Unit tests
    unit_patterns = mapping.get("unit_tests", [])
    result["G2"] = run_pytest_for_patterns(unit_patterns) if unit_patterns else False

    # G3: Integration tests
    int_patterns = mapping.get("integration_tests", [])
    result["G3"] = run_pytest_for_patterns(int_patterns) if int_patterns else False

    # G4: Runtime verification - require app health and, for some capabilities, frontend
    if name == "UI / API End-to-End":
        result["G4"] = frontend_build_check() and runtime_health_check()
    else:
        result["G4"] = runtime_health_check()

    # G5: Persistence/recovery - mark True if specific persistence tests exist and pass
    pers_patterns = mapping.get("persistence_tests", [])
    result["G5"] = run_pytest_for_patterns(pers_patterns) if pers_patterns else False

    # G6: Blueprint acceptance - require all G1..G5 True
    result["G6"] = all(result.get(g, False) for g in ["G1", "G2", "G3", "G4", "G5"])

    return result


def compute_progress(cap_gates: Dict[str, Dict]) -> Dict:
    total = 0.0
    per_cap = {}
    for cap, weight in CAPABILITIES.items():
        gates = cap_gates[cap]
        passed = 0
        for g in ["G1", "G2", "G3", "G4", "G5", "G6"]:
            if gates.get(g):
                passed += 1
        score = passed / 6.0
        contrib = weight * score
        per_cap[cap] = {
            "weight": weight,
            "passed_gates": passed,
            "score": score,
            "contrib": contrib,
            "gates": gates,
        }
        total += contrib
    return {"total": total, "details": per_cap}


def main():
    cap_gates = {}
    print("Scanning capabilities and running targeted checks...\n")
    for cap, weight in CAPABILITIES.items():
        print(f"Assessing: {cap} (weight={weight})")
        gates = assess_capability(cap, weight)
        cap_gates[cap] = gates
        print(f"Gates for {cap}: {gates}\n")

    progress = compute_progress(cap_gates)

    # Output audit table
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Y1 PROGRESS AUDIT")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    print(f"Overall Progress: {progress['total']:.2f} / 100.00")
    print("\nCapability                          Weight   PassedGates   Score(%)   Contrib")
    print("--------------------------------------------------------------------")
    for cap, data in progress["details"].items():
        print(f"{cap:35} {data['weight']:6}     {data['passed_gates']:3}         {data['score']*100:6.2f}    {data['contrib']:6.2f}")

    # Save JSON evidence
    out = {
        "summary": {"overall": progress["total"]},
        "capabilities": progress["details"],
    }

    # Add Model Manager persisted file evidence when present
    try:
        from pathlib import Path
        mm_path = Path(os.environ.get("MODEL_REGISTRY_DIR", "data")) / "model_registry.json"
        if mm_path.exists():
            with open(mm_path, "r", encoding="utf-8") as mf:
                sample = mf.read(2048)
            out["capabilities"]["Model Manager"]["evidence"] = {
                "persist_file": str(mm_path),
                "sample": sample,
            }
        else:
            out["capabilities"]["Model Manager"]["evidence"] = {
                "persist_file": str(mm_path),
                "exists": False,
            }
    except Exception as e:
        out["capabilities"]["Model Manager"]["evidence_error"] = str(e)

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    with open(docs / "Y1_EVIDENCE.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\nEvidence saved to docs/Y1_EVIDENCE.json")


if __name__ == '__main__':
    main()
