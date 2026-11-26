# Industrial Operations Analytics

An offline Python project that answers two questions about an industrial order book. Which orders missed a customer's requested date or a supplier's promise? How much cash came in for each product, and which buyers accounted for it?

The repository includes an HTML dashboard, six CSV reports, and a deterministic generator for five related input tables. All example customers, identifiers, transactions and amounts are fictional. Python 3.10 or later is sufficient. The project uses only the standard library.

[Open the sample dashboard](https://gavcun-bot.github.io/industrial-operations-analytics/)

## Run the demo

From the repository root, run these commands. Use `python3` if that is the Python executable on your system.

```sh
python -m analytics demo
python -m unittest discover -s tests -v
```

Open `build/reports/index.html` in a browser. The dashboard works offline. The same synthetic report is checked in at [docs/index.html](docs/index.html). Input tables are written to `build/data/`. Running the demo again regenerates the five input files and the reports at the selected output location.

To analyze the generated inputs at a different cutoff, run the following command.

```sh
python -m analytics report --input build/data --out build/midyear --as-of 2025-06-30
```

## Read the sample

At the default December 31, 2025 cutoff, 426 orders had at least one promise due. Of those, 246 had a late shipment and two still had overdue units. In this sample those groups did not overlap, so 248 unique orders missed a promise. The exception export identifies the affected lines and units. An order can appear in both groups when part of a line ships late and the balance stays open.

Applied receipts in the last 12 months totaled $192,912.70. The domestic and international portions were $100,236.50 and $92,676.20. Switch the cutoff to see how delivery and cash figures change as later shipments and receipts enter the calculation.

## How the metrics work

**Delivery performance.** Each order line has a requested and a promised ship date. The analyzer counts eligible orders once per target if at least one line is due by the cutoff. A shipment after the target is late. An outstanding quantity becomes overdue the day after its target. The delayed count is the union of the late-shipment and open-overdue sets. The rate uses orders due against that specific target as its denominator. The report excludes orders placed after the cutoff, cancelled orders and future shipments. The input represents one snapshot of status and target dates. Historical analyses use the dates in that snapshot and cannot reconstruct edits to a promise or cancellation status.

**Cash allocation.** A receipt applies to an invoice. To attribute it to products, the analyzer allocates the signed amount across lines in proportion to net line value. It works in integer cents and distributes residual cents by largest remainder, resolving ties by line ID. A negative receipt represents a refund. For example, a $10.00 payment on two equally weighted lines allocates $5.00 to each. A $0.01 refund on the same lines goes to the first line by ID. The period total represents applied cash after refunds.

**Time windows and concentration.** Receipt dates determine inclusion. The 12-month and five-year periods exclude their starting anniversary and include the cutoff. All-history totals include every receipt through the cutoff. Calendar-year totals use that same cutoff, so the final year can be partial. Domestic and international groups use bill-to region. Each period ranks up to 20 customers and products by net cash. The top-20 buyer share divides the leading customers' net cash by total net cash and is blank when the denominator is nonpositive.

## Input tables

| CSV | Grain and fields |
| --- | --- |
| `orders.csv` | One row per `order_id` with `placed_date`, `customer`, `region` and `status` (`active` or `cancelled`). |
| `lines.csv` | One row per order and line, with `order_id`, `line_id`, `product`, `quantity`, `requested_date` and `promised_date`. |
| `shipments.csv` | One movement per row with `order_id`, `line_id`, `quantity` and `shipped_date`. Split shipments are supported. |
| `invoice_lines.csv` | One row per invoice and line with `invoice_id`, `line_id`, `product`, `net_cents`, `customer`, `region` and `invoice_date`. Lines must agree on invoice header fields. |
| `receipts.csv` | One application per `receipt_id` and `invoice_id` pair with signed `amount_cents` and `receipt_date`. |

Dates use YYYY-MM-DD. Monetary inputs use USD cents. Invoice line weights are nonnegative integers and an invoice receiving a nonzero application must have a positive total. The cash analysis accepts `domestic` and `international` bill-to regions. An order can have a different number of shipped and billed lines at the cutoff.

## Exports

`shipping_summary.csv` contains the two due-order populations and the corresponding late, open and overlapping counts. `shipping_exceptions.csv` contains one row per affected line and target with the overdue balance and late-shipped quantity.

`cash_by_period.csv` and `cash_by_year.csv` contain regional cash totals. `cash_by_product.csv` and `cash_by_customer.csv` contain the period rankings. Currency outputs use decimal USD.
