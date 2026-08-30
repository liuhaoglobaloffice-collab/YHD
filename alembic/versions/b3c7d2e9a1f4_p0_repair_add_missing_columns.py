"""p0_repair_add_missing_columns

Adds the 13 columns that drifted out of dev.db (schema drift P0-A).
Column types mirror the ORM definitions:
    users -> src/identity/models.py
    tasks / agent_memories -> src/database/models.py
    leads -> src/crm/models.py
    platform_messages -> src/integrations/models.py

The migration is idempotent: each column is checked with PRAGMA
table_info before ALTER TABLE ADD COLUMN, so it can run on databases
that were already healed by init_database() lightweight migrations.

Revision ID: b3c7d2e9a1f4
Revises: 821f4be8970c
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c7d2e9a1f4'
down_revision: Union[str, Sequence[str], None] = '821f4be8970c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, column type DDL, ORM-backed DEFAULT backfill)
# sa.Column type kept for metadata parity; DDL string used for ALTER so
# SQLite dialect renders NOT NULL DEFAULT exactly as the lightweight
# heal path in src/api/dependencies/database.py does.
NEW_COLUMNS = [
    ("users", "business_role", "VARCHAR(30)", None),
    ("users", "data_scope", "VARCHAR(20)", "'self'"),
    ("users", "permissions_config", "JSON", None),
    ("tasks", "retry_count", "INTEGER", "0"),
    ("tasks", "max_retries", "INTEGER", "3"),
    ("agent_memories", "memory_level", "VARCHAR(20)", "'short_term'"),
    ("agent_memories", "importance", "FLOAT", "0.5"),
    ("agent_memories", "is_core", "BOOLEAN", "0"),
    ("agent_memories", "expires_at", "DATETIME", None),
    ("agent_memories", "last_accessed_at", "DATETIME", None),
    ("agent_memories", "access_count", "INTEGER", "0"),
    ("leads", "source_type", "VARCHAR(20)", "'MOCK'"),
    ("platform_messages", "source_type", "VARCHAR(20)", "'MOCK'"),
]


def _existing_columns(bind, table: str) -> set:
    result = bind.execute(sa.text(f"PRAGMA table_info({table})"))
    return {row[1] for row in result.fetchall()}


def upgrade() -> None:
    """Add missing columns, skipping ones that already exist."""
    bind = op.get_bind()
    for table, column, ddl_type, default in NEW_COLUMNS:
        cols = _existing_columns(bind, table)
        if column in cols:
            continue
        if default is not None:
            statement = (
                f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type} "
                f"NOT NULL DEFAULT {default}"
            )
        else:
            statement = f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"
        bind.execute(sa.text(statement))


def downgrade() -> None:
    """Drop the columns added by upgrade (SQLite rebuild path)."""
    bind = op.get_bind()
    for table, column, _ddl_type, _default in reversed(NEW_COLUMNS):
        cols = _existing_columns(bind, table)
        if column not in cols:
            continue
        bind.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN {column}"))
