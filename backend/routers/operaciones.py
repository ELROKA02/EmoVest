from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from models import Operacion, Cuenta_Trading
from routers.ia import guardar_registro_emocional
from schemas import OperacionCreate, OperacionUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/cuentas/{cuenta_id_trading}/operaciones", tags=["operaciones"])


def get_cuenta_usuario(db: Session, cuenta_id_trading: int, user_id: int) -> Cuenta_Trading:
    cuenta = db.query(Cuenta_Trading).filter(
        Cuenta_Trading.id == cuenta_id_trading,
        Cuenta_Trading.id_usuario == user_id,
    ).first()

    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta de trading no encontrada")

    return cuenta


def actualizar_saldo_cuenta(db: Session, cuenta_id: int, diferencia: Decimal) -> None:
    if diferencia == 0:
        return

    db.query(Cuenta_Trading).filter(Cuenta_Trading.id == cuenta_id).update(
        {
            Cuenta_Trading.saldo_actual: func.coalesce(Cuenta_Trading.saldo_actual, Decimal("0")) + diferencia
        },
        synchronize_session=False,
    )


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
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading.", examples=[1])],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

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
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading donde se registrara la operacion.", examples=[1])],
    operacion: OperacionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

    nueva_operacion = Operacion(
        id_cuenta=cuenta.id,
        fecha_hora=operacion.fecha_hora,
        tipo_operacion=operacion.tipo_operacion,
        cantidad=operacion.cantidad,
        activo=operacion.activo,
        precio_entrada=operacion.precio_entrada,
        precio_salida=operacion.precio_salida,
        notas=operacion.notas,
        stop_loss=operacion.stop_loss,
        take_profit=operacion.take_profit,
        resultado=operacion.resultado,
        ratio_rr=operacion.ratio_rr,
        nivel_confianza=operacion.nivel_confianza,
        screenshot=operacion.screenshot
    )

    db.add(nueva_operacion)
    db.commit()
    db.refresh(nueva_operacion)

    if operacion.resultado is not None:
        actualizar_saldo_cuenta(db, cuenta.id, Decimal(str(operacion.resultado)))
        db.commit()

    if operacion.notas:
        try:
            guardar_registro_emocional(operacion.notas, nueva_operacion.id, db)
            db.commit()
        except Exception as error:
            db.rollback()
            print(f"Advertencia: fallo en guardar registro emocional, la operacion ya fue guardada. Error: {error}")

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
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading propietaria de la operacion.", examples=[1])],
    id: Annotated[int, Path(description="Identificador de la operacion a actualizar.", examples=[10])],
    operacion: OperacionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

    op = db.query(Operacion).filter(Operacion.id == id, Operacion.id_cuenta == cuenta.id).first()

    if not op:
        raise HTTPException(status_code=404, detail="Operacion no encontrada")

    # model_dump con exclude_unset para obtener solo los campos que se estan actualizando, y asi evitar sobreescribir campos no incluidos en la request con valores por defecto o None
    datos = operacion.model_dump(exclude_unset=True)

    if "resultado" in datos:
        resultado_anterior = Decimal(str(op.resultado)) if op.resultado is not None else Decimal("0")
        resultado_nuevo = Decimal(str(datos["resultado"])) if datos["resultado"] is not None else Decimal("0")
        diferencia = resultado_nuevo - resultado_anterior
        actualizar_saldo_cuenta(db, cuenta.id, diferencia)

    for key, value in datos.items():
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
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading propietaria de la operacion.", examples=[1])],
    id: Annotated[int, Path(description="Identificador de la operacion a eliminar.", examples=[10])],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

    op = db.query(Operacion).filter(Operacion.id == id, Operacion.id_cuenta == cuenta.id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operacion no encontrada")

    if op.resultado is not None:
        actualizar_saldo_cuenta(db, cuenta.id, -Decimal(str(op.resultado)))

    db.delete(op)
    db.commit()
    return {"message": "Operacion eliminada exitosamente", "operacion_id": id, "cuenta_id": cuenta.id}