"""Allocate applied USD receipts using invoice-line value, then rank net collections."""

from collections import defaultdict
from datetime import date
from decimal import Decimal


def _allocate(amount, lines):
    """Return signed cent allocations; resolve equal remainders by line ID."""
    basis = sum(weight for _, _, weight in lines)
    if basis == 0:
        if amount:
            raise ValueError("A nonzero receipt requires a positive invoice value")
        return [0] * len(lines)

    shares = [divmod(abs(amount) * weight, basis) for _, _, weight in lines]
    allocated = [whole for whole, _ in shares]
    residual = abs(amount) - sum(allocated)
    order = sorted(range(len(lines)), key=lambda i: (-shares[i][1], lines[i][0]))
    for i in order[:residual]:
        allocated[i] += 1
    return allocated if amount >= 0 else [-cents for cents in allocated]


def _prior_anniversary(cutoff, years):
    try:
        return cutoff.replace(year=cutoff.year - years)
    except ValueError:  # February 29 in a non-leap comparison year
        return date(cutoff.year - years, 2, 28)


def _dollars(cents):
    return Decimal(cents).scaleb(-2)


def _top_rows(values, window, label):
    ranked = sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))[:20]
    return [
        {"window": window, "rank": rank, label: name, "amount": _dollars(cents)}
        for rank, (name, cents) in enumerate(ranked, start=1)
    ]


def cash_report(invoice_lines, receipts, cutoff):
    """Summarize applied cash by receipt date, up to and including the cutoff.

    Invoice lines use nonnegative net cents. A signed refund reverses the
    corresponding weighted allocation. Each receipt/invoice pair is unique.
    A finite window excludes its prior anniversary and includes its cutoff.
    All output currency fields are Decimal dollars. Share is a percentage,
    or None when net collections are nonpositive.
    """
    details = {}
    lines = defaultdict(list)
    line_keys = set()
    for row in invoice_lines:
        invoice = row["invoice_id"]
        key = (invoice, row["line_id"])
        if key in line_keys:
            raise ValueError(f"Duplicate invoice line {key!r}")
        line_keys.add(key)
        info = (row["customer"], row["region"].strip().lower(),
                date.fromisoformat(row["invoice_date"]))
        if info[1] not in {"domestic", "international"}:
            raise ValueError(f"Unknown bill-to region on invoice {invoice}")
        if details.setdefault(invoice, info) != info:
            raise ValueError(f"Inconsistent header fields on invoice {invoice}")
        weight = int(row["net_cents"])
        if weight < 0:
            raise ValueError(f"Negative allocation basis on invoice {invoice}")
        lines[invoice].append((row["line_id"], row["product"], weight))

    periods = [
        ("Last 12 months", _prior_anniversary(cutoff, 1)),
        ("Last 5 years", _prior_anniversary(cutoff, 5)),
        ("All history", None),
    ]
    regions = defaultdict(lambda: defaultdict(int))
    products = defaultdict(lambda: defaultdict(int))
    customers = defaultdict(lambda: defaultdict(int))
    annual = defaultdict(lambda: defaultdict(int))
    seen = set()
    for row in receipts:
        received = date.fromisoformat(row["receipt_date"])
        if received > cutoff:
            continue
        invoice = row["invoice_id"]
        key = (row["receipt_id"], invoice)
        if key in seen:
            raise ValueError(f"Duplicate receipt application {key!r}")
        seen.add(key)
        if invoice not in details:
            raise ValueError(f"Receipt references unknown invoice {invoice}")
        customer, region, issued = details[invoice]
        if received < issued:
            raise ValueError(f"Receipt predates invoice {invoice}")
        amount = int(row["amount_cents"])
        allocation = _allocate(amount, lines[invoice])
        annual[received.year][region] += amount
        for window, start in periods:
            if start is not None and received <= start:
                continue
            regions[window][region] += amount
            customers[window][customer] += amount
            for (_, product, _), cents in zip(lines[invoice], allocation):
                if cents:
                    products[window][product] += cents

    by_year = []
    for year, amounts in sorted(annual.items()):
        by_year.append({"year": year, "domestic": _dollars(amounts["domestic"]),
                        "international": _dollars(amounts["international"]),
                        "total": _dollars(sum(amounts.values()))})
    result = {"windows": [], "products": [], "customers": [], "annual": by_year}
    for window, _ in periods:
        total = sum(regions[window].values())
        top_cash = sum(sorted(customers[window].values(), reverse=True)[:20])
        share = (Decimal(top_cash) * 100 / total).quantize(Decimal("0.01")) if total > 0 else None
        result["windows"].append({
            "window": window,
            "domestic": _dollars(regions[window]["domestic"]),
            "international": _dollars(regions[window]["international"]),
            "total": _dollars(total),
            "top20_share_pct": share,
        })
        result["products"].extend(_top_rows(products[window], window, "product"))
        result["customers"].extend(_top_rows(customers[window], window, "customer"))
    return result
