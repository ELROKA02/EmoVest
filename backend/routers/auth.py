from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import SignUp
from database import get_db
from models import Usuario, Suscripcion
from passlib.context import CryptContext
from datetime import datetime, timedelta

ALGORITMO = "HS256"

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

def crear_usuario(db: Session, nombre: str, correo_electronico: str, contrasena: str):
    password_hash = hash_password(contrasena)

    usuario = Usuario(
        nombre=nombre,
        correo_electronico=correo_electronico,
        contrasena=password_hash
    )

    db.add(usuario)
    db.flush()

    return usuario

def obtener_correo_usuario(db: Session, email:str):
    return db.query(Usuario).filter(Usuario.correo_electronico == email).first()




@router.post("/signup",
             summary="Registrar a un usuario",
             description="Registra a un nuevo usuario en el sistema con email unico",
             responses={
                400: {
                    "description": "Correo Registrado",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {
                                        "type": "string",
                                        "example": "El correo ya está registrado"
                                    }
                                }
                            }
                        }
                    }
                }
             }
            )
def signup(usuario: SignUp, db: Session = Depends(get_db)):
    usuario_existente = obtener_correo_usuario(db, usuario.correo_electronico)

    if usuario_existente:
        raise HTTPException(
            status_code=400,
            detail="El correo ya está registrado"
        )
    
    try:
        nuevo_usuario = crear_usuario(
            db,
            usuario.nombre,
            usuario.correo_electronico,
            usuario.contrasena
        )

        now = datetime.now()

        if usuario.tipo_plan == "FREE":
            precio = 0
            fecha_expiracion = now + timedelta(days=30)
        elif usuario.tipo_plan == "PRO":
            precio = 14.99
            fecha_expiracion = now + timedelta(days=30)
        
        suscripcion = Suscripcion(
            id_usuario=nuevo_usuario.id,
            tipo_plan=usuario.tipo_plan,
            activa=True,
            precio=precio,
            fecha_expiracion=fecha_expiracion
        )

        db.add(suscripcion)
        db.commit()

        return {"msg": "Usuario creado correctamente"}

    except Exception as e:
        db.rollback()
        raise HTTPException(500, "Error creando usuario")