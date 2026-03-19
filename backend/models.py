from sqlalchemy import Column, Integer, String, Float, DateTime ,ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    contrasena = Column(String(255))
    correo_electronico = Column(String(100),index=True, unique=True)
    fecha_registro = Column(DateTime(), server_default=func.now())
    telefono = Column(String(20))

    # relacion con tabla
    notificacion = relationship("Notificacion", back_populates="usuario")
    usuario_trofeo = relationship("Usuario_Trofeo", back_populates="usuario")
    suscripcion = relationship("Suscripcion", back_populates="usuario")
    cuenta_trading = relationship("Cuenta_Trading", back_populates="usuario")