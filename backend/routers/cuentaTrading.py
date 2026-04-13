from schemas import createCuentaTrading, updateCuentaTrading
from database import get_db
from fastapi import Depends, HTTPException, Path, Query, status
from fastapi import APIRouter
from sqlalchemy.orm import Session
from routers.auth import get_current_user
from datetime import datetime
from models import Cuenta_Trading
from typing import Annotated


router = APIRouter(prefix="/cuentas", tags=["cuentas"])

@router.post(
    "/crearcuenta",
    summary="Crear una cuenta de trading",
    description=(
        "Crea una nueva cuenta de trading para el usuario autenticado. El saldo actual "
        "se inicializa con el mismo valor que el saldo inicial enviado en la peticion."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Cuenta creada correctamente.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "example": "Cuenta creada exitosamente"
                            },
                            "cuenta_id": {
                                "type": "integer",
                                "example": 3
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Token invalido"
                            }
                        }
                    }
                }
            }
        }
    }
)
def crear_cuenta(cuenta: createCuentaTrading, usuario: str = Depends(get_current_user), db: Session = Depends(get_db)):
    nueva_cuenta = Cuenta_Trading(
        nombre_cuenta=cuenta.nombre_cuenta,
        divisa=cuenta.divisa,
        id_usuario=usuario.id,
        saldo_inicial=cuenta.saldo_inicial,
        saldo_actual=cuenta.saldo_inicial,  
        fecha_creacion=datetime.now()
    )

    db.add(nueva_cuenta)
    db.commit()
    db.refresh(nueva_cuenta)

    return {"message": "Cuenta creada exitosamente", "cuenta_id": nueva_cuenta.id}


@router.get(
    "/vercuentas",
    summary="Listar cuentas de trading del usuario",
    description="Devuelve todas las cuentas de trading asociadas al usuario autenticado.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Listado de cuentas recuperado correctamente.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "example": 1},
                                "id_usuario": {"type": "integer", "example": 5},
                                "nombre_cuenta": {"type": "string", "example": "Cuenta principal"},
                                "fecha_creacion": {"type": "string", "format": "date-time", "example": "2026-04-08T18:30:00"},
                                "saldo_inicial": {"type": "number", "example": 1000.0},
                                "saldo_actual": {"type": "number", "example": 1250.5},
                                "divisa": {"type": "string", "example": "EUR"}
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Token invalido"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "No existen cuentas de trading registradas para el usuario.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "No se encontraron cuentas de trading para este usuario"
                            }
                        }
                    }
                }
            }
        }
    }
)
def ver_cuentas(
    id_usuario: Annotated[int | None, Query(description="Id del usuario cuyas cuentas se desean obtener", examples=[1])] = None,
    usuario: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    usuario_id = id_usuario if id_usuario is not None else usuario.id

    if id_usuario is not None and id_usuario != usuario.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver las cuentas de otro usuario")

    cuentas = db.query(Cuenta_Trading).filter(Cuenta_Trading.id_usuario == usuario_id).all()

    if not cuentas:
        raise HTTPException(status_code=404, detail="No se encontraron cuentas de trading para este usuario")

    return cuentas



@router.delete(
    "/eliminarcuenta/{cuenta_id}",
    summary="Eliminar una cuenta de trading",
    description="Elimina una cuenta de trading concreta siempre que pertenezca al usuario autenticado.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Cuenta eliminada correctamente.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "example": "Cuenta eliminada exitosamente"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Token invalido"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "La cuenta no existe o no pertenece al usuario autenticado.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Cuenta no encontrada"
                            }
                        }
                    }
                }
            }
        }
    }
)
def eliminar_cuenta(
    cuenta_id: Annotated[int, Path(description="Identificador numerico de la cuenta de trading a eliminar.", examples=[1])],
    usuario: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cuenta = db.query(Cuenta_Trading).filter(Cuenta_Trading.id == cuenta_id, Cuenta_Trading.id_usuario == usuario.id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    db.delete(cuenta)
    db.commit()
    return {"message": "Cuenta eliminada exitosamente"}


@router.put(
    "/actualizarcuenta/{cuenta_id}",
    summary="Actualizar una cuenta de trading",
    description=(
        "Actualiza los campos editables de una cuenta de trading existente del usuario autenticado."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Cuenta actualizada correctamente.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "example": "Cuenta actualizada exitosamente"
                            },
                            "cuenta": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer", "example": 1},
                                    "id_usuario": {"type": "integer", "example": 5},
                                    "nombre_cuenta": {"type": "string", "example": "Cuenta swing"},
                                    "fecha_creacion": {"type": "string", "format": "date-time", "example": "2026-04-08T18:30:00"},
                                    "saldo_inicial": {"type": "number", "example": 1000.0},
                                    "saldo_actual": {"type": "number", "example": 980.0},
                                    "divisa": {"type": "string", "example": "USD"}
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Token invalido"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "La cuenta no existe o no pertenece al usuario autenticado.",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Cuenta no encontrada"
                            }
                        }
                    }
                }
            }
        }
    }
)
def actualizar_cuenta(
    cuenta_id: Annotated[
        int,
        Path(
            description="Identificador numerico de la cuenta de trading a actualizar.",
            examples={"example": {"value": 1}}
        )
    ],
    cuenta: updateCuentaTrading,
    usuario: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cuenta_db = db.query(Cuenta_Trading).filter(Cuenta_Trading.id == cuenta_id, Cuenta_Trading.id_usuario == usuario.id).first()
    if not cuenta_db:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if cuenta.nombre_cuenta:
        cuenta_db.nombre_cuenta = cuenta.nombre_cuenta
    if cuenta.saldo_actual:
        cuenta_db.saldo_actual = cuenta.saldo_actual

    db.commit()
    db.refresh(cuenta_db)
    return {"message": "Cuenta actualizada exitosamente", "cuenta": cuenta_db}