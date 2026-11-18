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

import settings.main_settings as s  # noqa: E402
import settings.quality_settings as qs  # noqa: E402
from func import service  # noqa: E402

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
        multiplier = next(m for t, c, i, m in qs.data_quality_issues
                          if (t, c, i) == ("customer_data", column, "missing"))
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
    check("E", "fraud orders shipped to another postal code (some go to a locker near home)", f"{elsewhere:.0%}",
          0.6 <= elsewhere < 1)
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


# ---------------------------------------------------------------------------------------------------------------- #
# Pack D: prices, promotions, returns and logistics

def check_d(data):
    import func.calendar as cal
    orders = data["order_data"].drop_duplicates("order_id")
    per_day = orders.groupby("order_date").size()
    for year in range(s.start_year, s.end_year + 1):
        friday = cal.black_friday(year)
        november = per_day[(per_day.index.month == 11) & (per_day.index.year == year)]
        ratio = per_day.get(friday, 0) / november.mean()
        check("D", f"Black Friday {friday:%Y-%m-%d} / average November day", f"{ratio:.1f}x", ratio >= 3)
        december = per_day[(per_day.index.month == 12) & (per_day.index.year == year)]
        ratio = per_day.get(pd.Timestamp(year, 12, 25), 0) / december.mean()
        check("D", f"25 December {year} / average December day", f"{ratio:.2f}x", ratio <= 0.5)
    hours = orders["order_datetime"].dt.hour.value_counts(normalize=True).sort_index()
    peak = int(hours.idxmax())
    check("D", "busiest hour of the day", f"{peak}:00 ({hours.max():.1%} of orders)", 19 <= peak <= 22)
    lines = data["sales_data"]
    discounted = lines.loc[lines["discount_rate"] > 0, "quantity"].mean()
    full_price = lines.loc[lines["discount_rate"] == 0, "quantity"].mean()
    check("D", "units per line with / without discount", f"{discounted:.2f} / {full_price:.2f}",
          discounted >= 1.1 * full_price)
    returns = data["return_data"].merge(data["product_data"][["product_id", "category"]], on="product_id")
    rate = returns.groupby("category").size() / lines.groupby("category").size()
    check("D", "return rate Clothing / Electronics", f"{rate['Clothing']:.1%} / {rate['Electronics']:.1%}",
          rate["Clothing"] >= 3 * rate["Electronics"])
    shipments = data["shipment_data"]
    bulky_in_locker = shipments.loc[shipments["is_bulky"], "delivery_method"].isin(
        ["InPost parcel locker", "Orlen Paczka", "Allegro One", "Poczta Polska"]).mean()
    furniture = lines.loc[lines["category"] == "Furniture", "delivery_method"].eq("InPost parcel locker").mean()
    check("D", "bulky orders in lockers / furniture lines to parcel lockers",
          f"{bulky_in_locker:.1%} / {furniture:.1%} (was 55.6%)", bulky_in_locker == 0)
    products = data["product_data"].set_index("product_id")
    launch = lines["product_id"].map(products["launch_date"])
    stop = lines["product_id"].map(products["discontinued_date"])
    legit = ~lines["is_fraud"]
    outside = ((lines["order_date"] < launch) | (lines["order_date"] >= stop)) & legit
    check("D", "lines sold before launch or after discontinuation", int(outside.sum()), outside.sum() == 0)
    history = data["price_history"]
    sample = lines.sample(2000, random_state=1)
    merged = pd.merge_asof(sample.sort_values("order_date"), history.sort_values("valid_from"),
                           left_on="order_date", right_on="valid_from", by="product_id",
                           suffixes=("", "_history"))
    mismatch = (merged["unit_price_gross"] != merged["sales_price_gross_history"]).sum()
    check("D", "line price differs from price_history on the order day (2000 lines)", int(mismatch), mismatch == 0)
    changed = history.groupby("product_id").size().gt(1).mean()
    check("D", "products with at least one list price change", f"{changed:.0%}", changed >= 0.5)
    late = shipments.groupby(shipments["shipped_at"].dt.month.isin([11, 12]))["is_late"].mean()
    check("D", "late deliveries outside / in November-December", f"{late[False]:.1%} / {late[True]:.1%}",
          late[True] > late[False])


# ---------------------------------------------------------------------------------------------------------------- #
# Pack B: basket and preferences

