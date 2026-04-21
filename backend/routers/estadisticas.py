from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from routers.auth import get_current_user
from models import Cuenta_Trading, Operacion


router = APIRouter(prefix="/cuentas/{cuenta_id_trading}/estadisticas", tags=["estadisticas"])


def get_cuenta_usuario(db: Session, cuenta_id_trading: int, user_id: int) -> Cuenta_Trading:
	cuenta = db.query(Cuenta_Trading).filter(
		Cuenta_Trading.id == cuenta_id_trading,
		Cuenta_Trading.id_usuario == user_id,
	).first()

	if not cuenta:
		raise HTTPException(status_code=404, detail="Cuenta de trading no encontrada")

	return cuenta


def get_inicio_mes_siguiente(fecha_actual: datetime) -> datetime:
	if fecha_actual.month == 12:
		return datetime(fecha_actual.year + 1, 1, 1)

	return datetime(fecha_actual.year, fecha_actual.month + 1, 1)


def get_operaciones_del_mes(
	db: Session,
	cuenta_id_trading: int,
): 
	now = datetime.now()
	inicio_mes = datetime(now.year, now.month, 1)
	inicio_mes_siguiente = get_inicio_mes_siguiente(now)

	operaciones = db.query(Operacion).filter(
		Operacion.id_cuenta == cuenta_id_trading,
		Operacion.fecha_hora >= inicio_mes,
		Operacion.fecha_hora < inicio_mes_siguiente,
    ).order_by(Operacion.fecha_hora.asc(), Operacion.id.asc()).all()

	return operaciones


def calcular_ganancias_netas_mensuales(
	db: Session,
	cuenta_id_trading: int,
	) -> float:
	operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

	ganancia_neta_decimal = Decimal("0")

	for operacion in operaciones:
		if operacion.resultado is not None:
			ganancia_neta_decimal += Decimal(str(operacion.resultado))

	return float(ganancia_neta_decimal)

def calcular_winrate_mensual(
    db: Session,
    cuenta_id_trading: int,
    ) -> float:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    if not operaciones:
        return 0.0

    operaciones_ganadoras = 0
    operaciones_totales = 0

    for operacion in operaciones:
        if operacion.resultado is not None:
            operaciones_totales += 1
            if operacion.resultado > 0:
                operaciones_ganadoras += 1

    if operaciones_totales == 0:
        return 0.0

    win_rate = (operaciones_ganadoras / operaciones_totales) * 100

    return win_rate

def calcular_ganancias_promedias_mensuales(
    db: Session,
    cuenta_id_trading: int,
    ) -> float:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    ganancias_totales_decimal = Decimal("0")
    operaciones_ganadoras = 0

    for operacion in operaciones:
        if operacion.resultado is not None and operacion.resultado > 0:
            ganancias_totales_decimal += Decimal(str(operacion.resultado))
            operaciones_ganadoras += 1

    if operaciones_ganadoras == 0:
        return 0.0

    ganancia_promedio_decimal = ganancias_totales_decimal / Decimal(operaciones_ganadoras)

    return float(ganancia_promedio_decimal)

def calcular_perdidas_promedias_mensuales(
    db: Session,
    cuenta_id_trading: int,
    ) -> float:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    perdidas_totales_decimal = Decimal("0")
    operaciones_perdedoras = 0

    for operacion in operaciones:
        if operacion.resultado is not None and operacion.resultado < 0:
            perdidas_totales_decimal += Decimal(str(operacion.resultado))
            operaciones_perdedoras += 1

    if operaciones_perdedoras == 0:
        return 0.0

    perdida_promedio_decimal = perdidas_totales_decimal / Decimal(operaciones_perdedoras)

    return float(perdida_promedio_decimal)

