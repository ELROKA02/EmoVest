import csv
from datetime import datetime
from decimal import Decimal
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Cuenta_Trading, Operacion, Usuario
from routers.auth import get_current_user
from rq_queue import enqueue_emociones_job

router = APIRouter(tags=["operaciones"])

CSV_HEADERS = [
    "cuenta_id",
    "cuenta_nombre",
    "operacion_id",
    "fecha_hora",
    "tipo_operacion",
    "activo",
    "cantidad",
    "precio_entrada",
    "precio_salida",
    "resultado",
    "stop_loss",
    "take_profit",
    "ratio_rr",
    "nivel_confianza",
    "notas",
    "screenshot",
]

IMPORT_REQUIRED_HEADERS = {
    "fecha_hora",
    "tipo_operacion",
    "activo",
    "cantidad",
    "precio_entrada",
}
IMPORT_DECIMAL_FIELDS = {
    "cantidad",
    "precio_entrada",
    "precio_salida",
    "resultado",
    "stop_loss",
    "take_profit",
    "ratio_rr",
}

def serialize_csv_value(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def build_screenshot_url(cuenta_id: int, operacion_id: int, screenshot_path: str | None) -> str:
    if not screenshot_path:
        return ""
    return f"/cuentas/{cuenta_id}/operaciones/{operacion_id}/screenshot"


def clean_csv_cell(row: dict, field: str) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_decimal_field(row: dict, field: str, row_number: int, errors: list[dict], required: bool = False):
    value = clean_csv_cell(row, field)
    if value is None:
        if required:
            errors.append({"row": row_number, "field": field, "error": "Campo requerido"})
        return None

    try:
        return Decimal(value)
    except Exception:
        errors.append({"row": row_number, "field": field, "error": "Decimal invalido"})
        return None


def parse_datetime_field(row: dict, field: str, row_number: int, errors: list[dict]):
    value = clean_csv_cell(row, field)
    if value is None:
        errors.append({"row": row_number, "field": field, "error": "Campo requerido"})
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        errors.append({"row": row_number, "field": field, "error": "Fecha ISO 8601 invalida"})
        return None


def parse_int_field(row: dict, field: str, row_number: int, errors: list[dict]):
    value = clean_csv_cell(row, field)
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        errors.append({"row": row_number, "field": field, "error": "Entero invalido"})
        return None


def parse_csv_operaciones(csv_text: str, cuenta_id: int) -> list[Operacion]:
    reader = csv.DictReader(StringIO(csv_text))
    headers = set(reader.fieldnames or [])
    missing_headers = sorted(IMPORT_REQUIRED_HEADERS - headers)

    if missing_headers:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "CSV invalido",
                "errors": [
                    {
                        "row": None,
                        "field": header,
                        "error": "Cabecera requerida ausente",
                    }
                    for header in missing_headers
                ],
            },
        )

    errors: list[dict] = []
    operaciones: list[Operacion] = []

    for index, row in enumerate(reader, start=2):
        tipo_operacion = clean_csv_cell(row, "tipo_operacion")
        if tipo_operacion is None:
            errors.append({"row": index, "field": "tipo_operacion", "error": "Campo requerido"})
        elif tipo_operacion not in {"LONG", "SHORT"}:
            errors.append({"row": index, "field": "tipo_operacion", "error": "Debe ser LONG o SHORT"})

        activo = clean_csv_cell(row, "activo")
        if activo is None:
            errors.append({"row": index, "field": "activo", "error": "Campo requerido"})

        fecha_hora = parse_datetime_field(row, "fecha_hora", index, errors)
        cantidad = parse_decimal_field(row, "cantidad", index, errors, required=True)
        precio_entrada = parse_decimal_field(row, "precio_entrada", index, errors, required=True)
        optional_values = {
            field: parse_decimal_field(row, field, index, errors)
            for field in IMPORT_DECIMAL_FIELDS - {"cantidad", "precio_entrada"}
        }
        nivel_confianza = parse_int_field(row, "nivel_confianza", index, errors)
        notas = clean_csv_cell(row, "notas")

        operaciones.append(
            Operacion(
                id_cuenta=cuenta_id,
                fecha_hora=fecha_hora,
                tipo_operacion=tipo_operacion,
                activo=activo,
                cantidad=cantidad,
                precio_entrada=precio_entrada,
                precio_salida=optional_values["precio_salida"],
                resultado=optional_values["resultado"],
                stop_loss=optional_values["stop_loss"],
                take_profit=optional_values["take_profit"],
                ratio_rr=optional_values["ratio_rr"],
                nivel_confianza=nivel_confianza,
                notas=notas,
            )
        )

    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "CSV invalido",
                "errors": errors,
            },
        )

    return operaciones


