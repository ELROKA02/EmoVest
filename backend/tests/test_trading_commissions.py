import unittest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Cuenta_Trading, Operacion, Usuario
from routers.operaciones import actualizar_resultados_operacion
from trading_commissions import (
    calculate_commission,
    calculate_gross_result,
    calculate_net_result,
)


class TradingCommissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        cls.Session = sessionmaker(bind=engine)

    def setUp(self):
        self.db = self.Session()
        self.user = Usuario(nombre="Trader", correo_electronico="trader@example.dev", contrasena="hash")
        self.db.add(self.user)
        self.db.flush()
        self.account = Cuenta_Trading(
            id_usuario=self.user.id,
            nombre_cuenta="Principal",
            saldo_inicial=Decimal("1000"),
            saldo_actual=Decimal("1000"),
            divisa="EUR",
            tipo_comision="porcentaje",
            valor_comision=Decimal("1"),
        )
        self.db.add(self.account)
        self.db.commit()

    def tearDown(self):
        self.db.query(Operacion).delete()
        self.db.query(Cuenta_Trading).delete()
        self.db.query(Usuario).delete()
        self.db.commit()
        self.db.close()

    def test_fixed_commission_is_charged_once_per_operation(self):
        commission = calculate_commission("fija", Decimal("2.5"), Decimal("3"), Decimal("100"))

        self.assertEqual(commission, Decimal("2.500000"))
        self.assertEqual(calculate_net_result(Decimal("25"), commission), Decimal("22.500000"))

    def test_percentage_commission_uses_entry_notional(self):
        commission = calculate_commission("porcentaje", Decimal("0.2"), Decimal("3"), Decimal("100"))

        self.assertEqual(commission, Decimal("0.600000"))
        self.assertEqual(calculate_net_result(Decimal("25"), commission), Decimal("24.400000"))

    def test_open_operation_has_a_commission_but_no_net_result(self):
        commission = calculate_commission("fija", Decimal("1"), Decimal("2"), Decimal("50"))

        self.assertEqual(commission, Decimal("1.000000"))
        self.assertIsNone(calculate_gross_result("LONG", Decimal("2"), Decimal("50"), None))
        self.assertIsNone(calculate_net_result(None, commission))

    def test_short_gross_result_is_calculated_before_commission(self):
        gross = calculate_gross_result("SHORT", Decimal("2"), Decimal("100"), Decimal("90"))

        self.assertEqual(gross, Decimal("20.000000"))

    def test_net_result_is_a_snapshot_and_updates_balance_delta(self):
        operation = Operacion(
            id_cuenta=self.account.id,
            fecha_hora=datetime(2026, 1, 1),
            tipo_operacion="LONG",
            activo="BTC",
            cantidad=Decimal("2"),
            precio_entrada=Decimal("100"),
            precio_salida=Decimal("110"),
        )
        actualizar_resultados_operacion(operation, self.account)
        self.db.add(operation)
        self.account.saldo_actual += operation.resultado
        self.db.commit()

        self.assertEqual(operation.resultado_bruto, Decimal("20.000000"))
        self.assertEqual(operation.comisiones, Decimal("2.000000"))
        self.assertEqual(operation.resultado, Decimal("18.000000"))
        self.assertEqual(self.account.saldo_actual, Decimal("1018.000000"))

        self.account.tipo_comision = "fija"
        self.account.valor_comision = Decimal("5")
        self.db.commit()
        self.db.refresh(operation)
        self.assertEqual(operation.comisiones, Decimal("2.000000"))


if __name__ == "__main__":
    unittest.main()
