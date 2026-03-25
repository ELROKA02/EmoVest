from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import SignUp, login
from database import get_db
from models import Usuario, Suscripcion
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os

load_dotenv()

#Configuración de JWT
SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"])

#funciones auxiliares
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def obtener_correo_usuario(db: Session, correo: str):
    return db.query(Usuario).filter(
        Usuario.correo_electronico == correo
    ).first()

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

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = payload.get("sub")

        if user is None:
            raise HTTPException(status_code=401, detail="Token inválido")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")




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
    
    #login de usuario
@router.post("/login",summary="Iniciar sesión")
def login(credentials: login, db: Session = Depends(get_db)):
    '''Inicia sesión con correo y contraseña, devuelve un token JWT si las credenciales son correctas.'''
    # Buscar usuario en DB
    user = db.query(Usuario).filter(
        Usuario.correo_electronico == credentials.correo_electronico
    ).first()

    # Usuario no existe
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # Contraseña incorrecta
    if not verify_password(credentials.contrasena, user.contrasena):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    access_token = create_access_token(
        data={"sub": user.correo_electronico, "id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.correo_electronico
    }
'''
@router.post("/logout")
def logout(current_user: str = Depends(get_current_user)):
    # En JWT stateless, el logout se maneja del lado del cliente
    # eliminando el token. Aquí solo confirmamos que el usuario estaba autenticado
    return {"msg": "Sesión cerrada exitosamente"}
'''