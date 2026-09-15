"""Create encrypted OAuth credential storage.

Revision ID: 0010_oauth_credentials
Revises: 0009_execution_audit_events
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_oauth_credentials"
down_revision = "0009_execution_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_credentials",
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("plugin_id", sa.Text(), nullable=False),
        sa.Column("plugin_version", sa.Text(), nullable=False),
        sa.Column("capability_name", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.LargeBinary(), nullable=False),
        sa.Column("encryption_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("cipher_version", sa.String(length=32), nullable=False),
        sa.Column("granted_scopes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "refresh_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cipher_version = 'aesgcm-v1'",
            name="ck_oauth_credentials_cipher_version",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'reauthorization_required')",
            name="ck_oauth_credentials_status",
        ),
        sa.PrimaryKeyConstraint("profile_id"),
    )


def downgrade() -> None:
    op.drop_table("oauth_credentials")
