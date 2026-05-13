from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import SignUp, login, PasswordResetRequest, PasswordResetConfirm
from database import get_db
from models import Usuario, Suscripcion
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, ExpiredSignatureError, jwt
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from dotenv import load_dotenv
from email.message import EmailMessage
import smtplib
import ssl
import os

load_dotenv()

from config import (
    EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT,
    EMAIL_USERNAME,
    EMAIL_PASSWORD,
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    FRONTEND_URL,
)

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


def build_password_reset_message(correo: str, token: str) -> EmailMessage:
    reset_url = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    message = EmailMessage()
    message["Subject"] = "Recuperación de contraseña - EmoVest"
    message["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    message["To"] = correo
    message.set_content(
        f"Hola,\n\nHemos recibido una solicitud para restablecer la contraseña de tu cuenta EmoVest.\n\n" \
        f"Haz clic en el siguiente enlace o cópialo en tu navegador:\n\n{reset_url}\n\n" \
        "Este enlace expirará en 30 minutos.\n\n" \
        "Si no solicitaste este cambio, ignora este correo.\n\n" \
        "Saludos,\nEquipo EmoVest"
    )
    message.add_alternative(
        f"""<html>
<body style=\"font-family: Arial, sans-serif; color:#111;\">
  <p>Hola,</p>
  <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta EmoVest.</p>
  <p><a href=\"{reset_url}\" style=\"display:inline-block;padding:12px 16px;color:#fff;background:#2563eb;border-radius:8px;text-decoration:none;\">Restablecer contraseña</a></p>
  <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
  <p><a href=\"{reset_url}\">{reset_url}</a></p>
  <p>Este enlace expirará en 30 minutos.</p>
  <p>Si no solicitaste este cambio, ignora este correo.</p>
  <p>Saludos,<br/>Equipo EmoVest</p>
</body>
</html>""",
        subtype="html",
    )
    return message


def send_email_message(message: EmailMessage):
    if not EMAIL_SMTP_SERVER or not EMAIL_USERNAME or not EMAIL_PASSWORD or not EMAIL_FROM:
        raise ValueError("Falta configuración de correo electrónico en el backend")

    if EMAIL_SMTP_PORT == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, context=context, timeout=10) as server:
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)
    else:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)


def create_password_reset_token(email: str, expires_delta: timedelta = None):
    to_encode = {"sub": email, "type": "password_reset"}
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Token de recuperación inválido")

        correo = payload.get("sub")
        if correo is None:
            raise HTTPException(status_code=400, detail="Token de recuperación inválido")

        return correo

    except ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="El enlace de recuperación ha expirado")
    except JWTError:
        raise HTTPException(status_code=400, detail="Token de recuperación inválido")


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



@router.get(
    "/me",
    summary="Obtener perfil del usuario autenticado",
    description="Devuelve la informacion basica del usuario autenticado a partir del token JWT enviado.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Perfil recuperado correctamente."
        },
        401: {
            "description": "El token no es valido o no corresponde a un usuario existente."
        }
    }
)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.nombre,
        "email": current_user.correo_electronico
    }


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
            fecha_expiracion = now + timedelta(weeks=2)
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


@router.post(
    "/forgot-password",
    summary="Solicitar recuperación de contraseña",
    description="Envía un correo con un enlace para restablecer la contraseña si la dirección está registrada.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Se envió un correo con instrucciones si el correo existe." 
        }
    }
)
def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    usuario = obtener_correo_usuario(db, request.correo_electronico)

    if usuario:
        token = create_password_reset_token(usuario.correo_electronico)
        mensaje = build_password_reset_message(usuario.correo_electronico, token)
        try:
            send_email_message(mensaje)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo enviar el correo de recuperación: {type(exc).__name__} - {str(exc)}"
            )

    return {
        "msg": "Si existe una cuenta asociada a ese correo, recibirás un email con instrucciones para restablecer tu contraseña"
    }


@router.post(
    "/reset-password",
    summary="Restablecer contraseña con token",
    description="Actualiza la contraseña cuando se proporciona un token de recuperación válido.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Contraseña restablecida correctamente." 
        },
        400: {
            "description": "Token inválido o datos incorrectos." 
        }
    }
)
def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    correo = verify_password_reset_token(data.token)
    usuario = obtener_correo_usuario(db, correo)

    if not usuario:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")

    if len(data.contrasena) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    if data.contrasena != data.confirmar_contrasena:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden")

    usuario.contrasena = hash_password(data.contrasena)
    db.commit()

    return {"msg": "Contraseña restablecida correctamente"}


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

    # Validar que la suscripción no haya expirado
    suscripcion = db.query(Suscripcion).filter(
        Suscripcion.id_usuario == user.id
    ).first()

    if not suscripcion:
        raise HTTPException(
            status_code=403,
            detail="No hay suscripción asociada a esta cuenta"
        )

    if suscripcion.fecha_expiracion < datetime.utcnow():
        raise HTTPException(
            status_code=403,
            detail="Tu suscripción ha expirado. Por favor, renueva tu plan."
        )

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