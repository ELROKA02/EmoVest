from datetime import datetime
from decimal import Decimal
import logging
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Cuenta_Trading, Operacion, Usuario
from routers.auth import get_current_user
from rq_queue import dispatch_emociones_job, stage_emociones_job
from storage import image_storage
from trading_commissions import calculate_commission, calculate_gross_result, calculate_net_result, to_decimal
from trading_risk import calculate_operation_risk

router = APIRouter(prefix="/cuentas/{cuenta_id_trading}/operaciones", tags=["operaciones"])
logger = logging.getLogger(__name__)


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


def actualizar_riesgo_operacion(op: Operacion, saldo_referencia: Decimal) -> None:
    riesgo_importe, riesgo_porcentaje = calculate_operation_risk(
        balance=saldo_referencia,
        quantity=op.cantidad,
        entry_price=op.precio_entrada,
        stop_loss=op.stop_loss,
        side=op.tipo_operacion,
    )
    op.saldo_referencia_riesgo = saldo_referencia if riesgo_importe is not None else None
    op.riesgo_importe = riesgo_importe
    op.riesgo_porcentaje = riesgo_porcentaje


def actualizar_resultados_operacion(
    operacion: Operacion,
    cuenta: Cuenta_Trading,
    resultado_bruto_manual: Decimal | None = None,
) -> None:
    """Persist the current account's commission and the operation's net result."""
    operacion.comisiones = calculate_commission(
        cuenta.tipo_comision,
        cuenta.valor_comision,
        operacion.cantidad,
        operacion.precio_entrada,
    )
    resultado_calculado = calculate_gross_result(
        operacion.tipo_operacion,
        operacion.cantidad,
        operacion.precio_entrada,
        operacion.precio_salida,
    )
    operacion.resultado_bruto = (
        resultado_calculado
        if resultado_calculado is not None
        else resultado_bruto_manual
    )
    operacion.resultado = calculate_net_result(
        operacion.resultado_bruto,
        operacion.comisiones,
    )


def autenticar_usuario_desde_request(request: Request, db: Session) -> Usuario:
    jwt_token = None
    authorization_header = request.headers.get("Authorization")
    if authorization_header and authorization_header.lower().startswith("bearer "):
        jwt_token = authorization_header.split(" ", 1)[1].strip()

    if jwt_token is None:
        raise HTTPException(status_code=401, detail="Token inválido")

    return get_current_user(token=jwt_token, db=db)


def build_screenshot_url(cuenta_id: int, operacion_id: int, screenshot_path: str | None) -> str | None:
    if not screenshot_path:
        return None
    return f"/cuentas/{cuenta_id}/operaciones/{operacion_id}/screenshot"


