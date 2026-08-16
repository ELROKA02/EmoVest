from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

class SignUp(BaseModel):
    nombre: str
    correo_electronico: EmailStr
    contrasena: str

class login(BaseModel):
    correo_electronico: EmailStr
    contrasena: str


class TradingProfileUpdate(BaseModel):
    estrategia: str = Field(default="", max_length=4000)
    plan: str = Field(default="", max_length=4000)

    @field_validator("estrategia", "plan")
    @classmethod
    def normalizar_texto(cls, value: str) -> str:
        return value.strip()

class OperacionCreate(BaseModel):
    fecha_hora: datetime
    tipo_operacion: Literal["LONG", "SHORT"]
    cantidad: float
    activo: str
    precio_entrada: float
    precio_salida: Optional[float] = None
    notas: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    resultado_bruto: Optional[float] = None
    ratio_rr: Optional[float] = None
    nivel_confianza: Optional[int] = None
    screenshot: Optional[str] = None

class OperacionUpdate(BaseModel):
    fecha_hora: Optional[datetime] = None
    tipo_operacion: Optional[Literal["LONG", "SHORT"]] = None
    cantidad: Optional[float] = None
    activo: str
    precio_entrada: Optional[float] = None
    precio_salida: Optional[float] = None
    notas: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    resultado_bruto: Optional[float] = None
    ratio_rr: Optional[float] = None
    nivel_confianza: Optional[int] = None
    screenshot: Optional[str] = None


class CuentaOperacionPathParams(BaseModel):
    cuenta_id_trading: int


class OperacionPathParams(BaseModel):
    cuenta_id_trading: int
    id: int

class createCuentaTrading(BaseModel):
    nombre_cuenta: str
    divisa: Literal["EUR","USD"]
    saldo_inicial: Optional[float] = None
    tipo_comision: Literal["sin_comision", "fija", "porcentaje"] = "sin_comision"
    valor_comision: float = Field(default=0, ge=0)
    
class updateCuentaTrading(BaseModel):
    nombre_cuenta: Optional[str] = None
    saldo_actual: Optional[float] = None
    tipo_comision: Optional[Literal["sin_comision", "fija", "porcentaje"]] = None
    valor_comision: Optional[float] = Field(default=None, ge=0)
