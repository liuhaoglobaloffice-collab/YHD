"""initial_schema

Baseline migration capturing the current schema as managed by
Base.metadata.create_all() in production.  This is a blank revision
because the project auto-creates tables on startup.

Future schema changes (e.g. new columns, indexes) must be added as
new migration scripts under alembic/versions/ so that production
deployments can apply them via ``alembic upgrade head``.

Revision ID: 821f4be8970c
Revises: 
Create Date: 2026-08-29 13:56:13.940040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '821f4be8970c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Baseline — tables are auto-created by Base.metadata.create_all()
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
