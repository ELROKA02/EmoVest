import unittest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException

from models import Operacion
from trading_operations import build_manual_executions, recalculate_operation


class TradingOperationExecutionTests(unittest.TestCase):
    def operation(self, *, side="LONG", quantity="1", when=None):
        return Operacion(
            fecha_hora=when or datetime(2026, 8, 1, 9),
            tipo_operacion=side,
            cantidad=Decimal(quantity),
            activo="EURUSD",
            precio_entrada=Decimal("10"),
        )

    @staticmethod
    def account(commission="2"):
        return SimpleNamespace(tipo_comision="fija", valor_comision=Decimal(commission))

    def test_open_partial_and_closed_states_use_execution_aggregates(self):
        open_operation = self.operation()
        open_operation.ejecuciones.extend(build_manual_executions(open_operation, self.account(), []))
        self.assertEqual(recalculate_operation(open_operation), Decimal("-2.000000"))
        self.assertEqual(open_operation.estado, "OPEN")
        self.assertIsNone(open_operation.resultado)
        self.assertEqual(open_operation.cantidad_abierta, Decimal("1.000000"))

        partial = self.operation()
        partial.ejecuciones.extend(build_manual_executions(partial, self.account(), [{
            "fecha_hora": "2026-08-01T10:00:00",
            "cantidad": "0.4",
            "precio": "20",
            "comision": "0.4",
            "swap": "-0.1",
            "tasa": "0.1",
        }]))
        self.assertEqual(recalculate_operation(partial), Decimal("1.400000"))
        self.assertEqual(partial.estado, "PARTIALLY_CLOSED")
        self.assertEqual(partial.cantidad_abierta, Decimal("0.600000"))
        self.assertIsNone(partial.fecha_cierre)

        closed = self.operation()
        closed.ejecuciones.extend(build_manual_executions(closed, self.account(), [
            {"fecha_hora": "2026-08-01T10:00:00", "cantidad": "0.4", "precio": "20"},
            {"fecha_hora": "2026-08-01T11:00:00", "cantidad": "0.6", "precio": "25"},
        ]))
        self.assertEqual(recalculate_operation(closed), Decimal("11.000000"))
        self.assertEqual(closed.estado, "CLOSED")
        self.assertEqual(closed.cantidad_abierta, Decimal("0.000000"))
        self.assertEqual(closed.precio_salida, Decimal("23.000000"))
        self.assertEqual(closed.fecha_cierre, datetime(2026, 8, 1, 11))

    def test_short_and_manual_gross_without_price(self):
        short = self.operation(side="SHORT")
        short.ejecuciones.extend(build_manual_executions(short, self.account("0"), [{
            "fecha_hora": "2026-08-01T10:00:00",
            "cantidad": "1",
            "precio": "7",
        }]))
        self.assertEqual(recalculate_operation(short), Decimal("3.000000"))

        legacy = self.operation()
        legacy.ejecuciones.extend(build_manual_executions(legacy, self.account("0"), [{
            "fecha_hora": "2026-08-01T10:00:00",
            "cantidad": "1",
            "precio": None,
            "resultado_bruto": "8.5",
        }]))
        self.assertEqual(recalculate_operation(legacy), Decimal("8.500000"))
        self.assertIsNone(legacy.precio_salida)

    def test_rejects_over_close_and_normalizes_aware_datetimes_to_utc(self):
        operation = self.operation(when=datetime(2026, 8, 1, 9, tzinfo=timezone.utc))
        with self.assertRaises(HTTPException):
            executions = build_manual_executions(operation, self.account("0"), [{
                "fecha_hora": "2026-08-01T12:00:00+02:00",
                "cantidad": "1.1",
                "precio": "20",
            }])
            operation.ejecuciones.extend(executions)
            recalculate_operation(operation)

        valid = self.operation(when=datetime(2026, 8, 1, 9, tzinfo=timezone.utc))
        valid.ejecuciones.extend(build_manual_executions(valid, self.account("0"), [{
            "fecha_hora": "2026-08-01T12:00:00+02:00",
            "cantidad": "1",
            "precio": "20",
        }]))
        recalculate_operation(valid)
        self.assertEqual(valid.fecha_hora, datetime(2026, 8, 1, 9))
        self.assertEqual(valid.fecha_cierre, datetime(2026, 8, 1, 10))


if __name__ == "__main__":
    unittest.main()
