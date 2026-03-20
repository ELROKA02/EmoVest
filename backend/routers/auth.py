from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import SignUp
from database import SessionLocal
from models import Usuario
from passlib.context import CryptContext

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
    db.commit()
    db.refresh(usuario)

    return usuario

def obtener_correo_usuario(db: Session, email:str):
    return db.query(Usuario).filter(Usuario.correo_electronico == email).first()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/signup",
             summary="Registrar a un usuario",
             description="Registra a un nuevo usuario en el sistema con email unico"
            )
def signup(usuario: SignUp, db: Session = Depends(get_db)):
    usuario_existente = obtener_correo_usuario(db, usuario.correo_electronico)

    if usuario_existente:
        raise HTTPException(
            status_code=400,
            detail="El correo ya está registrado"
        )

    return crear_usuario(
        db,
        usuario.nombre,
        usuario.correo_electronico,
        usuario.contrasena
    )
