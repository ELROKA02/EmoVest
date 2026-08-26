import unittest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Cuenta_Trading, MovimientoCuenta, Operacion, OperacionEjecucion, Usuario
from routers.estadisticas import calcular_saldo_diario_mensual, obtener_vistas_realizadas


class PartialExitStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        user = Usuario(nombre="Test", contrasena="hash", correo_electronico="stats@example.com")
        self.account = Cuenta_Trading(
            usuario=user,
            nombre_cuenta="Cuenta",
            saldo_inicial=Decimal("1000"),
            saldo_actual=Decimal("1000"),
            divisa="EUR",
            tipo_comision="sin_comision",
            valor_comision=0,
        )
        self.db.add(self.account)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _operation(self, *, state, result, closed_at=None):
        operation = Operacion(
            id_cuenta=self.account.id,
            fecha_hora=datetime(2026, 7, 30, 9),
            fecha_cierre=closed_at,
            estado=state,
            tipo_operacion="LONG",
            activo="EURUSD",
            cantidad=Decimal("2"),
            cantidad_abierta=Decimal("0" if state == "CLOSED" else "1"),
            precio_entrada=Decimal("10"),
            resultado=result,
        )
        self.db.add(operation)
        self.db.flush()
        return operation

    def test_keeps_closed_operation_exit_and_cash_flow_views_separate(self):
        closed = self._operation(
            state="CLOSED",
            result=Decimal("15"),
            closed_at=datetime(2026, 8, 2, 12),
        )
        partial = self._operation(state="PARTIALLY_CLOSED", result=Decimal("-3"))
        self.db.add_all([
            OperacionEjecucion(
                operacion=closed,
                rol="ENTRY",
                fecha_hora=datetime(2026, 7, 30, 9),
                cantidad=2,
                precio=10,
                impacto_comision=-1,
                resultado_neto=-1,
                origen="BROKER",
            ),
            OperacionEjecucion(
                operacion=closed,
                rol="EXIT",
                fecha_hora=datetime(2026, 8, 2, 12),
                cantidad=2,
                precio=18,
                resultado_bruto=16,
                resultado_neto=16,
                origen="BROKER",
            ),
            OperacionEjecucion(
                operacion=partial,
                rol="EXIT",
                fecha_hora=datetime(2026, 8, 3, 12),
                cantidad=1,
                precio=7,
                resultado_bruto=-3,
                resultado_neto=-3,
                origen="BROKER",
            ),
            MovimientoCuenta(
                id_cuenta=self.account.id,
                fecha_hora=datetime(2026, 8, 1, 8),
                tipo="DEPOSIT",
                importe=500,
                descripcion="Ingreso",
            ),
        ])
        self.db.commit()

        result = obtener_vistas_realizadas(self.db, self.account.id, 2026, 8)

        self.assertEqual(result["operaciones"]["total"], 1)
        self.assertEqual(result["operaciones"]["resultado_neto"], 15.0)
        self.assertEqual(result["salidas"]["total"], 2)
        self.assertEqual(result["salidas"]["resultado_neto"], 13.0)
        self.assertEqual(result["salidas"]["costes_entrada"], 0.0)
        self.assertEqual(result["movimientos_cuenta"], {"total": 1, "importe_neto": 500.0})
        self.assertEqual(
            calcular_saldo_diario_mensual(self.db, self.account.id, 2026, 8),
            [
                {"fecha": "2026-08-01", "saldo": 1500.0, "es_inicio_mes": True},
                {"fecha": "2026-08-02", "saldo": 1515.0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