def pair_lift(lines, first, second):
    baskets = lines.groupby("order_id")["product_type"].agg(set)
    has_first = baskets.map(lambda types: first in types)
    has_second = baskets.map(lambda types: second in types)
    both = (has_first & has_second).mean()
    return both / (has_first.mean() * has_second.mean()), int((has_first & has_second).sum())


def check_b(data):
    lines = data["sales_data"][~data["sales_data"]["is_fraud"]]
    for first, second in [("Laptop", "Wireless Mouse"), ("Smartphone", "Headphones"), ("Office Desk", "Office Chair")]:
        lift, together = pair_lift(lines, first, second)
        check("B", f"lift {first} + {second}", f"{lift:.1f} ({together} orders)", lift > 3)
    lift, together = pair_lift(lines, "Cat Food", "Pet Litter")
    check("B", "lift Cat Food + Pet Litter (litter is bought by cat owners anyway)", f"{lift:.1f} ({together} orders)",
          lift > 1.5)
    orders = lines.sort_values("order_datetime").groupby("order_id").agg(
        customer=("customer_id", "first"), category=("category", "first"))
    previous = orders.groupby("customer")["category"].shift()
    repeat = orders[previous.notna()]
    same = (repeat["category"] == previous[previous.notna()]).mean()
    share = orders["category"].value_counts(normalize=True)
    random_same = (share ** 2).sum()
    check("B", "same first category as the previous order / at random", f"{same:.1%} / {random_same:.1%}",
          same >= random_same + 0.10)
    pet = lines[lines["product_type"].isin(["Dog Food", "Cat Food"])].drop_duplicates(["order_id", "product_id"])
    pet = pet.sort_values("order_date")
    gaps = pet.groupby(["customer_id", "product_id"])["order_date"].diff().dt.days.dropna()
    check("B", "median days between repeat purchases of the same pet food",
          f"{gaps.median():.0f} ({len(gaps)} repeats)",
          25 <= gaps.median() <= 45)
    tier_price = lines.groupby("price_tier")["unit_price_gross"].median()
    check("B", "median unit price premium / budget customers",
          f"{tier_price['premium']:.0f} / {tier_price['budget']:.0f} PLN",
          tier_price["premium"] >= 1.5 * tier_price["budget"])
    favourite = (lines["category"] == lines["preferred_category"]).mean()
    check("B", "lines from the customer's preferred category", f"{favourite:.0%}", favourite >= 0.35)


# ---------------------------------------------------------------------------------------------------------------- #
# Pack C: marketing and traffic

def check_c(data):
    import settings.marketing_settings as mk
    orders = data["order_data"].drop_duplicates("order_id")
    sessions = data["session_data"]
    converting = sessions.dropna(subset=["order_id"])
    covered = orders["order_id"].isin(converting["order_id"]).mean()
    check("C", "orders with a converting session", f"{covered:.1%} ({len(sessions):,} sessions)",
          covered == 1 and converting["order_id"].is_unique)
    worst = 0.0
    for (channel, device), group in sessions.groupby(["channel", "device"]):
        expected = mk.channel_conversion_rates[channel] * mk.device_conversion_multipliers[device]
        measured = group["order_id"].notna().mean()
        if len(group) > 2000:
            worst = max(worst, abs(measured / expected - 1))
    email = sessions[sessions["channel"] == "email"]["order_id"].notna().mean()
    check("C", "largest relative gap of conversion vs setting (channel x device)",
          f"{worst:.1%} (email {email:.1%})", worst <= 0.10)
    mobile = (sessions["device"] == "mobile").mean()
    check("C", "mobile share of sessions", f"{mobile:.1%} vs {mk.device_shares['mobile']:.0%}",
          abs(mobile - mk.device_shares["mobile"]) <= 0.02)
    campaigns = data["campaign_data"]
    social = campaigns[campaigns["channel"] == "social"]
    days = pd.Series(False, index=pd.date_range(f"{s.start_year}-01-01", f"{s.end_year}-12-31"))
    for row in social.itertuples():
        days[row.start_date:row.end_date] = True
    per_day = orders[orders["channel"] == "social"].groupby("order_date").size().reindex(days.index, fill_value=0)
    total = orders.groupby("order_date").size().reindex(days.index, fill_value=0)
    ratio = (per_day[days] / total[days]).mean() / (per_day[~days] / total[~days]).mean()
    check("C", "social share of orders on social campaign days / other days", f"{ratio:.2f}x", ratio >= 1.3)
    revenue = data["sales_data"].groupby("campaign_id")["revenue_gross"].sum()
    attributed = revenue.reindex(campaigns["campaign_id"]).fillna(0).groupby(campaigns["channel"].to_numpy()).sum()
    roas = attributed / campaigns.groupby("channel")["total_cost"].sum()
    check("C", "ROAS by channel (attributed revenue / cost)", ", ".join(f"{k} {v:.1f}" for k, v in roas.items()),
          bool((roas > 1).all()))
    cost_per_order = campaigns["total_cost"].sum() / len(orders)
    check("C", "marketing cost per order", f"{cost_per_order:.0f} PLN vs {mk.marketing_budget_per_order:.0f}",
          abs(cost_per_order / mk.marketing_budget_per_order - 1) <= 0.1)
    cart = sessions.loc[sessions["order_id"].isna(), "added_to_cart"].mean()
    check("C", "carts abandoned (sessions with a cart and no order / all carts)",
          f"{(sessions['added_to_cart'] & sessions['order_id'].isna()).sum() / sessions['added_to_cart'].sum():.0%}",
          cart > 0)


