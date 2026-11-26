"""Render offline HTML and machine-readable CSV reports."""

import csv
from html import escape


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def table(headers, rows, numeric=()):
    head = "".join(f'<th scope="col">{escape(header)}</th>' for header in headers)
    body = []
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            align = ' class="num"' if index in numeric else ''
            cells.append(f'<td{align}>{escape(str(cell))}</td>')
        body.append('<tr>' + ''.join(cells) + '</tr>')
    if not body:
        body.append(f'<tr><td colspan="{len(headers)}">No matching records</td></tr>')
    return '<div class="scroll"><table><thead><tr>' + head + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'


def money(value):
    return f"${value:,.2f}"


def percent(value):
    return f"{value:.1f}%" if value is not None else "—"


def render_html(cutoff, shipping, exceptions, cash, *, demo=False):
    source_label = "<p><b>Synthetic ERP data</b></p>" if demo else ""
    ship = table(["Target", "Orders due", "Shipped late", "Open overdue", "Both", "Delayed", "Delayed / due"],
                 [[r["basis"].title(), r["due_orders"], r["shipped_late_orders"], r["open_overdue_orders"],
                   r["both"], r["delayed_orders"], percent(r["delayed_pct"])] for r in shipping], range(1, 7))
    periods = table(["Window", "Domestic", "International", "Net cash", "Top 20 buyers"],
                    [[r["window"], money(r["domestic"]), money(r["international"]), money(r["total"]),
                      percent(r["top20_share_pct"])] for r in cash["windows"]], range(1, 5))
    years = table(["Year", "Domestic", "International", "Net cash"],
                  [[r["year"], money(r["domestic"]), money(r["international"]), money(r["total"])]
                   for r in cash["annual"]], range(1, 4))
    latest = cash["windows"][0]
    panels = []
    for title, group, key in [("Leading products", "products", "product"), ("Leading buyers", "customers", "customer")]:
        rows = [r for r in cash[group] if r["window"] == latest["window"]][:5]
        panels.append('<section><h3>' + title + '</h3>' + table(
            ["Rank", key.title(), "Net cash"], [[r["rank"], r[key], money(r["amount"])] for r in rows], (0, 2)) + '</section>')
    queue = [r for r in exceptions if r["basis"] == "promised" and r["open_overdue"]][:8]
    review = table(["Order", "Product", "Promise", "Units overdue", "Days overdue"],
                   [[r["order"], r["product"], r["target"], r["open_overdue"], r["days_overdue"]] for r in queue], (3, 4))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Industrial Operations Analytics</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f5f1;color:#182e30;font:16px/1.5 system-ui,sans-serif}}
header{{background:#123a3a;color:#fff;padding:38px max(6vw,20px) 34px}}h1{{font-size:clamp(2rem,5vw,3.8rem);letter-spacing:-.055em;line-height:1.06;margin:6px 0 10px}}
header p{{margin:0;color:#d8ebe4}}main{{max-width:1160px;margin:auto;padding:20px clamp(15px,4vw,50px) 55px}}
h2{{font-size:1.65rem;line-height:1.15;letter-spacing:-.04em;margin:1.65em 0 .3em}}h3{{font-size:1.15rem;margin:1.1em 0 .35em}}
p{{margin:.5em 0 1em}}.kpis,.pair{{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(225px,1fr))}}
.kpis article{{border-top:3px solid #287b65;padding:12px 16px 14px;background:white}}small{{display:block;color:#405659}}
strong{{display:block;font-size:clamp(1.35rem,3.5vw,2rem);line-height:1.25;letter-spacing:-.045em}}
.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:white;font-size:.9rem}}
th,td{{text-align:left;padding:9px 11px;border-bottom:1px solid #dae1df}}th{{background:#e5eeea;color:#234742}}
.num{{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}}footer{{margin-top:2rem;font-size:.85rem;color:#405659}}
@media print{{body{{background:white}}header{{background:white;color:black}}header p{{color:black}}.scroll{{overflow:visible}}}}
</style></head><body><header>{source_label}<h1>Industrial Operations Analytics</h1><p>Order fulfillment and applied customer cash · Through {cutoff.isoformat()}</p></header>
<main><div class="kpis">
<article><small>Active orders in scope</small><strong>{shipping[0]['active_orders']:,}</strong></article>
<article><small>Orders delayed against promise</small><strong>{percent(shipping[1]['delayed_pct'])}</strong></article>
<article><small>Applied cash · last 12 months</small><strong>{money(latest['total'])}</strong></article></div>
<h2>Shipping performance</h2><p>Each order counts once per target. “Both” identifies overlap between late shipments and overdue open quantities.</p>{ship}
<h2>Open promise exceptions</h2><p>Up to eight overdue lines, longest outstanding first.</p>{review}
<h2>Customer payments</h2><p>Receipts and refunds allocated to invoice lines, grouped by receipt date and bill-to region. All amounts in USD.</p>{periods}
<div class="pair">{''.join(panels)}</div>
<h3>Annual collections</h3><p>Calendar years with recorded receipts, through the reporting cutoff.</p>{years}<footer>Rankings show net cash over the last 12 months. The CSV exports include up to 20 buyers and products in each window.</footer>
</main></body></html>
"""


def write_reports(directory, cutoff, shipping, exceptions, cash, *, demo=False):
    directory.mkdir(parents=True, exist_ok=True)
    write_csv(directory / "shipping_summary.csv", list(shipping[0]), shipping)
    write_csv(directory / "shipping_exceptions.csv",
              ["basis", "order", "line", "product", "customer", "target", "ordered",
               "shipped_late", "open_overdue", "days_overdue"], exceptions)
    write_csv(directory / "cash_by_period.csv", list(cash["windows"][0]), cash["windows"])
    write_csv(directory / "cash_by_year.csv", ["year", "domestic", "international", "total"], cash["annual"])
    write_csv(directory / "cash_by_product.csv", ["window", "product", "amount", "rank"], cash["products"])
    write_csv(directory / "cash_by_customer.csv", ["window", "customer", "amount", "rank"], cash["customers"])
    (directory / "index.html").write_text(render_html(cutoff, shipping, exceptions, cash, demo=demo), encoding="utf-8")
