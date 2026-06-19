from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Suscripcion
from datetime import datetime, timedelta


def crear_suscripcion(db: Session, id_usuario: int):
    existe = db.query(Suscripcion).filter(Suscripcion.id_usuario == id_usuario).first()

    fecha_expiracion = datetime.utcnow() + timedelta(days=3650)

    if existe:
        raise HTTPException(400, "El usuario ya tiene suscripcion")

    suscripcion = Suscripcion(
        id_usuario=id_usuario,
        tipo_plan="FREE",
        activa=True,
        precio=0,
        fecha_expiracion=fecha_expiracion
    )

    db.add(suscripcion)
    db.commit()
    db.refresh(suscripcion)
    return suscripcion
