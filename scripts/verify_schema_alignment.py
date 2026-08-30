"""Verify that the database schema matches the full ORM metadata.

Compares every table/column declared in Base.metadata against
PRAGMA table_info of the target database and reports any missing
columns. Exit code 0 when the schema is fully aligned.

Usage:
    python scripts/verify_schema_alignment.py            # uses settings DATABASE_URL
    python scripts/verify_schema_alignment.py dev.db     # explicit sqlite file
"""

import sys
from pathlib import Path

# Ensure project root is importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

from sqlalchemy import create_engine

from src.database.base import Base
from src.database import models  # noqa: F401 - registers models on Base.metadata


def main() -> int:
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        from src.core.config import get_settings

        url = get_settings().database_url
        db_path = url.split("///")[-1]

    if not Path(db_path).exists():
        print(f"FAIL: database file not found: {db_path}")
        return 2

    engine = create_engine(f"sqlite:///{db_path}")
    insp = sqlalchemy_inspect(engine)
    conn = sqlite3.connect(db_path)

    missing = []
    tables_checked = 0
    for table in sorted(Base.metadata.tables):
        db_cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if not db_cols:
            # Table itself missing: create_all owns this, report it
            missing.append((table, "<TABLE>", "table missing"))
            continue
        tables_checked += 1
        orm_cols = set(Base.metadata.tables[table].columns.keys())
        for col in sorted(orm_cols - set(db_cols)):
            missing.append((table, col, "column missing"))

    conn.close()
    engine.dispose()

    print(f"ORM tables checked: {tables_checked}")
    if missing:
        print(f"MISSING: {len(missing)}")
        for table, col, reason in missing:
            print(f"  - {table}.{col} ({reason})")
        return 1
    print("MISSING: 0 - schema fully aligned with ORM")
    return 0


def sqlalchemy_inspect(engine):
    from sqlalchemy import inspect

    return inspect(engine)


if __name__ == "__main__":
    sys.exit(main())
