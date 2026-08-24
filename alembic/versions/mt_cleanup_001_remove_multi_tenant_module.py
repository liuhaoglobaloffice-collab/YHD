"""Remove multi_tenant module - 6 tables only

Revision ID: mt_cleanup_001
Revises: bc4420b32d53
Create Date: 2026-08-24 00:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'mt_cleanup_001'
down_revision: Union[str, Sequence[str], None] = 'bc4420b32d53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove multi_tenant module tables only.
    
    Deletes 6 tables:
    1. accounts
    2. api_configurations
    3. token_usage_stats
    4. token_consumption_logs
    5. master_stealth_permissions
    6. master_stealth_operations
    """
    # Check if tables exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop multi_tenant tables in correct order (handle foreign keys)
    
    # 1. Drop master_stealth_operations (references master_stealth_permissions)
    if 'master_stealth_operations' in existing_tables:
        op.execute("DROP TABLE IF EXISTS master_stealth_operations")
        print("[OK] Dropped table: master_stealth_operations")
    
    # 2. Drop master_stealth_permissions (references accounts)
    if 'master_stealth_permissions' in existing_tables:
        op.execute("DROP TABLE IF EXISTS master_stealth_permissions")
        print("[OK] Dropped table: master_stealth_permissions")
    
    # 3. Drop token_consumption_logs (references accounts)
    if 'token_consumption_logs' in existing_tables:
        op.execute("DROP TABLE IF EXISTS token_consumption_logs")
        print("[OK] Dropped table: token_consumption_logs")
    
    # 4. Drop token_usage_stats (references accounts)
    if 'token_usage_stats' in existing_tables:
        op.execute("DROP TABLE IF EXISTS token_usage_stats")
        print("[OK] Dropped table: token_usage_stats")
    
    # 5. Drop api_configurations (references accounts)
    if 'api_configurations' in existing_tables:
        op.execute("DROP TABLE IF EXISTS api_configurations")
        print("[OK] Dropped table: api_configurations")
    
    # 6. Drop accounts (parent table)
    if 'accounts' in existing_tables:
        op.execute("DROP TABLE IF EXISTS accounts")
        print("[OK] Dropped table: accounts")
    
    print("")
    print("[OK] Multi-tenant module cleanup complete")
    print("   Removed 6 tables: accounts, api_configurations, token_usage_stats,")
    print("   token_consumption_logs, master_stealth_permissions, master_stealth_operations")


def downgrade() -> None:
    """
    Recreate multi_tenant tables.
    
    Note: This will recreate empty tables. Data will NOT be restored.
    """
    # Recreate accounts table
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('master_account_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_accounts_id', 'accounts', ['id'])
    op.create_index('ix_accounts_username', 'accounts', ['username'])
    op.create_index('ix_accounts_account_type', 'accounts', ['account_type'])
    op.create_index('ix_accounts_master_account_id', 'accounts', ['master_account_id'])
    
    # Recreate api_configurations table
    op.create_table(
        'api_configurations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('account_id', sa.String(36), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_api_configurations_id', 'api_configurations', ['id'])
    op.create_index('ix_api_configurations_account_id', 'api_configurations', ['account_id'])
    
    # Recreate token_usage_stats table
    op.create_table(
        'token_usage_stats',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('account_id', sa.String(36), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_token_usage_stats_id', 'token_usage_stats', ['id'])
    op.create_index('ix_token_usage_stats_account_id', 'token_usage_stats', ['account_id'])
    
    # Recreate token_consumption_logs table
    op.create_table(
        'token_consumption_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('account_id', sa.String(36), nullable=False),
        sa.Column('tokens_consumed', sa.Integer(), nullable=False),
        sa.Column('consumed_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_token_consumption_logs_id', 'token_consumption_logs', ['id'])
    op.create_index('ix_token_consumption_logs_account_id', 'token_consumption_logs', ['account_id'])
    op.create_index('ix_token_consumption_logs_consumed_at', 'token_consumption_logs', ['consumed_at'])
    
    # Recreate master_stealth_permissions table
    op.create_table(
        'master_stealth_permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('master_account_id', sa.String(36), nullable=False),
        sa.Column('sub_account_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_master_stealth_permissions_id', 'master_stealth_permissions', ['id'])
    op.create_index('ix_master_stealth_permissions_master_account_id', 'master_stealth_permissions', ['master_account_id'])
    op.create_index('ix_master_stealth_permissions_sub_account_id', 'master_stealth_permissions', ['sub_account_id'])
    
    # Recreate master_stealth_operations table
    op.create_table(
        'master_stealth_operations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('master_account_id', sa.String(36), nullable=False),
        sa.Column('target_account_id', sa.String(36), nullable=False),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('operated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_master_stealth_operations_id', 'master_stealth_operations', ['id'])
    op.create_index('ix_master_stealth_operations_master_account_id', 'master_stealth_operations', ['master_account_id'])
    op.create_index('ix_master_stealth_operations_target_account_id', 'master_stealth_operations', ['target_account_id'])
    op.create_index('ix_master_stealth_operations_operation_type', 'master_stealth_operations', ['operation_type'])
    op.create_index('ix_master_stealth_operations_operated_at', 'master_stealth_operations', ['operated_at'])
    
    print("[OK] Multi-tenant tables recreated (empty)")
