from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    DECIMAL,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    contrasena = Column(String(255), nullable=False)
    correo_electronico = Column(String(100),index=True, unique=True, nullable=False)
    fecha_registro = Column(DateTime(), server_default=func.now())
    telefono = Column(String(20))
    estrategia_trading = Column(Text, nullable=True)
    plan_trading = Column(Text, nullable=True)

    # relacion con tabla
    notificaciones = relationship("Notificacion", back_populates="usuario")
    usuario_trofeos = relationship("Usuarios_Trofeo", back_populates="usuario")
    suscripcion = relationship("Suscripcion", uselist=False, back_populates="usuario") #uselist=false indica que es 1:1
    cuentas_trading = relationship("Cuenta_Trading", back_populates="usuario")


class Suscripcion(Base):
    __tablename__ = "suscripcion"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"),unique=True, nullable=False)
    tipo_plan = Column(
        Enum(
            "FREE",
            "PRO",
            "PARTNER",
            name="subscription_plan",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    fecha_inicio = Column(DateTime, server_default=func.now(), nullable=False)
    fecha_expiracion = Column(DateTime, nullable=False)
    activa = Column(Boolean, nullable=False)
    precio = Column(DECIMAL(10,2), nullable=False)

    usuario = relationship("Usuario", back_populates="suscripcion")


class Trofeos(Base):
    __tablename__ = "trofeos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50))
    descripcion = Column(String(255))

    usuario_trofeos = relationship("Usuarios_Trofeo", back_populates="trofeo")


class Usuarios_Trofeo(Base):
    __tablename__ = "usuario_trofeo"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    id_trofeo = Column(Integer, ForeignKey("trofeos.id"), nullable=False)
    
    # relaciones
    usuario = relationship("Usuario", back_populates="usuario_trofeos")
    trofeo = relationship("Trofeos", back_populates="usuario_trofeos")


class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha_hora = Column(DateTime)
    mensaje = Column(String(255))
    leida = Column(Boolean, nullable=False, default=False)

    usuario = relationship("Usuario", back_populates="notificaciones")


class Cuenta_Trading(Base):
    __tablename__ = "cuenta_trading"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nombre_cuenta = Column(String(50), nullable=False)
    fecha_creacion = Column(DateTime, server_default=func.now())
    saldo_inicial = Column(DECIMAL(20,6))
    saldo_actual = Column(DECIMAL(20,6))
    divisa = Column(
        Enum(
            "EUR",
            "USD",
            name="trading_currency",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    tipo_comision = Column(String(20), nullable=False, default="sin_comision", server_default="sin_comision")
    valor_comision = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    
    # relaciones
    usuario = relationship("Usuario", back_populates="cuentas_trading")
    alertas = relationship("Alerta", back_populates="cuenta_trading")
    operaciones = relationship("Operacion", back_populates="cuenta_trading")
    estadisticas = relationship("Estadistica", back_populates="cuenta_trading")
    movimientos = relationship("MovimientoCuenta", back_populates="cuenta_trading", cascade="all, delete-orphan")
    importaciones = relationship("Importacion", back_populates="cuenta_trading", cascade="all, delete-orphan")


class Alerta(Base):
    __tablename__ = "alerta"

    id = Column(Integer, primary_key=True, index=True)
    id_cuenta = Column(Integer, ForeignKey("cuenta_trading.id"))
    nombre = Column(String(50), nullable=False)
    umbral = Column(DECIMAL(20,6))
    fecha_creacion = Column(DateTime)

    cuenta_trading = relationship("Cuenta_Trading", back_populates="alertas")


class Estadistica(Base):
    __tablename__ = "estadistica"

    id = Column(Integer, primary_key=True, index=True)
    id_cuenta = Column(Integer, ForeignKey("cuenta_trading.id"))
    fecha_creacion = Column(DateTime, server_default=func.now())
    total_operaciones = Column(Integer, nullable=False)
    operaciones_ganadoras = Column(Integer, nullable=False)
    operaciones_perdedoras = Column(Integer, nullable=False)
    profit_total = Column(DECIMAL(20,6))    #Dinero ganado o perdido
    profit_promedio = Column(DECIMAL(20,6)) # Dinero promedio ganado o perdido

    max_drawdown = Column(DECIMAL(20,6))
    rr_promedio = Column(DECIMAL(10,4))

    cuenta_trading = relationship("Cuenta_Trading", back_populates="estadisticas")
    

class Operacion(Base):
    __tablename__ = "operacion"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('OPEN', 'PARTIALLY_CLOSED', 'CLOSED')",
            name="ck_operacion_estado",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_cuenta = Column(Integer, ForeignKey("cuenta_trading.id"))
    fecha_hora = Column(DateTime)
    tipo_operacion = Column(
        Enum(
            "LONG",
            "SHORT",
            name="operation_side",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    cantidad = Column(DECIMAL(20,6), nullable=False)
    activo = Column(String(10), nullable=False)
    precio_entrada = Column(DECIMAL(20,6), nullable=False)
    precio_salida = Column(DECIMAL(20,6))
    notas = Column(String(255))

    # NUEVO
    stop_loss = Column(DECIMAL(20,6), nullable=True)
    take_profit = Column(DECIMAL(20,6), nullable=True)
    saldo_referencia_riesgo = Column(DECIMAL(20,6), nullable=True)
    riesgo_importe = Column(DECIMAL(20,6), nullable=True)
    riesgo_porcentaje = Column(DECIMAL(10,4), nullable=True)

    resultado_bruto = Column(DECIMAL(20,6), nullable=True)
    comisiones = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    resultado = Column(DECIMAL(20,6), nullable=True)
    swap = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    tasas = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    ratio_rr = Column(DECIMAL(10,4), nullable=True)
    estado = Column(String(24), nullable=False, default="OPEN", server_default="OPEN")
    cantidad_abierta = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    fecha_cierre = Column(DateTime, nullable=True)

    nivel_confianza = Column(Integer, nullable=True)  # 1–10

    screenshot = Column(String(255), nullable=True)

    
    cuenta_trading = relationship("Cuenta_Trading", back_populates="operaciones")
    registro_emocional = relationship("Registro_emocional", uselist=False, back_populates="operacion")
    ejecuciones = relationship(
        "OperacionEjecucion",
        back_populates="operacion",
        cascade="all, delete-orphan",
        order_by="OperacionEjecucion.fecha_hora, OperacionEjecucion.id",
    )


class OperacionEjecucion(Base):
    __tablename__ = "operacion_ejecucion"
    __table_args__ = (
        CheckConstraint("rol IN ('ENTRY', 'EXIT')", name="ck_operacion_ejecucion_rol"),
        CheckConstraint("origen IN ('CALCULATED', 'MANUAL', 'BROKER', 'LEGACY')", name="ck_operacion_ejecucion_origen"),
        CheckConstraint("cantidad > 0", name="ck_operacion_ejecucion_cantidad"),
        Index("ix_operacion_ejecucion_operacion_fecha", "id_operacion", "fecha_hora", "id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_operacion = Column(Integer, ForeignKey("operacion.id", ondelete="CASCADE"), nullable=False)
    source_row_id = Column(Integer, ForeignKey("importacion_fila.id", ondelete="SET NULL"), nullable=True)
    source_leg = Column(String(16), nullable=True)
    rol = Column(String(8), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    cantidad = Column(DECIMAL(20,6), nullable=False)
    precio = Column(DECIMAL(20,6), nullable=True)
    resultado_bruto = Column(DECIMAL(20,6), nullable=True)
    impacto_comision = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    impacto_swap = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    impacto_tasa = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    resultado_neto = Column(DECIMAL(20,6), nullable=False, default=0, server_default="0")
    origen = Column(String(16), nullable=False, default="CALCULATED", server_default="CALCULATED")

    operacion = relationship("Operacion", back_populates="ejecuciones")
    source_row = relationship("ImportacionFila", back_populates="ejecuciones")


class MovimientoCuenta(Base):
    __tablename__ = "movimiento_cuenta"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('DEPOSIT', 'WITHDRAWAL', 'COMMISSION', 'FEE', 'ADJUSTMENT')",
            name="ck_movimiento_cuenta_tipo",
        ),
        Index("ix_movimiento_cuenta_cuenta_fecha", "id_cuenta", "fecha_hora", "id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_cuenta = Column(Integer, ForeignKey("cuenta_trading.id", ondelete="CASCADE"), nullable=False)
    source_row_id = Column(Integer, ForeignKey("importacion_fila.id", ondelete="SET NULL"), nullable=True)
    fecha_hora = Column(DateTime, nullable=False)
    tipo = Column(String(20), nullable=False)
    importe = Column(DECIMAL(20,6), nullable=False)
    descripcion = Column(String(255), nullable=True)

    cuenta_trading = relationship("Cuenta_Trading", back_populates="movimientos")
    source_row = relationship("ImportacionFila", back_populates="movimientos")


class Importacion(Base):
    __tablename__ = "importacion"
    __table_args__ = (
        UniqueConstraint("id_cuenta", "proveedor", "fingerprint", name="uq_importacion_archivo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_cuenta = Column(Integer, ForeignKey("cuenta_trading.id", ondelete="CASCADE"), nullable=False)
    proveedor = Column(String(32), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    cuenta_origen_hash = Column(String(64), nullable=False)
    broker = Column(String(120), nullable=True)
    zona_horaria = Column(String(80), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    cuenta_trading = relationship("Cuenta_Trading", back_populates="importaciones")
    filas = relationship("ImportacionFila", back_populates="importacion", cascade="all, delete-orphan")


class ImportacionFila(Base):
    __tablename__ = "importacion_fila"
    __table_args__ = (
        UniqueConstraint("id_cuenta", "source_key", name="uq_importacion_fila_source"),
        UniqueConstraint("id_importacion", "numero_fila", name="uq_importacion_fila_numero"),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_importacion = Column(Integer, ForeignKey("importacion.id", ondelete="CASCADE"), nullable=False)
    id_cuenta = Column(Integer, ForeignKey("cuenta_trading.id", ondelete="CASCADE"), nullable=False)
    numero_fila = Column(Integer, nullable=False)
    deal_ticket = Column(String(80), nullable=True)
    source_key = Column(String(128), nullable=False)
    clasificacion = Column(String(32), nullable=False)
    normalized_json = Column(Text, nullable=False)

    importacion = relationship("Importacion", back_populates="filas")
    ejecuciones = relationship("OperacionEjecucion", back_populates="source_row")
    movimientos = relationship("MovimientoCuenta", back_populates="source_row")


class Registro_emocional(Base):
    __tablename__ = "registro_emocional"

    id = Column(Integer, primary_key=True, index=True)
    id_operacion = Column(Integer, ForeignKey("operacion.id"), unique=True)    
    fecha_hora = Column(DateTime)
    texto_entrada = Column(String(255))
    confianza = Column(DECIMAL(3,2))
    duda = Column(DECIMAL(3,2))
    euforia = Column(DECIMAL(3,2))
    miedo = Column(DECIMAL(3,2))
    neutral = Column(DECIMAL(3,2))

    operacion = relationship("Operacion", back_populates="registro_emocional")


class AiSetting(Base):
    __tablename__ = "ai_settings"
    __table_args__ = (
        UniqueConstraint("use_case", "provider", name="uq_ai_settings_use_case_provider"),
    )

    id = Column(Integer, primary_key=True, index=True)
    use_case = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(120), nullable=False)
    base_url = Column(String(255), nullable=False)
    install_mode = Column(String(50), nullable=False, default="manual")
    is_active = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_background_jobs_status",
        ),
        Index(
            "ix_background_jobs_due",
            "status",
            "available_at",
            "created_at",
        ),
        Index(
            "ix_background_jobs_lease",
            "status",
            "lease_expires_at",
        ),
    )

    id = Column(String(36), primary_key=True)
    kind = Column(String(50), nullable=False)
    operation_id = Column(
        Integer,
        ForeignKey("operacion.id", ondelete="CASCADE"),
        nullable=True,
    )
    idempotency_key = Column(String(160), nullable=False, unique=True)
    payload_json = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending", server_default="pending")
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    max_attempts = Column(Integer, nullable=False, default=4, server_default="4")
    available_at = Column(DateTime, nullable=False)
    lease_token = Column(String(36), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    last_error_code = Column(String(80), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class ChatSessionRecord(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_user_expires", "user_id", "expires_at"),
        Index("ix_chat_sessions_expires_at", "expires_at"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id = Column(
        Integer,
        ForeignKey("cuenta_trading.id", ondelete="SET NULL"),
        nullable=True,
    )
    history_json = Column(Text, nullable=False, default="[]", server_default="[]")
    tool_summaries_json = Column(Text, nullable=False, default="[]", server_default="[]")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    version = Column(Integer, nullable=False, default=1, server_default="1")
