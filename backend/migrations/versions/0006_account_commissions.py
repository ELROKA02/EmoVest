"""Store per-account commission settings and operation net-result snapshots.

Revision ID: 0006_account_commissions
Revises: 0005_ai_provider_profiles
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_account_commissions"
down_revision = "0005_ai_provider_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cuenta_trading",
        sa.Column("tipo_comision", sa.String(length=20), nullable=False, server_default="sin_comision"),
    )
    op.add_column(
        "cuenta_trading",
        sa.Column("valor_comision", sa.DECIMAL(precision=20, scale=6), nullable=False, server_default="0"),
    )
    op.add_column("operacion", sa.Column("resultado_bruto", sa.DECIMAL(precision=20, scale=6), nullable=True))
    op.add_column(
        "operacion",
        sa.Column("comisiones", sa.DECIMAL(precision=20, scale=6), nullable=False, server_default="0"),
    )
    # Existing results were historically stored without commission deductions.
    op.execute("UPDATE operacion SET resultado_bruto = resultado, comisiones = 0")


def downgrade() -> None:
    op.drop_column("operacion", "comisiones")
    op.drop_column("operacion", "resultado_bruto")
    op.drop_column("cuenta_trading", "valor_comision")
    op.drop_column("cuenta_trading", "tipo_comision")
