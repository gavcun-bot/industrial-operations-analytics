"""Create repeatable fictional orders, fulfillment events, invoices, and applied receipts."""

import csv
from datetime import date, timedelta
from pathlib import Path
from random import Random


PRODUCTS = (
    ("Bench Mixer", 54500),
    ("Panel Gauge", 18250),
    ("Sample Rack", 7600),
    ("Flow Meter", 37300),
    ("Probe Mount", 9200),
    ("Bench Scale", 51600),
    ("Test Stand", 82400),
    ("Control Dial", 6100),
)
SCHEMAS = {
    "orders": ("order_id", "placed_date", "customer", "region", "status"),
    "lines": ("order_id", "line_id", "product", "quantity", "requested_date", "promised_date"),
    "shipments": ("order_id", "line_id", "quantity", "shipped_date"),
    "invoice_lines": ("invoice_id", "line_id", "product", "net_cents", "customer", "region", "invoice_date"),
    "receipts": ("receipt_id", "invoice_id", "amount_cents", "receipt_date"),
}


def generate(directory: Path) -> None:
    """Write five CSVs from a fixed seed. All IDs, amounts, and dates are invented."""
    directory.mkdir(parents=True, exist_ok=True)
    rng = Random(63109)
    rows = {name: [] for name in SCHEMAS}
    snapshot = date(2026, 1, 31)
    for month_number in range(97):  # January 2018 through January 2026
        year_offset, month_offset = divmod(month_number, 12)
        for _ in range(rng.randint(3, 6)):
            placed = date(2018 + year_offset, month_offset + 1, rng.randint(1, 26))
            number = len(rows["orders"]) + 1
            order_id = f"DEMO-O{number:04d}"
            invoice_id = f"DEMO-I{number:04d}"
            account = rng.randint(1, 40)
            customer = f"Demo buyer {account:02d}"
            region = "international" if account % 5 < 2 else "domestic"
            status = "cancelled" if number % 23 == 0 else "active"
            rows["orders"].append((order_id, placed, customer, region, status))

            billed = []
            ship_dates = []
            for index, (product, unit_cents) in enumerate(rng.sample(PRODUCTS, rng.randint(1, 3)), 1):
                line_id = f"DEMO-L{index:02d}"
                qty = rng.randint(2, 12)
                requested = placed + timedelta(days=rng.randint(8, 30))
                promised = requested + timedelta(days=rng.randint(-3, 12))
                rows["lines"].append((order_id, line_id, product, qty, requested, promised))
                if status == "cancelled":
                    continue

                first_ship = max(placed + timedelta(days=1), promised + timedelta(days=rng.randint(-12, 4)))
                # A few fourth-quarter lines are waiting for stock at the demo cutoff.
                if placed >= date(2025, 10, 1) and number % 4 == 0:
                    first_ship += timedelta(days=75)
                pieces = [(qty, first_ship)]
                if rng.random() < 0.30:
                    first_qty = rng.randint(1, qty - 1)
                    final_ship = first_ship + timedelta(days=rng.randint(2, 15))
                    pieces = [(first_qty, first_ship), (qty - first_qty, final_ship)]
                shipped = 0
                for piece_qty, ship_date in pieces:
                    if ship_date <= snapshot:
                        rows["shipments"].append((order_id, line_id, piece_qty, ship_date))
                        ship_dates.append(ship_date)
                        shipped += piece_qty
                if shipped:
                    billed.append((line_id, product, shipped * unit_cents))

            if not billed:
                continue
            invoice_date = max(ship_dates) + timedelta(days=rng.randint(0, 2))
            if invoice_date > snapshot:
                continue
            for line_id, product, net_cents in billed:
                rows["invoice_lines"].append((invoice_id, line_id, product, net_cents, customer, region, invoice_date))

            total = sum(net_cents for _, _, net_cents in billed)
            paid = invoice_date + timedelta(days=rng.randint(7, 40))
            payments = [(total, paid)]
            if number % 3 == 0:
                deposit = total // 3
                payments = [(deposit, paid), (total - deposit, paid + timedelta(days=17))]
            if number % 13 == 0:
                payments.append((-(total // 20), paid + timedelta(days=31)))
            for index, (amount, receipt_date) in enumerate(payments, 1):
                if receipt_date <= snapshot:
                    receipt_id = f"DEMO-R{number:04d}-{index}"
                    rows["receipts"].append((receipt_id, invoice_id, amount, receipt_date))

    for table, columns in SCHEMAS.items():
        with (directory / f"{table}.csv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.writer(target, lineterminator="\n")
            writer.writerow(columns)
            writer.writerows(rows[table])
