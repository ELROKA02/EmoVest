import unittest
from decimal import Decimal

from trading_risk import calculate_operation_risk


class TradingRiskTests(unittest.TestCase):
    def test_calculates_long_risk_against_balance(self):
        amount, percentage = calculate_operation_risk(
            balance=Decimal("10000"),
            quantity=Decimal("2"),
            entry_price=Decimal("100"),
            stop_loss=Decimal("90"),
            side="LONG",
        )

        self.assertEqual(amount, Decimal("20.000000"))
        self.assertEqual(percentage, Decimal("0.2000"))

    def test_rejects_stop_on_the_wrong_side(self):
        amount, percentage = calculate_operation_risk(
            balance=1000,
            quantity=1,
            entry_price=100,
            stop_loss=105,
            side="LONG",
        )

        self.assertIsNone(amount)
        self.assertIsNone(percentage)


if __name__ == "__main__":
    unittest.main()
