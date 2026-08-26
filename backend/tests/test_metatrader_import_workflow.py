import asyncio
import unittest
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers, UploadFile
from fastapi import HTTPException

from database import Base
from metatrader_import import parse_mt5_report
from models import Cuenta_Trading, Importacion, MovimientoCuenta, Operacion, Usuario
from routers.importaciones import commit_metatrader, preview_metatrader


REPORT = b"""<html><body>
<p>Account: 123456</p><p>Company: Demo Broker</p>
<table>
<tr><th>Time</th><th>Deal</th><th>Position</th><th>Symbol</th><th>Type</th><th>Direction</th><th>Volume</th><th>Price</th><th>Commission</th><th>Fee</th><th>Swap</th><th>Profit</th><th>Comment</th></tr>
<tr><td>2026.08.01 09:00:00</td><td>1</td><td>42</td><td>EURUSD</td><td>buy</td><td>in</td><td>1</td><td>10</td><td>-1</td><td>0</td><td>0</td><td>0</td><td></td></tr>
<tr><td>2026.08.01 10:00:00</td><td>2</td><td>42</td><td>EURUSD</td><td>sell</td><td>out</td><td>1</td><td>25</td><td>-1</td><td>0</td><td>-0.5</td><td>15</td><td></td></tr>
<tr><td>2026.08.01 08:00:00</td><td>3</td><td></td><td></td><td>balance</td><td></td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>100</td><td>Deposit</td></tr>
</table></body></html>"""


def upload():
    return UploadFile(BytesIO(REPORT), filename="report.html", headers=Headers({"content-type": "text/html"}))


class MetaTraderImportWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = Usuario(nombre="Test", contrasena="hash", correo_electronico="mt5@example.com")
        self.account = Cuenta_Trading(
            usuario=self.user,
            nombre_cuenta="MT5",
            saldo_inicial=1000,
            saldo_actual=1000,
            divisa="EUR",
            tipo_comision="sin_comision",
            valor_comision=0,
        )
        self.db.add(self.account)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_preview_commit_and_retry_are_atomic_and_idempotent(self):
        current_user = SimpleNamespace(id=self.user.id)
        preview = asyncio.run(preview_metatrader(
            cuenta_id_trading=self.account.id,
            zona_horaria="UTC",
            file=upload(),
            db=self.db,
            current_user=current_user,
        ))
        self.assertTrue(preview["ready_to_commit"])
        self.assertEqual(len(preview["normalized_rows"]), 3)
        self.assertEqual(preview["summary"]["operations"], 1)
        self.assertEqual(preview["summary"]["movements"], 1)

        with self.assertRaises(HTTPException) as changed:
            asyncio.run(commit_metatrader(
                cuenta_id_trading=self.account.id,
                zona_horaria="UTC",
                expected_preview_token=preview["preview_token"],
                file=upload(),
                resolution_json='[{"position":"changed","tipo_operacion":"LONG","entries":[],"exits":[]}]',
                db=self.db,
                current_user=current_user,
            ))
        self.assertEqual(changed.exception.status_code, 409)

        committed = asyncio.run(commit_metatrader(
            cuenta_id_trading=self.account.id,
            zona_horaria="UTC",
            expected_preview_token=preview["preview_token"],
            file=upload(),
            resolution_json=None,
            db=self.db,
            current_user=current_user,
        ))
        self.assertEqual(committed["created_operations"], 1)
        self.assertEqual(committed["created_movements"], 1)
        self.assertEqual(Decimal(str(committed["balance_delta"])), Decimal("112.5"))
        self.assertEqual(self.db.query(Operacion).one().estado, "CLOSED")
        self.assertEqual(self.db.query(Operacion).one().resultado, Decimal("12.500000"))
        self.assertEqual(self.db.query(MovimientoCuenta).one().importe, Decimal("100.000000"))
        self.assertEqual(self.db.query(Importacion).count(), 1)

        retried = asyncio.run(commit_metatrader(
            cuenta_id_trading=self.account.id,
            zona_horaria="UTC",
            expected_preview_token=preview["preview_token"],
            file=upload(),
            resolution_json=None,
            db=self.db,
            current_user=current_user,
        ))
        self.assertTrue(retried["already_imported"])
        self.assertEqual(self.db.query(Operacion).count(), 1)
        self.db.refresh(self.account)
        self.assertEqual(self.account.saldo_actual, Decimal("1112.500000"))


if __name__ == "__main__":
    unittest.main()