# ---------------------------------------------------------------------------------------------------------------- #
# Pack F: A/B experiments

def check_f(data):
    import math
    experiments = data["experiment_data"]
    assignments = data["experiment_assignment_data"]
    sessions = data["session_data"].set_index("session_id")
    lines = data["order_data"]
    for row in experiments.itertuples():
        units = assignments[assignments["experiment_id"] == row.experiment_id]
        counts = units["variant"].value_counts()
        expected = np.array([1 - row.planned_split_b, row.planned_split_b]) * counts.sum()
        observed = np.array([counts.get("A", 0), counts.get("B", 0)])
        chi2 = float(((observed - expected) ** 2 / expected).sum())
        p_value = math.erfc(math.sqrt(chi2 / 2))  # chi-square with one degree of freedom
        srm_ok = p_value < 0.001 if row.has_sample_ratio_mismatch else p_value > 0.05
        check("F", f"{row.experiment_name}: sample ratio test p-value "
                   f"(mismatch planted: {row.has_sample_ratio_mismatch})",
              f"{p_value:.2g} (B {counts.get('B', 0) / counts.sum():.1%})", srm_ok)
        if row.metric == "conversion_rate":
            converted = sessions.loc[units["unit_id"], "order_id"].notna().to_numpy()
            b = units["variant"].to_numpy() == "B"
            pa, pb = converted[~b].mean(), converted[b].mean()
            se = np.sqrt((1 - pa) / (pa * (~b).sum()) + (1 - pb) / (pb * b.sum()))
            low, high = np.exp(np.log(pb / pa) + np.array([-1.96, 1.96]) * se) - 1
            check("F", f"{row.experiment_name}: conversion lift, 95% CI (true {row.true_effect:+.0%})",
                  f"{pb / pa - 1:+.1%} [{low:+.1%}, {high:+.1%}]", low <= row.true_effect <= high)
        else:
            variant = units.set_index("unit_id")["variant"]
            window = sessions[(sessions["session_start"].dt.normalize() >= row.start_date)
                              & (sessions["session_start"].dt.normalize() <= row.end_date)].dropna(subset=["order_id"])
            in_test = lines[lines["order_id"].isin(window["order_id"].astype(int))
                            & lines["customer_id"].isin(variant.index)]
            group = in_test["customer_id"].map(variant)
            qa, qb = in_test.loc[group == "A", "quantity"], in_test.loc[group == "B", "quantity"]
            diff = qb.mean() - qa.mean()
            se = np.sqrt(qa.var() / len(qa) + qb.var() / len(qb))
            check("F", f"{row.experiment_name}: units per line B - A, 95% CI (true {row.true_effect:+.2f})",
                  f"{diff:+.3f} [{diff - 1.96 * se:+.3f}, {diff + 1.96 * se:+.3f}]",
                  diff - 1.96 * se <= row.true_effect <= diff + 1.96 * se)


PACKS = {"E": check_e, "A": check_a, "D": check_d, "B": check_b, "C": check_c, "F": check_f}


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
