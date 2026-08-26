"""Add partial executions, account movements and import audit data.

Revision ID: 0007_operation_executions
Revises: 0006_account_commissions
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_operation_executions"
down_revision = "0006_account_commissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operacion", sa.Column("swap", sa.DECIMAL(20, 6), nullable=False, server_default="0"))
    op.add_column("operacion", sa.Column("tasas", sa.DECIMAL(20, 6), nullable=False, server_default="0"))
    op.add_column("operacion", sa.Column("estado", sa.String(24), nullable=False, server_default="OPEN"))
    op.add_column("operacion", sa.Column("cantidad_abierta", sa.DECIMAL(20, 6), nullable=False, server_default="0"))
    op.add_column("operacion", sa.Column("fecha_cierre", sa.DateTime(), nullable=True))
    with op.batch_alter_table("operacion") as batch_op:
        batch_op.create_check_constraint(
            "ck_operacion_estado",
            "estado IN ('OPEN', 'PARTIALLY_CLOSED', 'CLOSED')",
        )

    op.create_table(
        "importacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_cuenta", sa.Integer(), nullable=False),
        sa.Column("proveedor", sa.String(32), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("cuenta_origen_hash", sa.String(64), nullable=False),
        sa.Column("broker", sa.String(120), nullable=True),
        sa.Column("zona_horaria", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["id_cuenta"], ["cuenta_trading.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_cuenta", "proveedor", "fingerprint", name="uq_importacion_archivo"),
    )
    op.create_index(op.f("ix_importacion_id"), "importacion", ["id"], unique=False)
    op.create_table(
        "importacion_fila",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_importacion", sa.Integer(), nullable=False),
        sa.Column("id_cuenta", sa.Integer(), nullable=False),
        sa.Column("numero_fila", sa.Integer(), nullable=False),
        sa.Column("deal_ticket", sa.String(80), nullable=True),
        sa.Column("source_key", sa.String(128), nullable=False),
        sa.Column("clasificacion", sa.String(32), nullable=False),
        sa.Column("normalized_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["id_importacion"], ["importacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["id_cuenta"], ["cuenta_trading.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_cuenta", "source_key", name="uq_importacion_fila_source"),
        sa.UniqueConstraint("id_importacion", "numero_fila", name="uq_importacion_fila_numero"),
    )
    op.create_index(op.f("ix_importacion_fila_id"), "importacion_fila", ["id"], unique=False)
    op.create_table(
        "operacion_ejecucion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_operacion", sa.Integer(), nullable=False),
        sa.Column("source_row_id", sa.Integer(), nullable=True),
        sa.Column("source_leg", sa.String(16), nullable=True),
        sa.Column("rol", sa.String(8), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(), nullable=False),
        sa.Column("cantidad", sa.DECIMAL(20, 6), nullable=False),
        sa.Column("precio", sa.DECIMAL(20, 6), nullable=True),
        sa.Column("resultado_bruto", sa.DECIMAL(20, 6), nullable=True),
        sa.Column("impacto_comision", sa.DECIMAL(20, 6), nullable=False, server_default="0"),
        sa.Column("impacto_swap", sa.DECIMAL(20, 6), nullable=False, server_default="0"),
        sa.Column("impacto_tasa", sa.DECIMAL(20, 6), nullable=False, server_default="0"),
        sa.Column("resultado_neto", sa.DECIMAL(20, 6), nullable=False, server_default="0"),
        sa.Column("origen", sa.String(16), nullable=False, server_default="CALCULATED"),
        sa.CheckConstraint("cantidad > 0", name="ck_operacion_ejecucion_cantidad"),
        sa.CheckConstraint("origen IN ('CALCULATED', 'MANUAL', 'BROKER', 'LEGACY')", name="ck_operacion_ejecucion_origen"),
        sa.CheckConstraint("rol IN ('ENTRY', 'EXIT')", name="ck_operacion_ejecucion_rol"),
        sa.ForeignKeyConstraint(["id_operacion"], ["operacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_row_id"], ["importacion_fila.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operacion_ejecucion_id"), "operacion_ejecucion", ["id"], unique=False)
    op.create_index("ix_operacion_ejecucion_operacion_fecha", "operacion_ejecucion", ["id_operacion", "fecha_hora", "id"], unique=False)
    op.create_table(
        "movimiento_cuenta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_cuenta", sa.Integer(), nullable=False),
        sa.Column("source_row_id", sa.Integer(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("importe", sa.DECIMAL(20, 6), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.CheckConstraint("tipo IN ('DEPOSIT', 'WITHDRAWAL', 'COMMISSION', 'FEE', 'ADJUSTMENT')", name="ck_movimiento_cuenta_tipo"),
        sa.ForeignKeyConstraint(["id_cuenta"], ["cuenta_trading.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_row_id"], ["importacion_fila.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_movimiento_cuenta_id"), "movimiento_cuenta", ["id"], unique=False)
    op.create_index("ix_movimiento_cuenta_cuenta_fecha", "movimiento_cuenta", ["id_cuenta", "fecha_hora", "id"], unique=False)

    op.execute("""
        UPDATE operacion
        SET estado = CASE WHEN resultado IS NOT NULL OR precio_salida IS NOT NULL THEN 'CLOSED' ELSE 'OPEN' END,
            cantidad_abierta = CASE WHEN resultado IS NOT NULL OR precio_salida IS NOT NULL THEN 0 ELSE cantidad END,
            fecha_cierre = CASE WHEN resultado IS NOT NULL OR precio_salida IS NOT NULL THEN fecha_hora ELSE NULL END
    """)
    op.execute("""
        INSERT INTO operacion_ejecucion
            (id_operacion, rol, fecha_hora, cantidad, precio, resultado_bruto,
             impacto_comision, impacto_swap, impacto_tasa, resultado_neto, origen)
        SELECT id, 'ENTRY', COALESCE(fecha_hora, CURRENT_TIMESTAMP), cantidad, precio_entrada, NULL,
               -COALESCE(comisiones, 0), 0, 0,
               CASE WHEN resultado IS NOT NULL OR precio_salida IS NOT NULL THEN -COALESCE(comisiones, 0) ELSE 0 END,
               'LEGACY'
        FROM operacion
    """)
    op.execute("""
        INSERT INTO operacion_ejecucion
            (id_operacion, rol, fecha_hora, cantidad, precio, resultado_bruto,
             impacto_comision, impacto_swap, impacto_tasa, resultado_neto, origen)
        SELECT id, 'EXIT', COALESCE(fecha_hora, CURRENT_TIMESTAMP), cantidad, precio_salida, resultado_bruto,
               0, 0, 0, COALESCE(resultado_bruto, resultado, 0), 'LEGACY'
        FROM operacion
        WHERE resultado IS NOT NULL OR precio_salida IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_movimiento_cuenta_cuenta_fecha", table_name="movimiento_cuenta")
    op.drop_index(op.f("ix_movimiento_cuenta_id"), table_name="movimiento_cuenta")
    op.drop_table("movimiento_cuenta")
    op.drop_index("ix_operacion_ejecucion_operacion_fecha", table_name="operacion_ejecucion")
    op.drop_index(op.f("ix_operacion_ejecucion_id"), table_name="operacion_ejecucion")
    op.drop_table("operacion_ejecucion")
    op.drop_index(op.f("ix_importacion_fila_id"), table_name="importacion_fila")
    op.drop_table("importacion_fila")
    op.drop_index(op.f("ix_importacion_id"), table_name="importacion")
    op.drop_table("importacion")
    with op.batch_alter_table("operacion") as batch_op:
        batch_op.drop_constraint("ck_operacion_estado", type_="check")
    op.drop_column("operacion", "fecha_cierre")
    op.drop_column("operacion", "cantidad_abierta")
    op.drop_column("operacion", "estado")
    op.drop_column("operacion", "tasas")
    op.drop_column("operacion", "swap")