def calcular_maximo_drawdown_mensual(
    db: Session,
    cuenta_id_trading: int
) -> dict:

    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    saldo = Decimal("0")
    pico = Decimal("0")
    max_drawdown_euros = Decimal("0")
    max_drawdown_porcentaje = Decimal("0")

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        # Balance acumulado
        saldo += Decimal(str(operacion.resultado))

        # Nuevo pico histórico
        if saldo > pico:
            pico = saldo

        # Drawdown en euros
        drawdown_actual = pico - saldo

        if drawdown_actual > max_drawdown_euros:
            max_drawdown_euros = drawdown_actual

        # Drawdown en porcentaje
        if pico > 0:
            porcentaje_actual = (drawdown_actual / pico) * Decimal("100")

            if porcentaje_actual > max_drawdown_porcentaje:
                max_drawdown_porcentaje = porcentaje_actual

    return {
        "drawdown_euros": round(float(max_drawdown_euros), 2),
        "drawdown_porcentaje": round(float(max_drawdown_porcentaje), 2)
    }

def calcular_media_operaciones_hasta_error_mensual(
    db: Session,
    cuenta_id_trading: int
) -> float:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    rachas_ganadoras = []
    racha_actual = 0

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        if operacion.resultado < 0:
            if racha_actual > 0:
                rachas_ganadoras.append(racha_actual)
                racha_actual = 0

        elif operacion.resultado > 0:
            racha_actual += 1
    # FIX: guardar última racha si el mes acaba en ganancias
    if racha_actual > 0:
        rachas_ganadoras.append(racha_actual)
        
    if not rachas_ganadoras:
        return 0.0

    suma_rachas = 0

    for racha in rachas_ganadoras:
        suma_rachas += racha

    media_decimal = Decimal(str(suma_rachas)) / Decimal(str(len(rachas_ganadoras)))

    return float(media_decimal)

def calcular_media_operaciones_hasta_ganadora_mensual(
    db: Session,
    cuenta_id_trading: int
) -> float:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    rachas_perdedoras = []
    racha_actual = 0

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        if operacion.resultado > 0:
            if racha_actual > 0:
                rachas_perdedoras.append(racha_actual)
                racha_actual = 0

        elif operacion.resultado < 0:
            racha_actual += 1

  #  FIX: guardar última racha si el mes acaba en pérdidas
    if racha_actual > 0:
        rachas_perdedoras.append(racha_actual)
        
    if not rachas_perdedoras:
        return 0.0

    suma_rachas = 0

    for racha in rachas_perdedoras:
        suma_rachas += racha

    media_decimal = Decimal(str(suma_rachas)) / Decimal(str(len(rachas_perdedoras)))

    return float(media_decimal)

def calcular_operaciones_ganadoras_consecutivas_actuales_mensual(
    db: Session,
    cuenta_id_trading: int
) -> int:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    racha_actual = 0

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        if operacion.resultado > 0:
            racha_actual += 1
        elif operacion.resultado < 0:
            racha_actual = 0

    return racha_actual

def calcular_racha_ganadora_mas_larga_mensual(
    db: Session,
    cuenta_id_trading: int
) -> int:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    racha_ganadora_mas_larga = 0
    racha_actual = 0

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        if operacion.resultado > 0:
            racha_actual += 1
            if racha_actual > racha_ganadora_mas_larga:
                racha_ganadora_mas_larga = racha_actual
        elif operacion.resultado < 0:
            racha_actual = 0

    return racha_ganadora_mas_larga

def calcular_racha_perdedora_mas_larga_mensual(
    db: Session,
    cuenta_id_trading: int
) -> int:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    racha_perdedora_mas_larga = 0
    racha_actual = 0

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        if operacion.resultado < 0:
            racha_actual += 1
            if racha_actual > racha_perdedora_mas_larga:
                racha_perdedora_mas_larga = racha_actual
        elif operacion.resultado > 0:
            racha_actual = 0

    return racha_perdedora_mas_larga

