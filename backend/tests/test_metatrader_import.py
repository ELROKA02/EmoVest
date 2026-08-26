import unittest

from fastapi import HTTPException

from metatrader_import import parse_mt5_report


def report_html(headers, rows, *, account="123456", broker="Demo Broker"):
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in [headers, *rows]
    )
    return f"""<html><body><p>Account: {account}</p><p>Company: {broker}</p>
    <table><tr><th>Deals</th></tr></table><table>{body}</table></body></html>"""


class MetaTraderImportParserTests(unittest.TestCase):
    def test_groups_partial_exits_and_keeps_movements_and_open_positions_separate(self):
        headers = [
            "Time", "Deal", "Position", "Symbol", "Type", "Direction",
            "Volume", "Price", "Commission", "Fee", "Swap", "Profit", "Comment",
        ]
        rows = [
            ["2026.08.01 09:00:00", "1", "42", "EURUSD", "buy", "in", "1.00", "10", "-1", "0", "0", "0", ""],
            ["2026.08.01 10:00:00", "2", "42", "EURUSD", "sell", "out", "0.40", "20", "-0.4", "0", "0", "4", "partial"],
            ["2026.08.01 11:00:00", "3", "42", "EURUSD", "sell", "out", "0.60", "25", "-0.6", "0", "-0.1", "9", "close"],
            ["2026.08.01 08:00:00", "4", "", "", "balance", "", "0", "0", "0", "0", "0", "1000", "Deposit"],
            ["2026.08.01 12:00:00", "5", "77", "GBPUSD", "sell", "in", "2", "30", "0", "0", "0", "0", "open"],
        ]

        parsed = parse_mt5_report(report_html(headers, rows).encode(), "Europe/Madrid")

        self.assertEqual(parsed["account"], "123456")
        self.assertEqual(parsed["broker"], "Demo Broker")
        self.assertEqual(len(parsed["proposed_operations"]), 1)
        operation = parsed["proposed_operations"][0]
        self.assertEqual(operation["position"], "42")
        self.assertEqual(operation["tipo_operacion"], "LONG")
        self.assertEqual([item["cantidad"] for item in operation["exits"]], ["0.40", "0.60"])
        self.assertEqual(len(parsed["movements"]), 1)
        self.assertEqual(parsed["movements"][0]["tipo"], "DEPOSIT")
        self.assertEqual(parsed["skipped_open"][0]["position"], "77")
        self.assertEqual(parsed["errors"], [])
        self.assertEqual(parsed["conflicts"], [])

    def test_accepts_spanish_utf16_report(self):
        headers = [
            "Hora", "Operación", "Posición", "Símbolo", "Tipo", "Dirección",
            "Volumen", "Precio", "Comisión", "Tasa", "Swap", "Beneficio",
        ]
        rows = [
            ["2026.08.01 09:00:00", "10", "9", "DAX40", "venta", "entrada", "1,5", "100,5", "-1,25", "0", "0", "0"],
            ["2026.08.01 10:00:00", "11", "9", "DAX40", "compra", "salida", "1,5", "90,5", "-1,25", "0", "0", "15"],
        ]
        parsed = parse_mt5_report(report_html(headers, rows).encode("utf-16"), "UTC")

        self.assertEqual(parsed["encoding"], "utf-16")
        self.assertEqual(parsed["proposed_operations"][0]["tipo_operacion"], "SHORT")
        self.assertEqual(parsed["proposed_operations"][0]["cantidad"], "1.5")

    def test_requires_valid_iana_timezone(self):
        with self.assertRaises(HTTPException) as raised:
            parse_mt5_report(b"<html></html>", "Madrid")
        self.assertEqual(raised.exception.status_code, 422)

    def test_manual_resolution_groups_deals_without_position(self):
        headers = [
            "Time", "Deal", "Position", "Symbol", "Type", "Direction",
            "Volume", "Price", "Commission", "Fee", "Swap", "Profit",
        ]
        rows = [
            ["2026.08.01 09:00:00", "20", "", "EURUSD", "buy", "in", "1", "10", "0", "0", "0", "0"],
            ["2026.08.01 10:00:00", "21", "", "EURUSD", "sell", "out", "1", "15", "0", "0", "0", "5"],
        ]
        raw = report_html(headers, rows).encode()
        unresolved = parse_mt5_report(raw, "UTC")
        self.assertEqual(len(unresolved["conflicts"]), 2)
        keys = {row["deal"]: row["source_key"] for row in unresolved["normalized_rows"]}

        resolved = parse_mt5_report(raw, "UTC", resolutions=[{
            "position": "manual-20",
            "tipo_operacion": "LONG",
            "entries": [keys["20"]],
            "exits": [keys["21"]],
        }])

        self.assertEqual(resolved["conflicts"], [])
        self.assertEqual(resolved["proposed_operations"][0]["position"], "manual-20")

    def test_duplicate_deal_and_zero_price_are_reported(self):
        headers = [
            "Time", "Deal", "Position", "Symbol", "Type", "Direction",
            "Volume", "Price", "Commission", "Fee", "Swap", "Profit",
        ]
        rows = [
            ["2026.08.01 09:00:00", "30", "3", "EURUSD", "buy", "in", "1", "0", "0", "0", "0", "0"],
            ["2026.08.01 10:00:00", "30", "3", "EURUSD", "sell", "out", "1", "15", "0", "0", "0", "5"],
        ]
        parsed = parse_mt5_report(report_html(headers, rows).encode(), "UTC")
        self.assertTrue(any("precio positivos" in item["error"] for item in parsed["errors"]))
        self.assertTrue(any("duplicado" in item["error"] for item in parsed["errors"]))

    def test_rejects_non_mt5_html(self):
        with self.assertRaises(HTTPException) as raised:
            parse_mt5_report(b"<html><table><tr><td>hello</td></tr></table></html>", "UTC")
        self.assertEqual(raised.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
