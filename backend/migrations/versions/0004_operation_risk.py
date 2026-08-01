"""Store the risk snapshot calculated for each operation.

Revision ID: 0004_operation_risk
Revises: 0003_trading_profile
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_operation_risk"
down_revision = "0003_trading_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operacion", sa.Column("saldo_referencia_riesgo", sa.DECIMAL(precision=20, scale=6), nullable=True))
    op.add_column("operacion", sa.Column("riesgo_importe", sa.DECIMAL(precision=20, scale=6), nullable=True))
    op.add_column("operacion", sa.Column("riesgo_porcentaje", sa.DECIMAL(precision=10, scale=4), nullable=True))


def downgrade() -> None:
    op.drop_column("operacion", "riesgo_porcentaje")
    op.drop_column("operacion", "riesgo_importe")
    op.drop_column("operacion", "saldo_referencia_riesgo")