@router.get(
    "/operaciones/export.csv",
    summary="Exportar operaciones en CSV",
    description=(
        "Descarga un CSV con operaciones de una, varias o todas las cuentas de trading "
        "del usuario autenticado, con filtros opcionales por fecha."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "CSV generado correctamente."
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido."
        },
        404: {
            "description": "Alguna cuenta solicitada no existe o no pertenece al usuario autenticado."
        },
    },
)
def export_operaciones_csv(
    cuenta_ids: Annotated[
        list[int] | None,
        Query(
            description="IDs de cuentas de trading a exportar. Puede repetirse para varias cuentas.",
            examples=[1, 2],
        ),
    ] = None,
    fecha_desde: Annotated[
        datetime | None,
        Query(description="Fecha/hora inicial inclusiva aplicada a fecha_hora."),
    ] = None,
    fecha_hasta: Annotated[
        datetime | None,
        Query(description="Fecha/hora final inclusiva aplicada a fecha_hora."),
    ] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    requested_ids = sorted(set(cuenta_ids or []))

    cuentas_query = db.query(Cuenta_Trading).filter(
        Cuenta_Trading.id_usuario == current_user.id
    )
    if requested_ids:
        cuentas_query = cuentas_query.filter(Cuenta_Trading.id.in_(requested_ids))

    cuentas = cuentas_query.all()
    cuentas_by_id = {cuenta.id: cuenta for cuenta in cuentas}

    if requested_ids and set(requested_ids) != set(cuentas_by_id):
        raise HTTPException(status_code=404, detail="Cuenta de trading no encontrada")

    cuenta_ids_propias = list(cuentas_by_id)

    operaciones_query = (
        db.query(Operacion)
        .filter(Operacion.id_cuenta.in_(cuenta_ids_propias))
        .order_by(Operacion.fecha_hora.asc(), Operacion.id.asc())
    )

    if fecha_desde is not None:
        operaciones_query = operaciones_query.filter(Operacion.fecha_hora >= fecha_desde)
    if fecha_hasta is not None:
        operaciones_query = operaciones_query.filter(Operacion.fecha_hora <= fecha_hasta)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)

    for operacion in operaciones_query.all():
        cuenta = cuentas_by_id[operacion.id_cuenta]
        writer.writerow(
            [
                serialize_csv_value(cuenta.id),
                serialize_csv_value(cuenta.nombre_cuenta),
                serialize_csv_value(operacion.id),
                serialize_csv_value(operacion.fecha_hora),
                serialize_csv_value(operacion.tipo_operacion),
                serialize_csv_value(operacion.activo),
                serialize_csv_value(operacion.cantidad),
                serialize_csv_value(operacion.precio_entrada),
                serialize_csv_value(operacion.precio_salida),
                serialize_csv_value(operacion.resultado),
                serialize_csv_value(operacion.stop_loss),
                serialize_csv_value(operacion.take_profit),
                serialize_csv_value(operacion.ratio_rr),
                serialize_csv_value(operacion.nivel_confianza),
                serialize_csv_value(operacion.notas),
                build_screenshot_url(cuenta.id, operacion.id, operacion.screenshot),
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="operaciones.csv"'
        },
    )


@router.post(
    "/operaciones/import.csv",
    summary="Importar operaciones desde CSV",
    description=(
        "Importa operaciones desde un archivo CSV a una cuenta de trading propia. "
        "La cuenta destino validada prevalece sobre cualquier columna de cuenta del CSV."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "CSV importado correctamente."
        },
        401: {
            "description": "El usuario no esta autenticado o el token no es valido."
        },
        404: {
            "description": "La cuenta indicada no existe o no pertenece al usuario autenticado."
        },
        422: {
            "description": "El CSV no tiene el formato esperado o contiene valores invalidos."
        },
    },
)
async def import_operaciones_csv(
    cuenta_id: Annotated[
        int,
        Form(description="Cuenta de trading destino para todas las operaciones importadas."),
    ],
    file: Annotated[
        UploadFile,
        File(description="Archivo CSV compatible con la exportacion de operaciones."),
    ],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cuenta = db.query(Cuenta_Trading).filter(
        Cuenta_Trading.id == cuenta_id,
        Cuenta_Trading.id_usuario == current_user.id,
    ).first()

    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta de trading no encontrada")

    raw_content = await file.read()
    try:
        csv_text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "CSV invalido",
                "errors": [
                    {
                        "row": None,
                        "field": "file",
                        "error": "El archivo debe estar codificado en UTF-8",
                    }
                ],
            },
        )

    operaciones = parse_csv_operaciones(csv_text, cuenta.id)

    db.add_all(operaciones)
    try:
        db.commit()
        for operacion in operaciones:
            db.refresh(operacion)
    except SQLAlchemyError:
        db.rollback()
        raise

    warnings = []
    for operacion in operaciones:
        if not operacion.notas:
            continue
        try:
            enqueue_emociones_job(operacion.id, operacion.notas)
        except Exception as error:
            warnings.append(
                {
                    "operacion_id": operacion.id,
                    "warning": f"No se pudo encolar analisis emocional: {error}",
                }
            )

    return {
        "created_count": len(operaciones),
        "cuenta_id": cuenta.id,
        "warnings": warnings,
    }
