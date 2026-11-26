from datetime import date
from decimal import Decimal
import unittest

from analytics.cash import cash_report


def line(number, product, cents="100", invoice="I1"):
    return {"invoice_id": invoice, "line_id": number, "product": product,
            "net_cents": cents, "customer": "A", "region": "Domestic",
            "invoice_date": "2015-01-01"}


def receipt(key, amount, day="2025-02-28", invoice="I1"):
    return {"receipt_id": key, "invoice_id": invoice, "amount_cents": amount,
            "receipt_date": day}


class CashReportTests(unittest.TestCase):
    def test_residual_cent_signed_refund_and_header_order(self):
        lines = [line("2", "Sensor"), line("1", "Pump")]
        receipts = [receipt("P1", "101"), receipt("R1", "-3")]
        report = cash_report(lines, receipts, date(2025, 2, 28))
        by_product = {r["product"]: r["amount"] for r in report["products"]
                      if r["window"] == "All history"}
        self.assertEqual(by_product, {"Pump": Decimal(".49"), "Sensor": Decimal(".49")})
        self.assertEqual(report["windows"][-1]["total"], sum(by_product.values()))
        self.assertEqual(report, cash_report(lines[::-1], receipts, date(2025, 2, 28)))

    def test_period_boundaries_and_future_cash(self):
        receipts = [receipt(str(i), "100", day) for i, day in enumerate((
            "2019-02-28", "2019-03-01", "2023-02-28", "2023-03-01",
            "2024-02-29", "2024-03-01",
        ))]
        report = cash_report([line("1", "Assembly")], receipts, date(2024, 2, 29))
        self.assertEqual([r["total"] for r in report["windows"]], [2, 4, 5])

    def test_weighted_allocation_and_rank_limit(self):
        lines, receipts = [], []
        for i in range(21):
            invoice = f"I{i:02}"
            rows = [line("1", "Pump", "300", invoice), line("2", "Sensor", "100", invoice)]
            for row in rows:
                row.update(customer=invoice, region="International")
            lines.extend(rows)
            receipts.append(receipt(f"P{i}", "400", invoice=invoice))
        report = cash_report(lines, receipts, date(2025, 2, 28))
        self.assertEqual(report["windows"][-1]["international"], 84)
        self.assertEqual(report["windows"][-1]["top20_share_pct"], Decimal("95.24"))
        self.assertEqual([r["amount"] for r in report["products"][-2:]], [63, 21])
        ranked = [r["customer"] for r in report["customers"] if r["window"] == "All history"]
        self.assertEqual(ranked, [f"I{i:02}" for i in range(20)])

    def test_rejects_double_application_and_missing_invoice(self):
        payment = receipt("P", "10")
        with self.assertRaisesRegex(ValueError, "Duplicate receipt"):
            cash_report([line("1", "Pump")], [payment, payment], date(2025, 2, 28))
        with self.assertRaisesRegex(ValueError, "unknown invoice"):
            cash_report([], [payment], date(2025, 2, 28))
