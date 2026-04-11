from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Operacion, Cuenta_Trading
from routers.ia import guardar_registro_emocional
from schemas import (
    CuentaOperacionPathParams,
    OperacionCreate,
    OperacionPathParams,
    OperacionUpdate,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/cuentas/{cuenta_id_trading}/operaciones", tags=["operaciones"])


def get_cuenta_usuario(db: Session, cuenta_id: int, user_id: int) -> Cuenta_Trading:
    cuenta = db.query(Cuenta_Trading).filter(
        Cuenta_Trading.id == cuenta_id,
        Cuenta_Trading.id_usuario == user_id,
    ).first()

    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta de trading no encontrada")

    return cuenta


@router.get(
    "/",
    summary="Obtener operaciones de una cuenta",
    description="Lista todas las operaciones asociadas a una cuenta de trading concreta del usuario autenticado.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Listado de operaciones recuperado correctamente."
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido."
        },
        404: {
            "description": "La cuenta indicada no existe o no pertenece al usuario autenticado."
        }
    }
)
def get_operaciones(
    params: CuentaOperacionPathParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, params.cuenta_id_trading, current_user.id)

    operaciones = db.query(Operacion).filter(Operacion.id_cuenta == cuenta.id).all()

    return operaciones



@router.post(
    "/",
    summary="Crear una operacion en una cuenta",
    description="Registra una nueva operacion vinculada a la cuenta de trading indicada del usuario autenticado.",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Operacion creada correctamente."
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido."
        },
        404: {
            "description": "La cuenta indicada no existe o no pertenece al usuario autenticado."
        }
    }
)
def create_operacion(
    operacion: OperacionCreate,
    params: CuentaOperacionPathParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, params.cuenta_id_trading, current_user.id)

    nueva_operacion = Operacion(id_cuenta=cuenta.id, **operacion.model_dump())

    try:
        db.add(nueva_operacion)
        db.flush()

        if operacion.notas:
            try:
                guardar_registro_emocional(operacion.notas, nueva_operacion.id, db)
            except Exception as error:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fallo en guardar_registro_emocional: {error}",
                ) from error

        try:
            db.commit()
            db.refresh(nueva_operacion)
        except Exception as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fallo en commit o refresh: {error}",
            ) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fallo antes de guardar registro emocional: {error}",
        ) from error

    return {"message": "Operacion creada exitosamente", "operacion_id": nueva_operacion.id, "cuenta_id": cuenta.id}



@router.put(
    "/{id}",
    summary="Actualizar una operacion de una cuenta",
    description="Actualiza una operacion concreta siempre que pertenezca a la cuenta indicada y al usuario autenticado.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Operacion actualizada correctamente."
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido."
        },
        404: {
            "description": "La cuenta u operacion indicada no existe o no pertenece al usuario autenticado."
        }
    }
)
def update_operacion(
    operacion: OperacionUpdate,
    params: OperacionPathParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, params.cuenta_id_trading, current_user.id)

    op = db.query(Operacion).filter(Operacion.id == params.id, Operacion.id_cuenta == cuenta.id).first()

    if not op:
        raise HTTPException(status_code=404, detail="Operacion no encontrada")
    
    for key, value in operacion.model_dump(exclude_unset=True).items():
        setattr(op, key, value)

    db.commit()
    db.refresh(op)

    return {"message": "Operacion actualizada exitosamente", "operacion_id": op.id, "cuenta_id": cuenta.id}




@router.delete(
    "/{id}",
    summary="Eliminar una operacion de una cuenta",
    description="Elimina una operacion concreta siempre que pertenezca a la cuenta indicada y al usuario autenticado.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Operacion eliminada correctamente."
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido."
        },
        404: {
            "description": "La cuenta u operacion indicada no existe o no pertenece al usuario autenticado."
        }
    }
)
def delete_operacion(
    params: OperacionPathParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, params.cuenta_id_trading, current_user.id)

    op = db.query(Operacion).filter(Operacion.id == params.id, Operacion.id_cuenta == cuenta.id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operacion no encontrada")
    db.delete(op)
    db.commit()
    return {"message": "Operacion eliminada exitosamente", "operacion_id": params.id, "cuenta_id": cuenta.id}