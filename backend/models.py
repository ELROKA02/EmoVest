from sqlalchemy import Column, Integer, String, DECIMAL, DateTime ,ForeignKey, Boolean, Enum
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

    # relacion con tabla
    notificaciones = relationship("Notificacion", back_populates="usuario")
    usuario_trofeos = relationship("Usuarios_Trofeo", back_populates="usuario")
    suscripcion = relationship("Suscripcion", uselist=False, back_populates="usuario") #uselist=false indica que es 1:1
    cuentas_trading = relationship("Cuenta_Trading", back_populates="usuario")


class Suscripcion(Base):
    __tablename__ = "suscripcion"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"),unique=True, nullable=False)
    tipo_plan = Column(Enum("FREE", "PRO", "PARTNER"), nullable=False)
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
    divisa = Column(Enum("EUR","USD"), nullable=False)
    
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

    cuenta_trading = relationship("Cuenta_Trading", back_populates="estadisticas")
    

class Operacion(Base):
    __tablename__ = "operacion"

    id = Column(Integer, primary_key=True, index=True)
    id_cuenta = Column(Integer, ForeignKey("cuenta_trading.id"))
    fecha_hora = Column(DateTime)
    tipo_operacion = Column(Enum("LONG", "SHORT"), nullable=False)
    cantidad = Column(DECIMAL(20,6), nullable=False)
    activo = Column(String(10), nullable=False)
    precio_entrada = Column(DECIMAL(20,6), nullable=False)
    precio_salida = Column(DECIMAL(20,6))
    notas = Column(String(255))
    
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