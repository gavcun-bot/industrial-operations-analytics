"""Generate synthetic tables or analyze a specified snapshot."""

import argparse
import csv
from datetime import date
from pathlib import Path

from .cash import cash_report
from .demo import SCHEMAS, generate
from .report import write_reports
from .shipping import shipping_report


def load(directory, name):
    with (directory / f"{name}.csv").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(SCHEMAS[name]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{name}.csv is missing columns: {', '.join(sorted(missing))}")
        return list(reader)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="create deterministic synthetic data and analyze it")
    report = commands.add_parser("report", help="analyze five CSV tables")
    demo.add_argument("--out", type=Path, default=Path("build"))
    report.add_argument("--input", type=Path, required=True)
    report.add_argument("--out", type=Path, required=True)
    for command in [demo, report]:
        command.add_argument("--as-of", type=date.fromisoformat, default=date(2025, 12, 31), metavar="YYYY-MM-DD")
    args = parser.parse_args()
    try:
        if args.command == "demo":
            source, destination = args.out / "data", args.out / "reports"
            generate(source)
        else:
            source, destination = args.input, args.out
        shipping, exceptions = shipping_report(load(source, "orders"), load(source, "lines"),
                                               load(source, "shipments"), args.as_of)
        cash = cash_report(load(source, "invoice_lines"), load(source, "receipts"), args.as_of)
        write_reports(destination, args.as_of, shipping, exceptions, cash, demo=args.command == "demo")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Analysis failed: {error}\n")
    print(f"Report: {destination / 'index.html'}")


if __name__ == "__main__":
    main()
