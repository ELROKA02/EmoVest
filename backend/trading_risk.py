"""Cálculos de riesgo reproducibles para operaciones registradas."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def calculate_operation_risk(
    *,
    balance: Decimal | int | float | None,
    quantity: Decimal | int | float | None,
    entry_price: Decimal | int | float | None,
    stop_loss: Decimal | int | float | None,
    side: str,
) -> tuple[Decimal | None, Decimal | None]:
    """Return risk amount and balance percentage when the stop is valid."""
    try:
        reference_balance = Decimal(str(balance))
        position_size = Decimal(str(quantity))
        entry = Decimal(str(entry_price))
        stop = Decimal(str(stop_loss))
    except (InvalidOperation, TypeError, ValueError):
        return None, None

    if reference_balance <= 0 or position_size <= 0:
        return None, None

    distance = entry - stop if side == "LONG" else stop - entry
    if distance <= 0:
        return None, None

    amount = (distance * position_size).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    percentage = ((amount / reference_balance) * Decimal("100")).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )
    return amount, percentage
