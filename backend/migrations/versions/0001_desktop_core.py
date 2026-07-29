"""Create the desktop core schema.

Revision ID: 0001_desktop_core
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_desktop_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trofeos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=True),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trofeos_id"), "trofeos", ["id"], unique=False)

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=True),
        sa.Column("contrasena", sa.String(length=255), nullable=False),
        sa.Column("correo_electronico", sa.String(length=100), nullable=False),
        sa.Column(
            "fecha_registro",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_usuarios_correo_electronico"),
        "usuarios",
        ["correo_electronico"],
        unique=True,
    )
    op.create_index(op.f("ix_usuarios_id"), "usuarios", ["id"], unique=False)

    op.create_table(
        "notificacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(), nullable=True),
        sa.Column("mensaje", sa.String(length=255), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notificacion_id"), "notificacion", ["id"], unique=False)

    op.create_table(
        "suscripcion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column(
            "tipo_plan",
            sa.Enum(
                "FREE",
                "PRO",
                "PARTNER",
                name="subscription_plan",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "fecha_inicio",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("fecha_expiracion", sa.DateTime(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("precio", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_usuario"),
    )
    op.create_index(op.f("ix_suscripcion_id"), "suscripcion", ["id"], unique=False)

    op.create_table(
        "usuario_trofeo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_trofeo", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id_trofeo"], ["trofeos.id"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_usuario_trofeo_id"),
        "usuario_trofeo",
        ["id"],
        unique=False,
    )

    op.create_table(
        "cuenta_trading",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("nombre_cuenta", sa.String(length=50), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("saldo_inicial", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("saldo_actual", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column(
            "divisa",
            sa.Enum(
                "EUR",
                "USD",
                name="trading_currency",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cuenta_trading_id"),
        "cuenta_trading",
        ["id"],
        unique=False,
    )

    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("use_case", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column(
            "install_mode",
            sa.String(length=50),
            server_default="manual",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("use_case"),
    )
    op.create_index(op.f("ix_ai_settings_id"), "ai_settings", ["id"], unique=False)

    op.create_table(
        "alerta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_cuenta", sa.Integer(), nullable=True),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("umbral", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["id_cuenta"], ["cuenta_trading.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerta_id"), "alerta", ["id"], unique=False)

    op.create_table(
        "estadistica",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_cuenta", sa.Integer(), nullable=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("total_operaciones", sa.Integer(), nullable=False),
        sa.Column("operaciones_ganadoras", sa.Integer(), nullable=False),
        sa.Column("operaciones_perdedoras", sa.Integer(), nullable=False),
        sa.Column("profit_total", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("profit_promedio", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("max_drawdown", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("rr_promedio", sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.ForeignKeyConstraint(["id_cuenta"], ["cuenta_trading.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_estadistica_id"), "estadistica", ["id"], unique=False)

    op.create_table(
        "operacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_cuenta", sa.Integer(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(), nullable=True),
        sa.Column(
            "tipo_operacion",
            sa.Enum(
                "LONG",
                "SHORT",
                name="operation_side",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("cantidad", sa.DECIMAL(precision=20, scale=6), nullable=False),
        sa.Column("activo", sa.String(length=10), nullable=False),
        sa.Column("precio_entrada", sa.DECIMAL(precision=20, scale=6), nullable=False),
        sa.Column("precio_salida", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("notas", sa.String(length=255), nullable=True),
        sa.Column("stop_loss", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("take_profit", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("resultado", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("ratio_rr", sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column("nivel_confianza", sa.Integer(), nullable=True),
        sa.Column("screenshot", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["id_cuenta"], ["cuenta_trading.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operacion_id"), "operacion", ["id"], unique=False)

    op.create_table(
        "registro_emocional",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_operacion", sa.Integer(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(), nullable=True),
        sa.Column("texto_entrada", sa.String(length=255), nullable=True),
        sa.Column("confianza", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("duda", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("euforia", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("miedo", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column("neutral", sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["id_operacion"], ["operacion.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_operacion"),
    )
    op.create_index(
        op.f("ix_registro_emocional_id"),
        "registro_emocional",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    for table_name in (
        "registro_emocional",
        "operacion",
        "estadistica",
        "alerta",
        "ai_settings",
        "cuenta_trading",
        "usuario_trofeo",
        "suscripcion",
        "notificacion",
        "usuarios",
        "trofeos",
    ):
        op.drop_table(table_name)
