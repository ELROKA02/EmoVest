from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from models import Suscripcion
from datetime import datetime, timedelta


def crear_suscripcion(db: Session, id_usuario: int, tipo_plan: str):
    existe = db.query(Suscripcion).filter(Suscripcion.id_usuario == id_usuario).first()

    fecha_expiracion = datetime.utcnow() + timedelta(days=30)

    if existe:
        raise HTTPException(400, "El usuario ya tiene suscripcion")

    if tipo_plan == "FREE":
        precio = 0
    elif tipo_plan == "PRO":
        precio = 14.99
    elif tipo_plan == "PARTNER":
        precio = 50                     # "Partner no se que hacer"
    else:
        raise HTTPException(400, "Plan invalido")

    suscripcion = Suscripcion(
        id_usuario=id_usuario,
        tipo_plan=tipo_plan,
        activa=True,
        precio=precio,
        fecha_expiracion=fecha_expiracion
    )