"""Order-level delivery performance reconstructed from line-level movements."""

from collections import defaultdict
from datetime import date


def shipping_report(orders, lines, shipments, cutoff):
    """Compare each line's shipped and open quantities with its two target dates."""
    order_by_id = {}
    for row in orders:
        key = row["order_id"]
        if not key or key in order_by_id:
            raise ValueError(f"Missing or duplicate order ID: {key!r}")
        if row["status"] not in {"active", "cancelled"}:
            raise ValueError(f"Unsupported order status for {key}")
        order_by_id[key] = row, date.fromisoformat(row["placed_date"])

    line_by_key = {}
    for row in lines:
        key = (row["order_id"], row["line_id"])
        if key[0] not in order_by_id or not key[1] or key in line_by_key:
            raise ValueError(f"Unknown order or duplicate/missing line: {key}")
        quantity = int(row["quantity"])
        if quantity <= 0:
            raise ValueError(f"Invalid ordered quantity: {key}")
        dates = {basis: date.fromisoformat(row[f"{basis}_date"])
                 for basis in ("requested", "promised")}
        line_by_key[key] = row["product"], quantity, dates

    movements = defaultdict(list)
    for row in shipments:
        key = row["order_id"], row["line_id"]
        if key not in line_by_key:
            raise ValueError(f"Shipment with unknown line: {key}")
        quantity = int(row["quantity"])
        shipped = date.fromisoformat(row["shipped_date"])
        if quantity <= 0 or shipped < order_by_id[key[0]][1]:
            raise ValueError(f"Invalid shipment: {key}")
        if shipped <= cutoff:
            movements[key].append((shipped, quantity))

    active = {key for key, (row, placed) in order_by_id.items()
              if placed <= cutoff and row["status"] == "active"}
    due = defaultdict(set)
    late = defaultdict(set)
    overdue = defaultdict(set)
    exceptions = []
    for key, (product, quantity, targets) in line_by_key.items():
        order, line = key
        if order not in active:
            continue
        delivered = movements[key]
        remaining = quantity - sum(qty for _, qty in delivered)
        if remaining < 0:
            raise ValueError(f"Shipped quantity exceeds order: {key}")
        for basis, target in targets.items():
            if target > cutoff:
                continue
            due[basis].add(order)
            shipped_late = sum(qty for day, qty in delivered if day > target)
            overdue_qty = remaining if target < cutoff else 0
            if shipped_late:
                late[basis].add(order)
            if overdue_qty:
                overdue[basis].add(order)
            if shipped_late or overdue_qty:
                exceptions.append(dict(
                    basis=basis, order=order, line=line, product=product,
                    customer=order_by_id[order][0]["customer"], target=target.isoformat(),
                    ordered=quantity, shipped_late=shipped_late, open_overdue=overdue_qty,
                    days_overdue=(cutoff - target).days if overdue_qty else 0,
                ))

    summary = []
    for basis in ("requested", "promised"):
        delayed = late[basis] | overdue[basis]
        due_count = len(due[basis])
        summary.append(dict(
            basis=basis, active_orders=len(active), due_orders=due_count,
            shipped_late_orders=len(late[basis]), open_overdue_orders=len(overdue[basis]),
            both=len(late[basis] & overdue[basis]), delayed_orders=len(delayed),
            delayed_pct=round(100 * len(delayed) / due_count, 2) if due_count else None,
        ))
    exceptions.sort(key=lambda row: (row["basis"], -row["days_overdue"], row["order"], row["line"]))
    return summary, exceptions
