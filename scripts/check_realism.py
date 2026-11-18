"""
Check the realism criteria of the generated data on the default command-line volume (seed 42).

Usage (from the repository root):
    python scripts/check_realism.py            # all packs
    python scripts/check_realism.py E A        # selected packs

Each criterion prints PASS or FAIL with the measured number. The exit code is 1 when any criterion fails.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import func.log as l  # noqa: E402
from func import service  # noqa: E402
import settings.main_settings as s  # noqa: E402
import settings.quality_settings as qs  # noqa: E402

for name in ("log_info", "log_success", "log_section", "log_metric"):
    setattr(l, name, lambda *args, **kwargs: None)

RESULTS = []


def check(pack, label, value, passed):
    RESULTS.append(passed)
    print(f"  [{'PASS' if passed else 'FAIL'}] {pack} {label}: {value}")


def generate(**changes):
    params = service.GenerationParams(customers=s.customer_data_rows, products=s.product_data_rows,
                                      order_lines=s.order_data_rows, **changes)
    started = time.perf_counter()
    data = service.generate(params)
    print(f"  generated {params.data_quality_level!r} data in {time.perf_counter() - started:.1f} s")
    return data


# ---------------------------------------------------------------------------------------------------------------- #
# Pack E: dirty data and anomalies

def check_e(data):
    dirty = generate(data_quality_level="medium")
    customers = dirty["customer_data"]
    issues = dirty["quality_issue_data"]
    base_rows = s.customer_data_rows
    rate = qs.data_quality_rates["medium"]
    for column in ("phone_number", "city", "age"):
        multiplier = next(m for t, c, i, m in qs.data_quality_issues if (t, c, i) == ("customer_data", column, "missing"))
        expected = rate * multiplier * base_rows
        missing = int(customers[column].isna().sum())
        check("E", f"missing {column} at medium (expected {expected:.0f})", missing,
              abs(missing - expected) <= 0.2 * expected)
    duplicates = int((issues["issue_type"] == "duplicate_customer").sum())
    check("E", "duplicate customers at medium (expected 3% of customers)", duplicates,
          duplicates == round(rate * base_rows))
    clean_missing = int(data["customer_data"].isna().sum().sum())
    check("E", "missing values at none / issues listed", f"{clean_missing} / {len(data['quality_issue_data'])}",
          clean_missing == 0 and data["quality_issue_data"].empty)

    sales = data["sales_data"]
    orders = sales.groupby("order_id").agg(value=("revenue_gross", "sum"), fraud=("is_fraud", "first"),
                                           home=("postal_code", "first"), ship=("shipping_postal_code", "first"))
    fraud, legit = orders[orders["fraud"]], orders[~orders["fraud"]]
    ratio = fraud["value"].mean() / legit["value"].mean()
    check("E", "fraud order value / other orders", f"{ratio:.1f}x ({len(fraud)} fraud orders)", ratio >= 3)
    elsewhere = (fraud["ship"] != fraud["home"]).mean()
    check("E", "fraud orders shipped to another postal code", f"{elsewhere:.0%}", elsewhere >= 0.9)
    per_day = data["order_data"].drop_duplicates("order_id").groupby("order_date").size()
    for day in data["anomaly_data"].query("anomaly_type == 'shop_outage'")["start_date"]:
        share = per_day.get(day, 0) / per_day.median()
        check("E", f"orders on outage day {day:%Y-%m-%d} vs median day", f"{share:.0%}", share <= 0.10)


PACKS = {"E": check_e}


def main(selected):
    selected = [pack.upper() for pack in selected] or list(PACKS)
    data = generate()
    for pack in selected:
        print(f"Pack {pack}")
        PACKS[pack](data)
    print(f"{sum(RESULTS)} of {len(RESULTS)} criteria passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