def calcular_dia_mas_rentable_semanal_mensual(
    db: Session,
    cuenta_id_trading: int
) -> dict:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    ganancias_por_dia = {}

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        dia_semana = operacion.fecha_hora.strftime("%A")

        if dia_semana not in ganancias_por_dia:
            ganancias_por_dia[dia_semana] = Decimal("0")

        ganancias_por_dia[dia_semana] += Decimal(str(operacion.resultado))

    if not ganancias_por_dia:
        return {"dia": None, "ganancia": 0.0}

    dia_mas_rentable = max(ganancias_por_dia, key=ganancias_por_dia.get)
    ganancia_mas_alta_decimal = ganancias_por_dia[dia_mas_rentable]

    return {
        "dia": dia_mas_rentable,
        "ganancia": round(float(ganancia_mas_alta_decimal), 2)
    }
    
def calcular_dia_menos_rentable_semanal_mensual(
    db: Session,
    cuenta_id_trading: int
) -> dict:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    ganancias_por_dia = {}

    for operacion in operaciones:
        if operacion.resultado is None:
            continue

        dia_semana = operacion.fecha_hora.strftime("%A")

        if dia_semana not in ganancias_por_dia:
            ganancias_por_dia[dia_semana] = Decimal("0")

        ganancias_por_dia[dia_semana] += Decimal(str(operacion.resultado))

    if not ganancias_por_dia:
        return {"dia": None, "ganancia": 0.0}

    dia_menos_rentable = min(ganancias_por_dia, key=ganancias_por_dia.get)
    ganancia_mas_baja_decimal = ganancias_por_dia[dia_menos_rentable]

    return {
        "dia": dia_menos_rentable,
        "ganancia": round(float(ganancia_mas_baja_decimal), 2)
    }

def calcular_expectativa_mensual(
    db: Session,
    cuenta_id_trading: int
) -> float:
    winrate = calcular_winrate_mensual(db, cuenta_id_trading)
    ganancias_promedio = calcular_ganancias_promedias_mensuales(db, cuenta_id_trading)
    perdidas_promedio = calcular_perdidas_promedias_mensuales(db, cuenta_id_trading)
    loserate = 100 - winrate
    expectancy=(winrate*ganancias_promedio)/100-(loserate*perdidas_promedio)/100
    
    return expectancy
    

from decimal import Decimal

def get_emocion_principal_operacion(
    operacion: Operacion
) -> list[str] | None:
    
    if operacion.registro_emocional is None:
        return None

    emociones = {
        "confianza": operacion.registro_emocional.confianza,
        "duda": operacion.registro_emocional.duda,
        "euforia": operacion.registro_emocional.euforia,
        "miedo": operacion.registro_emocional.miedo,
        "neutral": operacion.registro_emocional.neutral
    }

    valor_maximo = max(emociones.values())

    if valor_maximo == Decimal("0"):
        return None

    emociones_principales = [
        nombre
        for nombre, valor in emociones.items()
        if valor == valor_maximo
    ]

    return emociones_principales

def get_operaciones_por_emocion_mensual(
    db: Session,
    cuenta_id_trading: int
) -> dict:
    operaciones = get_operaciones_del_mes(db, cuenta_id_trading)

    operaciones_emociones = {
        "confianza": [],
        "duda": [],
        "euforia": [],
        "miedo": [],
        "neutral": []
    }

    for operacion in operaciones:
        if operacion.registro_emocional is not None:
            emociones_principales = get_emocion_principal_operacion(operacion)

            if emociones_principales is not None:
                for emocion in emociones_principales:
                    operaciones_emociones[emocion].append(operacion)

    return operaciones_emociones
    
