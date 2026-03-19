from sqlalchemy import Column, Integer, String, Float
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    contrasena = Column(String(255))
    correo = Column(String(100))
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    telefono = Column(String(20))