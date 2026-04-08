from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import SignUp, login
from database import get_db
from models import Usuario, Suscripcion
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from dotenv import load_dotenv
import os

load_dotenv()

#Configuración de JWT
SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

router = APIRouter(tags=["usuarios"])

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

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")

        if user_email is None:
            raise HTTPException(status_code=401, detail="Token inválido")

        user = db.query(Usuario).filter(
            Usuario.correo_electronico == user_email
        ).first()

        if user is None:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")




@router.post(
    "/signup",
    summary="Registrar un usuario",
    description=(
        "Crea un nuevo usuario con un correo electronico unico y genera su "
        "suscripcion inicial en funcion del plan enviado."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Usuario creado correctamente.",
            "content": {
                "application/json": {
                    "example": {
                        "msg": "Usuario creado correctamente"
                    }
                }
            }
        },
        400: {
            "description": "El correo electronico ya esta registrado.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "El correo ya esta registrado"
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Se produjo un error interno durante el registro.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Error creando usuario"
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

    except Exception:
        db.rollback()
        raise HTTPException(500, "Error creando usuario")
    
    #login de usuario
@router.post(
    "/login",
    summary="Iniciar sesion",
    description="Valida las credenciales del usuario y devuelve un token JWT de acceso.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Inicio de sesion completado correctamente.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "access_token": {
                                "type": "string",
                                "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                            },
                            "token_type": {
                                "type": "string",
                                "example": "bearer"
                            },
                            "user": {
                                "type": "string",
                                "format": "email",
                                "example": "usuario@emovest.dev"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Las credenciales no son validas.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Credenciales incorrectas"
                            }
                        }
                    }
                }
            }
        }
    }
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    '''Inicia sesión con correo y contraseña, devuelve un token JWT si las credenciales son correctas.'''
    # Buscar usuario en DB
    user = db.query(Usuario).filter(
        Usuario.correo_electronico == form_data.username
    ).first()

    # Usuario no existe
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # Contraseña incorrecta
    if not verify_password(form_data.password, user.contrasena):
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