def calcular_winrate_por_emocion_mensual(
    db: Session,
    cuenta_id_trading: int
) -> dict:
    operaciones_emociones = get_operaciones_por_emocion_mensual(db, cuenta_id_trading)

    winrate_emociones = {
        "confianza": 0.0,
        "duda": 0.0,
        "euforia": 0.0,
        "miedo": 0.0,
        "neutral": 0.0
    }

    for emocion, operaciones in operaciones_emociones.items():
        if not operaciones:
            winrate_emociones[emocion] = 0.0
            continue

        operaciones_ganadoras = 0
        operaciones_totales = 0

        for operacion in operaciones:
            if operacion.resultado is not None:
                operaciones_totales += 1
                if operacion.resultado > 0:
                    operaciones_ganadoras += 1

        if operaciones_totales == 0:
            winrate_emociones[emocion] = 0.0
            continue

        win_rate = (operaciones_ganadoras / operaciones_totales) * 100
        winrate_emociones[emocion] = round(win_rate, 2)

    return winrate_emociones
   

@router.get(
    "/mensual",
    summary="Obtener resumen estadistico mensual de una cuenta de trading",
    description="Calcula y devuelve un resumen estadistico de las operaciones realizadas en el mes actual para una cuenta de trading concreta del usuario autenticado, incluyendo ganancias netas, win rate, ganancias promedio y perdidas promedio.",
)
def get_resumen_mensual(
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading.", examples=[1])],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

    ganancias_netas = calcular_ganancias_netas_mensuales(db, cuenta.id)
    win_rate = calcular_winrate_mensual(db, cuenta.id)
    ganancias_promedio = calcular_ganancias_promedias_mensuales(db, cuenta.id)
    perdidas_promedio = calcular_perdidas_promedias_mensuales(db, cuenta.id)
    max_drawdown = calcular_maximo_drawdown_mensual(db, cuenta.id)
    media_operaciones_hasta_error = calcular_media_operaciones_hasta_error_mensual(db, cuenta.id)
    media_operaciones_hasta_ganadora = calcular_media_operaciones_hasta_ganadora_mensual(db, cuenta.id)
    operaciones_ganadoras_consecutivas_actuales = calcular_operaciones_ganadoras_consecutivas_actuales_mensual(db, cuenta.id)
    racha_ganadora_mas_larga = calcular_racha_ganadora_mas_larga_mensual(db, cuenta.id)
    racha_perdedora_mas_larga = calcular_racha_perdedora_mas_larga_mensual(db, cuenta.id)
    dia_semanal_mas_rentable = calcular_dia_mas_rentable_semanal_mensual(db, cuenta.id)
    dia_semanal_menos_rentable = calcular_dia_menos_rentable_semanal_mensual(db, cuenta.id)
    expectativa = calcular_expectativa_mensual(db, cuenta.id)
    

    return {
        "ganancias_netas": ganancias_netas,
        "win_rate": win_rate,
        "ganancias_promedio": ganancias_promedio,
        "perdidas_promedio": perdidas_promedio,
        "max_drawdown": max_drawdown,
        "media_operaciones_hasta_error": media_operaciones_hasta_error,
        "media_operaciones_hasta_ganadora": media_operaciones_hasta_ganadora,
        "operaciones_ganadoras_consecutivas_actuales": operaciones_ganadoras_consecutivas_actuales,
        "racha_ganadora_mas_larga": racha_ganadora_mas_larga,
        "racha_perdedora_mas_larga": racha_perdedora_mas_larga,
        "dia_semanal_mas_rentable": dia_semanal_mas_rentable,
        "dia_semanal_menos_rentable": dia_semanal_menos_rentable,
        "expectativa": expectativa
    }


@router.get(
    "/emociones",
    summary="Obtener estadisticas de emociones mensuales de una cuenta de trading",
    description="Calcula y devuelve el win rate mensual desglosado por emocion principal identificada en el registro emocional de cada operacion para una cuenta de trading concreta del usuario autenticado.",
    tags=["estadisticas", "emociones"]
)
def get_estadisticas_emociones_mensuales(
    cuenta_id_trading: Annotated[int, Path(description="Identificador de la cuenta de trading.", examples=[1])],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cuenta = get_cuenta_usuario(db, cuenta_id_trading, current_user.id)

    winrate_emociones = calcular_winrate_por_emocion_mensual(db, cuenta.id)

    return winrate_emociones