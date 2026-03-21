from pydantic import BaseModel, EmailStr
from typing import Literal

class SignUp(BaseModel):
    nombre: str
    correo_electronico: EmailStr
    contrasena: str
    tipo_plan: Literal["FREE","PRO"]

class login(BaseModel):
    correo_electronico: EmailStr
    contrasena: str

