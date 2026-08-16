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
    ratio_rr = Column(DECIMAL(10,4), nullable=True)

    nivel_confianza = Column(Integer, nullable=True)  # 1–10

    screenshot = Column(String(255), nullable=True)

    
    cuenta_trading = relationship("Cuenta_Trading", back_populates="operaciones")
    registro_emocional = relationship("Registro_emocional", uselist=False, back_populates="operacion")


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
