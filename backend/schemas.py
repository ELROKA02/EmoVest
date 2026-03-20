from pydantic import BaseModel, EmailStr
from typing import Literal

class SignUp(BaseModel):
    nombre: str
    correo_electronico: EmailStr
    contrasena: str
#    tipo_cuenta: Literal["FREE","PRO"]

class login(BaseModel):
    correo_electronico: EmailStr
    contrasena: str

class CrearSuscripcion(BaseModel):
    id_usuario: int
    tipo_plan: Literal["FREE","PRO","PARTNER"]