from datetime import date
import unittest

from analytics.shipping import shipping_report


class ShippingTests(unittest.TestCase):
    def test_partial_late_shipment_and_open_balance_count_once(self):
        orders = [dict(order_id="A", customer="C", placed_date="2025-03-01", status="active")]
        lines = [dict(order_id="A", line_id="1", product="P", quantity="10",
                      requested_date="2025-03-06", promised_date="2025-03-10")]
        shipments = [dict(order_id="A", line_id="1", quantity="4", shipped_date=d)
                     for d in ("2025-03-07", "2025-03-14")]
        summary, exc = shipping_report(orders, lines, shipments, date(2025, 3, 10))
        requested, promised = summary
        self.assertEqual((requested["delayed_orders"], requested["both"]), (1, 1))
        self.assertEqual((exc[0]["shipped_late"], exc[0]["open_overdue"]), (4, 6))
        self.assertEqual((promised["due_orders"], promised["delayed_orders"]), (1, 0))

    def test_one_order_with_two_late_lines_and_cancelled_order(self):
        orders = [dict(order_id=k, customer="C", placed_date="2025-03-01", status=status)
                  for k, status in [("A", "active"), ("B", "cancelled")]]
        lines = [dict(order_id=o, line_id=i, product="P", quantity="1",
                      requested_date="2025-03-06", promised_date="2025-03-06")
                 for o in ("A", "B") for i in ("1", "2")]
        summary, exc = shipping_report(orders, lines, [], date(2025, 3, 10))
        self.assertEqual(summary[0]["due_orders"], 1)
        self.assertEqual(summary[0]["delayed_pct"], 100)
        self.assertEqual(len(exc), 4)

    def test_empty_due_population(self):
        summary, exc = shipping_report([], [], [], date(2025, 3, 10))
        self.assertIsNone(summary[0]["delayed_pct"])
        self.assertEqual(exc, [])
