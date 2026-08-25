#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./verify_metrics.db")
METRICS_PERSIST = os.environ.get("METRICS_PERSIST", "0")


def sqlite_path_from_url(database_url: str) -> Path:
    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme!r}")
    if parsed.path in ("", ":memory:"):
        return Path(":memory:")

    path_value = parsed.path
    if path_value.startswith("/") and not path_value.startswith("//"):
        path_value = path_value.lstrip("/")

    database_file = Path(path_value)
    if not database_file.is_absolute():
        database_file = (Path.cwd() / database_file).resolve()
    return database_file


def ensure_db_file(path: Path) -> None:
    if path == Path(":memory:"):
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    if METRICS_PERSIST != "1":
        print("METRICS_PERSIST is not enabled; skipping persistence verification.")
        return 0

    database_path = sqlite_path_from_url(DATABASE_URL)
    ensure_db_file(database_path)

    conn = sqlite3.connect(str(database_path))
    conn.execute("CREATE TABLE IF NOT EXISTS provider_metric_samples (id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, model TEXT, timestamp TEXT, latency_ms REAL, success_rate REAL)")

    sample = (
        "openai",
        "gpt-4o-mini",
        "2026-08-25T00:00:00Z",
        220.5,
        0.99,
    )
    conn.execute(
        "INSERT INTO provider_metric_samples (provider, model, timestamp, latency_ms, success_rate) VALUES (?, ?, ?, ?, ?)",
        sample,
    )
    conn.commit()

    rows = conn.execute(
        "SELECT provider, model, timestamp, latency_ms, success_rate FROM provider_metric_samples ORDER BY id DESC LIMIT 5"
    ).fetchall()
    print(f"DATABASE_URL={DATABASE_URL}")
    print(f"METRICS_PERSIST={METRICS_PERSIST}")
    print(f"persisted_rows={len(rows)}")
    for row in rows:
        print(f"sample={row}")

    conn.close()

    if not rows:
        raise RuntimeError("Persistence verification failed: no rows were written to the database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
