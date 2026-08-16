"""Keep local and remote AI profiles independently per use case.

Revision ID: 0005_ai_provider_profiles
Revises: 0004_operation_risk
"""
from alembic import op


revision = "0005_ai_provider_profiles"
down_revision = "0004_operation_risk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite cannot drop the unnamed UNIQUE constraint from the first schema in
    # place. Rebuild the small settings table while retaining every active
    # configuration as the initial profile for its provider.
    op.execute(
        """
        CREATE TABLE ai_settings_new (
            id INTEGER NOT NULL PRIMARY KEY,
            use_case VARCHAR(50) NOT NULL,
            provider VARCHAR(50) NOT NULL,
            model VARCHAR(120) NOT NULL,
            base_url VARCHAR(255) NOT NULL,
            install_mode VARCHAR(50) NOT NULL DEFAULT 'manual',
            is_active BOOLEAN NOT NULL DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ai_settings_use_case_provider UNIQUE (use_case, provider)
        )
        """
    )
    op.execute(
        """
        INSERT INTO ai_settings_new
            (id, use_case, provider, model, base_url, install_mode, is_active, updated_at)
        SELECT id, use_case, provider, model, base_url, install_mode, 1, updated_at
        FROM ai_settings
        """
    )
    op.drop_table("ai_settings")
    op.rename_table("ai_settings_new", "ai_settings")
    op.create_index("ix_ai_settings_id", "ai_settings", ["id"], unique=False)


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE ai_settings_old (
            id INTEGER NOT NULL PRIMARY KEY,
            use_case VARCHAR(50) NOT NULL UNIQUE,
            provider VARCHAR(50) NOT NULL,
            model VARCHAR(120) NOT NULL,
            base_url VARCHAR(255) NOT NULL,
            install_mode VARCHAR(50) NOT NULL DEFAULT 'manual',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        INSERT INTO ai_settings_old (id, use_case, provider, model, base_url, install_mode, updated_at)
        SELECT id, use_case, provider, model, base_url, install_mode, updated_at
        FROM ai_settings
        WHERE is_active = 1
        """
    )
    op.drop_table("ai_settings")
    op.rename_table("ai_settings_old", "ai_settings")
    op.create_index("ix_ai_settings_id", "ai_settings", ["id"], unique=False)
