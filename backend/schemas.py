from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from datetime import datetime

class SignUp(BaseModel):
    nombre: str
    correo_electronico: EmailStr
    contrasena: str
    tipo_plan: Literal["FREE","PRO"]

class login(BaseModel):
    correo_electronico: EmailStr
    contrasena: str

class OperacionCreate(BaseModel):
    fecha_hora: datetime
    tipo_operacion: Literal["LONG", "SHORT"]
    cantidad: float
    activo: str
    precio_entrada: float
    precio_salida: Optional[float] = None
    notas: Optional[str] = None

class OperacionUpdate(BaseModel):
    fecha_hora: Optional[datetime] = None
    tipo_operacion: Optional[Literal["LONG", "SHORT"]] = None
    cantidad: Optional[float] = None
    activo: str
    precio_entrada: Optional[float] = None
    precio_salida: Optional[float] = None
    notas: Optional[str] = None

class createCuentaTrading(BaseModel):
    nombre_cuenta: str
    divisa: Literal["EUR","USD"]
    saldo_inicial: Optional[float] = None
    
class updateCuentaTrading(BaseModel):
    nombre_cuenta: Optional[str] = None
    saldo_actual: Optional[float] = None
