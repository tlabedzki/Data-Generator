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


# ---------------------------------------------------------------------------------------------------------------- #
# Pack A: customer behaviour

def cohort_retention(sales):
    """Share of customers of each first-purchase month who buy again k months later, averaged over cohorts."""
    orders = sales.drop_duplicates("order_id")[["customer_id", "order_date"]]
    month = orders["order_date"].dt.to_period("M")
    first = month.groupby(orders["customer_id"]).transform("min")
    offset = (month - first).apply(lambda delta: delta.n)
    active = pd.DataFrame({"customer_id": orders["customer_id"], "cohort": first, "offset": offset}).drop_duplicates()
    sizes = active[active["offset"] == 0].groupby("cohort").size()
    counts = active.groupby(["cohort", "offset"]).size().unstack(fill_value=0)
    retention = counts.div(sizes, axis=0)
    first_year = retention.loc[retention.index < retention.index.min() + 12]
    return first_year.mean()


def calendar_month_share(month, seed=None):
    import func.calendar as cal
    import func.rng as rng
    with service.overridden_settings({"random_state": s.random_state if seed is None else seed}):
        calendar = cal.build_calendar(rng.stream("calendar"))
    return calendar.loc[calendar["month"] == month, "weight"].sum()


def check_a(data):
    sales, customers = data["sales_data"], data["customer_data"]
    retention = cohort_retention(sales[sales["signup_date"] >= pd.Timestamp(s.start_year, 1, 1)])
    check("A", "cohort retention month 1 / month 12", f"{retention[1]:.1%} / {retention[12]:.1%}",
          retention[1] >= 1.5 * retention[12])
    per_customer = sales.groupby("customer_id")["order_id"].nunique().reindex(customers["customer_id"], fill_value=0)
    ratio = per_customer.var() / per_customer.mean()
    check("A", "orders per customer: variance / mean", f"{ratio:.2f}", ratio > 2)
    revenue = sales.groupby("customer_id")["revenue_gross"].sum().sort_values(ascending=False)
    top = revenue.head(int(len(customers) * 0.1)).sum() / revenue.sum()
    check("A", "revenue share of the top 10% customers", f"{top:.0%}", top >= 0.35)
    by_segment = revenue.reindex(customers["customer_id"], fill_value=0).groupby(
        customers.set_index("customer_id")["customer_segment"]).mean()
    check("A", "revenue per customer loyal / occasional",
          f"{by_segment['loyal']:,.0f} / {by_segment['occasional']:,.0f} PLN",
          by_segment["loyal"] >= 3 * by_segment["occasional"])
    electronics = sales["category"].eq("Electronics")
    young, old = electronics[sales["age"] < 30].mean(), electronics[sales["age"] >= 55].mean()
    check("A", "Electronics share of lines, age < 30 / 55+", f"{young:.1%} / {old:.1%}", young > old)
    lines = sales.drop_duplicates("order_id")
    month_share = lines.groupby(lines["order_date"].dt.month).size() / len(lines)
    target = np.asarray(s.base_monthly_seasonality) / np.sum(s.base_monthly_seasonality)
    calendar_share = calendar_month_share(11)
    gap = (month_share[11] - calendar_share) * 100
    check("A", "November share of orders vs the calendar (no flattening)",
          f"{month_share[11]:.1%} vs {calendar_share:.1%} ({gap:+.1f} pp)", abs(gap) <= 0.5)
    seeds = [calendar_month_share(11, seed) for seed in range(10)]
    gap = (np.mean(seeds) - target[10]) * 100
    check("A", "November weight over 10 seeds vs setting (noise has no bias)",
          f"{np.mean(seeds):.1%} vs {target[10]:.1%} ({gap:+.1f} pp)", abs(gap) <= 0.5)
    yearly = lines.groupby(lines["order_date"].dt.year).size()
    growth = yearly.iloc[-1] / yearly.iloc[0] - 1
    check("A", "order growth first to last year (setting 20%/year)", f"{growth:.0%}", 0.10 <= growth <= 0.30)


PACKS = {"E": check_e, "A": check_a}


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