def serialize_operacion(cuenta_id: int, operacion: Operacion) -> dict:
    data = jsonable_encoder(operacion)
    screenshot_path = operacion.screenshot if isinstance(operacion.screenshot, str) else None
    data["screenshot"] = build_screenshot_url(cuenta_id, operacion.id, screenshot_path)
    return data


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

    return [serialize_operacion(cuenta.id, operacion) for operacion in operaciones]



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
    fecha_hora: Annotated[datetime, Form(...)],
    tipo_operacion: Annotated[Literal["LONG", "SHORT"], Form(...)],
    cantidad: Annotated[float, Form(...)],
    activo: Annotated[str, Form(...)],
    precio_entrada: Annotated[float, Form(...)],
    precio_salida: Annotated[Optional[float], Form()] = None,
    notas: Annotated[Optional[str], Form()] = None,
    stop_loss: Annotated[Optional[float], Form()] = None,
    take_profit: Annotated[Optional[float], Form()] = None,
    resultado_bruto: Annotated[Optional[float], Form()] = None,
    # Kept temporarily for integrations that still submit the old gross result field.
    resultado: Annotated[Optional[float], Form()] = None,
    ratio_rr: Annotated[Optional[float], Form()] = None,
    nivel_confianza: Annotated[Optional[int], Form()] = None,
    screenshot: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

    screenshot_path = image_storage.save_operation_image(screenshot) if screenshot else None

    nueva_operacion = Operacion(
        id_cuenta=cuenta.id,
        fecha_hora=fecha_hora,
        tipo_operacion=tipo_operacion,
        cantidad=cantidad,
        activo=activo,
        precio_entrada=precio_entrada,
        precio_salida=precio_salida,
        notas=notas,
        stop_loss=stop_loss,
        take_profit=take_profit,
        ratio_rr=ratio_rr,
        nivel_confianza=nivel_confianza,
        screenshot=screenshot_path,
    )
    actualizar_riesgo_operacion(
        nueva_operacion,
        Decimal(str(cuenta.saldo_actual or Decimal("0"))),
    )
    resultado_manual = (
        to_decimal(resultado_bruto)
        if resultado_bruto is not None
        else (to_decimal(resultado) if resultado is not None else None)
    )
    actualizar_resultados_operacion(nueva_operacion, cuenta, resultado_manual)

    db.add(nueva_operacion)
    queued_job = None
    try:
        db.flush()

        if nueva_operacion.resultado is not None:
            actualizar_saldo_cuenta(db, cuenta.id, to_decimal(nueva_operacion.resultado))

        if notas:
            try:
                queued_job = stage_emociones_job(
                    db, nueva_operacion.id, notas
                )
            except Exception:
                # El análisis es opcional. No incluir detalles de infraestructura
                # ni notas privadas en los logs.
                logger.warning(
                    "No se pudo preparar el análisis emocional; "
                    "la operación se guardará igualmente."
                )

        # En escritorio la operación y el trabajo SQLite quedan durables juntos.
        db.commit()
        db.refresh(nueva_operacion)
    except SQLAlchemyError:
        db.rollback()
        if screenshot_path:
            image_storage.delete_image(screenshot_path)
        raise

    if queued_job is not None:
        try:
            dispatch_emociones_job(queued_job)
        except Exception:
            # En SQLite el job ya es persistente y el polling lo recuperará. En
            # servidor se mantiene el contrato histórico: la operación no falla.
            logger.warning(
                "No se pudo notificar la cola emocional; "
                "la operación ya fue guardada."
            )

    return {
        "message": "Operacion creada exitosamente",
        "operacion_id": nueva_operacion.id,
        "cuenta_id": cuenta.id,
        "screenshot_url": build_screenshot_url(cuenta.id, nueva_operacion.id, screenshot_path),
    }



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
async def update_operacion(
    request: Request,
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading propietaria de la operacion.", examples=[1])],
    id: Annotated[int, Path(description="Identificador de la operacion a actualizar.", examples=[10])],
    fecha_hora: Annotated[Optional[datetime], Form()] = None,
    tipo_operacion: Annotated[Optional[Literal["LONG", "SHORT"]], Form()] = None,
    cantidad: Annotated[Optional[float], Form()] = None,
    activo: Annotated[Optional[str], Form()] = None,
    precio_entrada: Annotated[Optional[float], Form()] = None,
    precio_salida: Annotated[Optional[float], Form()] = None,
    notas: Annotated[Optional[str], Form()] = None,
    stop_loss: Annotated[Optional[float], Form()] = None,
    take_profit: Annotated[Optional[float], Form()] = None,
    resultado_bruto: Annotated[Optional[float], Form()] = None,
    # Kept temporarily for integrations that still submit the old gross result field.
    resultado: Annotated[Optional[float], Form()] = None,
    ratio_rr: Annotated[Optional[float], Form()] = None,
    nivel_confianza: Annotated[Optional[int], Form()] = None,
    remove_screenshot: Annotated[bool, Form()] = False,
    screenshot: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)
    # Se consulta el payload bruto para distinguir campos omitidos de campos enviados explícitamente.
    form_payload = await request.form()

    op = db.query(Operacion).filter(Operacion.id == id, Operacion.id_cuenta == cuenta.id).first()

    if not op:
        raise HTTPException(status_code=404, detail="Operacion no encontrada")

    datos = {
        "fecha_hora": fecha_hora,
        "tipo_operacion": tipo_operacion,
        "cantidad": cantidad,
        "activo": activo,
        "precio_entrada": precio_entrada,
        "precio_salida": precio_salida,
        "notas": notas,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "ratio_rr": ratio_rr,
        "nivel_confianza": nivel_confianza,
    }
    datos_filtrados = {key: value for key, value in datos.items() if key in form_payload}
    resultado_bruto_enviado = None
    if "resultado_bruto" in form_payload:
        resultado_bruto_enviado = to_decimal(resultado_bruto) if resultado_bruto is not None else None
    elif "resultado" in form_payload:
        resultado_bruto_enviado = to_decimal(resultado) if resultado is not None else None

    for key, value in datos_filtrados.items():
        setattr(op, key, value)

    campos_financieros = {
        "tipo_operacion",
        "cantidad",
        "precio_entrada",
        "precio_salida",
        "resultado_bruto",
        "resultado",
    }
    if campos_financieros & set(form_payload.keys()):
        resultado_anterior = to_decimal(op.resultado) if op.resultado is not None else Decimal("0")
        actualizar_resultados_operacion(op, cuenta, resultado_bruto_enviado)
        resultado_nuevo = to_decimal(op.resultado) if op.resultado is not None else Decimal("0")
        actualizar_saldo_cuenta(db, cuenta.id, resultado_nuevo - resultado_anterior)

    saldo_referencia = Decimal(str(
        op.saldo_referencia_riesgo
        if op.saldo_referencia_riesgo is not None
        else cuenta.saldo_actual or Decimal("0")
    ))
    actualizar_riesgo_operacion(op, saldo_referencia)

    screenshot_path_anterior = op.screenshot if isinstance(op.screenshot, str) else None
    nueva_ruta_screenshot: str | None = None
    if screenshot:
        nueva_ruta = image_storage.save_operation_image(screenshot)
        nueva_ruta_screenshot = nueva_ruta
        op.screenshot = nueva_ruta
    elif remove_screenshot:
        op.screenshot = None

    try:
        db.commit()
        db.refresh(op)
    except SQLAlchemyError:
        db.rollback()
        if nueva_ruta_screenshot:
            image_storage.delete_image(nueva_ruta_screenshot)
        raise

    if screenshot_path_anterior and (remove_screenshot or nueva_ruta_screenshot):
        image_storage.delete_image(screenshot_path_anterior)

    return {
        "message": "Operacion actualizada exitosamente",
        "operacion_id": op.id,
        "cuenta_id": cuenta.id,
        "screenshot_url": build_screenshot_url(cuenta.id, op.id, op.screenshot if isinstance(op.screenshot, str) else None),
    }




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

    screenshot_a_eliminar = op.screenshot if isinstance(op.screenshot, str) else None

    db.delete(op)
    db.commit()

    if screenshot_a_eliminar:
        image_storage.delete_image(screenshot_a_eliminar)
    return {"message": "Operacion eliminada exitosamente", "operacion_id": id, "cuenta_id": cuenta.id}


@router.get(
    "/{id}/screenshot",
    summary="Obtener screenshot de una operación",
    description="Devuelve la imagen adjunta de una operación si el usuario autenticado es dueño de la cuenta.",
    responses={
        200: {"description": "Imagen recuperada correctamente."},
        401: {"description": "Token inválido o ausente."},
        404: {"description": "No se encontró la operación o no tiene imagen."},
    },
)
def get_operacion_screenshot(
    request: Request,
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading.", examples=[1])],
    id: Annotated[int, Path(description="Identificador de la operación.", examples=[10])],
    db: Session = Depends(get_db),
):
    current_user = autenticar_usuario_desde_request(request, db)
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

    op = db.query(Operacion).filter(Operacion.id == id, Operacion.id_cuenta == cuenta.id).first()
    if not op or not isinstance(op.screenshot, str):
        raise HTTPException(status_code=404, detail="La operación no tiene imagen asociada")

    screenshot_path = image_storage.resolve_image_path(op.screenshot)
    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="La imagen no existe en el servidor")

    return FileResponse(path=screenshot_path)
