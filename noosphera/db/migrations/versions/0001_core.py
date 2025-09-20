from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure control-plane schema and pgvector extension
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    tenant_status = postgresql.ENUM("active", "suspended", name="tenant_status", schema="core")
    key_status = postgresql.ENUM("active", "revoked", name="key_status", schema="core")
    # IMPORTANT: prevent auto-creation on table create; we create explicitly with checkfirst
    tenant_status = postgresql.ENUM(
        "active", "suspended", name="tenant_status", schema="core", create_type=False
    )
    key_status = postgresql.ENUM(
        "active", "revoked", name="key_status", schema="core", create_type=False
    )
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("db_schema_name", sa.Text(), nullable=False),
        sa.Column("status", tenant_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_tenants_name"),
        sa.UniqueConstraint("db_schema_name", name="uq_tenants_schema"),
        schema="core",
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("status", key_status, nullable=False, server_default="active"),        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["core.tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_prefix", name="uq_api_keys_prefix"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_api_keys_tenant_name"),
        sa.Index("ix_api_keys_tenant_id", "tenant_id"),
        schema="core",
    )


def downgrade() -> None:
    op.drop_table("api_keys", schema="core")
    op.drop_table("tenants", schema="core")
    op.execute('DROP TYPE IF EXISTS core.key_status')
    op.execute('DROP TYPE IF EXISTS core.tenant_status')
