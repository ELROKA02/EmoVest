"""Store the trading context supplied by each user.

Revision ID: 0003_trading_profile
Revises: 0002_local_runtime
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_trading_profile"
down_revision = "0002_local_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("estrategia_trading", sa.Text(), nullable=True))
    op.add_column("usuarios", sa.Column("plan_trading", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "plan_trading")
    op.drop_column("usuarios", "estrategia_trading")
