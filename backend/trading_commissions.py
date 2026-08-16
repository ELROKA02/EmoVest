"""Commission and net-result calculations shared by operation routes."""
from decimal import Decimal, ROUND_HALF_UP


COMMISSION_TYPES = {"sin_comision", "fija", "porcentaje"}
MONEY_QUANTUM = Decimal("0.000001")


def to_decimal(value) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_commission(tipo_comision: str | None, valor_comision, cantidad, precio_entrada) -> Decimal:
    """Return the one-off commission for an operation's entry notional."""
    if tipo_comision == "sin_comision" or not tipo_comision:
        return Decimal("0")

    value = to_decimal(valor_comision or 0)
    if tipo_comision == "fija":
        return money(value)
    if tipo_comision == "porcentaje":
        return money(to_decimal(cantidad) * to_decimal(precio_entrada) * value / Decimal("100"))
    raise ValueError("Tipo de comisión no válido")


def calculate_gross_result(tipo_operacion: str, cantidad, precio_entrada, precio_salida) -> Decimal | None:
    if precio_salida is None:
        return None
    entry = to_decimal(precio_entrada)
    exit_price = to_decimal(precio_salida)
    quantity = to_decimal(cantidad)
    result = (exit_price - entry) * quantity if tipo_operacion == "LONG" else (entry - exit_price) * quantity
    return money(result)


def calculate_net_result(resultado_bruto, comisiones: Decimal) -> Decimal | None:
    if resultado_bruto is None:
        return None
    return money(to_decimal(resultado_bruto) - comisiones)
