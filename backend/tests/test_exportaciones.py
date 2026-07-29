import csv
import unittest
from datetime import datetime
from decimal import Decimal
from io import StringIO

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Cuenta_Trading, Operacion, Usuario
from routers.exportaciones import export_operaciones_csv


class ExportOperacionesTests(unittest.TestCase):
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
        self.user = Usuario(nombre="Samuel", correo_electronico="samuel@test.dev", contrasena="hash")
        self.db.add(self.user)
        self.db.flush()
        self.cuenta = Cuenta_Trading(
            id_usuario=self.user.id,
            nombre_cuenta="Principal",
            saldo_inicial=Decimal("1000"),
            saldo_actual=Decimal("1000"),
            divisa="EUR",
        )
        self.db.add(self.cuenta)
        self.db.flush()
        self.db.add_all([
            Operacion(
                id_cuenta=self.cuenta.id,
                fecha_hora=datetime(2026, 1, 1, 10),
                tipo_operacion="LONG",
                activo="BTC",
                cantidad=Decimal("1"),
                precio_entrada=Decimal("100"),
                resultado=Decimal("30"),
            ),
            Operacion(
                id_cuenta=self.cuenta.id,
                fecha_hora=datetime(2026, 1, 2, 10),
                tipo_operacion="SHORT",
                activo="ETH",
                cantidad=Decimal("1"),
                precio_entrada=Decimal("100"),
                resultado=Decimal("10"),
            ),
            Operacion(
                id_cuenta=self.cuenta.id,
                fecha_hora=datetime(2026, 1, 3, 10),
                tipo_operacion="LONG",
                activo="btc",
                cantidad=Decimal("1"),
                precio_entrada=Decimal("100"),
                resultado=Decimal("20"),
            ),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.query(Operacion).delete()
        self.db.query(Cuenta_Trading).delete()
        self.db.query(Usuario).delete()
        self.db.commit()
        self.db.close()

    def test_exports_all_matching_rows_with_active_filters_and_order(self):
        response = export_operaciones_csv(
            cuenta_ids=[self.cuenta.id],
            fecha_desde=None,
            fecha_hasta=None,
            tipo_operacion="LONG",
            activo="BTC",
            sort_by="beneficio",
            sort_direction="desc",
            db=self.db,
            current_user=self.user,
        )

        rows = list(csv.DictReader(StringIO(response.body.decode("utf-8"))))

        self.assertEqual([row["resultado"] for row in rows], ["30.000000", "20.000000"])
        self.assertEqual({row["tipo_operacion"] for row in rows}, {"LONG"})
        self.assertEqual({row["activo"].lower() for row in rows}, {"btc"})


if __name__ == "__main__":
    unittest.main()
