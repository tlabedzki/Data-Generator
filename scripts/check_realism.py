"""
Check the realism criteria of the generated data on the default command-line volume (seed 42).

Usage (from the repository root):
    python scripts/check_realism.py            # all packs
    python scripts/check_realism.py E A        # selected packs (E A D B C F G H I J)

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
from func import calendar, service  # noqa: E402

RESULTS = []


def realised(lines):
    """Lines of orders that were paid and shipped: cancelled and failed orders bring no revenue."""
    return lines[~lines["order_status"].isin(["cancelled", "payment_failed"])]


def check(pack, label, value, passed):
    RESULTS.append(passed)
    print(f"  [{'PASS' if passed else 'FAIL'}] {pack} {label}: {value}")


def generate(**changes):
    volume = {"customers": s.customer_data_rows, "products": s.product_data_rows, "order_lines": s.order_data_rows}
    params = service.GenerationParams(**{**volume, **changes})
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
    revenue = realised(sales).groupby("customer_id")["revenue_gross"].sum().sort_values(ascending=False)
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
    rate = returns.groupby("category").size() / realised(lines).groupby("category").size()
    check("D", "return rate Clothing / Electronics (shipped lines)",
          f"{rate['Clothing']:.1%} / {rate['Electronics']:.1%}", rate["Clothing"] >= 3 * rate["Electronics"])
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
    revenue = realised(data["sales_data"]).groupby("campaign_id")["revenue_gross"].sum()
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


# ---------------------------------------------------------------------------------------------------------------- #
# Pack G: order status, reviews and churn truth

EXPECTED_PAYMENT = {"delivered": {"paid"}, "returned": {"refunded"}, "payment_failed": {"failed"},
                    "cancelled": {"refunded", "unpaid"}}


def check_g(data):
    import settings.commerce_settings as cs
    import settings.quality_settings as qs
    lines, shipments, returns, reviews = (data["order_data"], data["shipment_data"], data["return_data"],
                                          data["review_data"])
    orders = lines.drop_duplicates("order_id").set_index("order_id")

    failed = orders.groupby("payment_method")["order_status"].apply(lambda status: (status == "payment_failed").mean())
    check("G", "failed payments, deferred payment / BLIK (setting 10% / 1.2%)",
          f"{failed['Deferred payment']:.1%} / {failed['BLIK']:.1%}", failed["Deferred payment"] >= 3 * failed["BLIK"])
    lost = orders["order_status"].isin(["cancelled", "payment_failed"])
    check("G", "orders cancelled or with a failed payment (settings give about 5%)", f"{lost.mean():.1%}",
          0.03 <= lost.mean() <= 0.08)
    lost_ids = orders.index[lost]
    leaks = int(shipments["order_id"].isin(lost_ids).sum() + returns["order_id"].isin(lost_ids).sum()
                + reviews["order_id"].isin(lost_ids).sum())
    check("G", "cancelled or failed orders with a shipment, return or review", leaks, leaks == 0)
    cancelled = orders[orders["order_status"] == "cancelled"]
    wrong = sum(int((~orders.loc[orders["order_status"] == status, "payment_status"].isin(allowed)).sum())
                for status, allowed in EXPECTED_PAYMENT.items())
    wrong += int((cancelled["cancelled_at"] <= cancelled["order_datetime"]).sum()
                 + cancelled["cancel_reason"].isna().sum()
                 + orders.loc[orders["order_status"] != "cancelled", "cancelled_at"].notna().sum())
    check("G", "payment status, cancel time or reason that contradicts the order status", wrong, wrong == 0)
    refunded = returns[returns["return_status"] == "refunded"].set_index("order_line_id")["returned_quantity"]
    full = lines["order_line_id"].map(refunded).fillna(0).to_numpy() >= lines["quantity"].to_numpy()
    all_back = pd.Series(full).groupby(lines["order_id"].to_numpy()).all()
    shipped = orders.index[orders["order_status"].isin(["delivered", "returned"])]
    expected_returned = set(all_back[all_back].index) & set(shipped)
    actual_returned = set(orders.index[orders["order_status"] == "returned"])
    check("G", "returned orders / shipped orders refunded in full, line by line",
          f"{len(actual_returned)} / {len(expected_returned)}", actual_returned == expected_returned)
    peak = cancelled["order_date"].dt.month.isin(cs.peak_months)
    stock = cancelled.groupby(peak)["cancel_reason"].apply(lambda reason: (reason == "out_of_stock").mean())
    check("G", "out_of_stock share of cancellations, November-December / other months",
          f"{stock[True]:.0%} / {stock[False]:.0%}", stock[True] >= 1.5 * stock[False])

    reached = lines[lines["order_id"].isin(shipments["order_id"]) & ~lines["is_fraud"]]
    late = reached["order_id"].map(shipments.set_index("order_id")["is_late"]).to_numpy(dtype=bool)
    defect = reached["order_line_id"].isin(
        returns.loc[returns["return_reason"].isin(cs.defect_return_reasons), "order_line_id"]).to_numpy()
    experience = pd.Series(np.where(defect, "defect", np.where(late, "late", "on_time")),
                           index=reached["order_line_id"].to_numpy())
    rated = reviews.assign(experience=reviews["order_line_id"].map(experience))
    mean = rated.groupby("experience")["review_score"].mean()
    check("G", "average rating on time / late / returned as defective or damaged",
          f"{mean['on_time']:.2f} / {mean['late']:.2f} / {mean['defect']:.2f}",
          mean["on_time"] - mean["late"] >= 0.5 and mean["late"] - mean["defect"] >= 0.5)
    share = rated.groupby("experience").size() / experience.value_counts()
    check("G", "lines reviewed, late / on time (bad experiences get more reviews)",
          f"{share['late']:.0%} / {share['on_time']:.0%}", share["late"] >= 1.3 * share["on_time"])
    delivered = reviews["order_id"].map(shipments.set_index("order_id")["delivered_at"]).dt.normalize()
    early = int((reviews["review_date"] <= delivered).sum() + delivered.isna().sum())
    check("G", "reviews dated on or before delivery, or of lines never delivered", early, early == 0)
    stars = reviews["review_score"].value_counts(normalize=True)
    check("G", "ratings with 5 / 1 / 2 stars (J-shaped, as in real shops)",
          f"{stars[5]:.0%} / {stars[1]:.0%} / {stars[2]:.0%}", stars.idxmax() == 5 and stars[1] > stars[2])

    customers = data["customer_data"].set_index("customer_id")
    legit = orders[~orders["is_fraud"]]
    after = (legit["order_date"] - legit["customer_id"].map(customers["true_churn_date"])).dt.days
    beyond = int((after > qs.outage_recovery_days).sum())
    check("G", f"orders more than {qs.outage_recovery_days} days after true_churn_date (outages move orders "
               f"by up to {qs.outage_recovery_days} days)", f"{beyond} ({int((after > 0).sum())} moved by an outage)",
          beyond == 0)
    start, end = pd.Timestamp(s.start_year, 1, 1), pd.Timestamp(s.end_year, 12, 31)
    first = legit.groupby("customer_id")["order_date"].min().reindex(customers.index)
    count = legit.groupby("customer_id").size().reindex(customers.index, fill_value=0)
    existing = customers["signup_date"] < start
    window_start = first.where(~existing, start)
    window_end = customers["true_churn_date"].clip(upper=end)
    years = ((window_end - window_start).dt.days.clip(lower=0) + existing.astype(int)) / 365
    repeats = (count - (~existing).astype(int)).clip(lower=0)
    active = existing | first.notna()
    ratio = repeats[active].sum() / (customers["true_purchase_rate"] * years)[active].sum()
    check("G", "repeat orders in the period / true_purchase_rate x active years", f"{ratio:.3f}",
          abs(ratio - 1) <= 0.05)
    last = legit.groupby("customer_id")["order_date"].max().reindex(customers.index)
    churned = customers["true_churn_date"] <= end
    silent = last.notna() & (last < end - pd.Timedelta(days=180))
    recent = last.notna() & ~silent
    check("G", "churned by the end: buyers silent for the last 180 days / recent buyers",
          f"{churned[silent].mean():.0%} / {churned[recent].mean():.0%}",
          churned[silent].mean() >= 2 * churned[recent].mean())


# ---------------------------------------------------------------------------------------------------------------- #
# Pack H: competitor prices

def check_h(data):
    import settings.market_settings as ms
    offers, products, history = data["competitor_prices"], data["product_data"], data["price_history"]
    end = pd.Timestamp(s.end_year, 12, 31)
    current = offers[(offers["valid_from"] <= end) & (offers["valid_to"].isna() | (offers["valid_to"] >= end))]
    regular = current[~current["is_promotion"]]
    level = (regular["price_gross"] / regular["true_market_price_gross"]).groupby(regular["competitor_name"]).mean()
    truth = current.groupby("competitor_name")["true_price_level"].first()
    names = [shop["name"] for shop in ms.competitor_settings.values()]
    check("H", "five shops with different names and strategies",
          " / ".join(f"{shop['name']} {shop['strategy']}" for shop in ms.competitor_settings.values()),
          len(ms.competitor_settings) == 5 and offers["competitor_name"].nunique() == 5
          and len({shop["strategy"] for shop in ms.competitor_settings.values()}) == 5)
    check("H", "regular price level to the market price on the last day, " + " / ".join(names) + " (true_price_level "
               + " / ".join(f"{truth[name]:.2f}" for name in names) + ")",
          " / ".join(f"{level[name]:.3f}" for name in names), ((level - truth).abs() <= 0.02).all())
    coverage = offers.groupby("competitor_name")["product_id"].nunique() / len(products)
    check("H", "products each shop sells (settings " + " / ".join(f"{shop['coverage']:.0%}" for shop in
                                                                     ms.competitor_settings.values()) + ")",
          " / ".join(f"{coverage[name]:.0%}" for name in names),
          all(abs(coverage[shop["name"]] - shop["coverage"]) <= 0.03 for shop in ms.competitor_settings.values()))
    median = current.groupby("product_id")["price_gross"].median()
    index = (products.set_index("product_id")["sales_price_gross"] / median).dropna()
    check("H", "our price / median competitor price between 0.8 and 1.25; below 0.95 / above 1.05",
          f"{index.between(0.8, 1.25).mean():.0%}; {(index < 0.95).mean():.0%} / {(index > 1.05).mean():.0%}",
          index.between(0.8, 1.25).mean() >= 0.85 and min((index < 0.95).mean(), (index > 1.05).mean()) >= 0.15)
    offer = offers.groupby(["product_id", "competitor_id"])
    gaps = int(((offers["valid_from"] - offer["valid_to"].shift()).dt.days.dropna() != 1).sum())
    check("H", "competitor price periods with a gap or an overlap", gaps, gaps == 0)
    matcher = next(shop for shop in ms.competitor_settings.values() if "reaction_probability" in shop)
    low, high = matcher["reaction_delay_days"]
    changes = offers[(offers["competitor_name"] == matcher["name"]) & (offers["change_type"] != "initial")]
    ours = history.loc[history["change_type"] != "initial", ["product_id", "valid_from"]]
    pairs = changes.merge(ours, on="product_id", suffixes=("", "_ours"))
    delay = (pairs["valid_from"] - pairs["valid_from_ours"]).dt.days
    followed = pairs.loc[delay.between(low, high), "competitor_price_id"].nunique()
    check("H", f"{matcher['name']} price changes made {low}-{high} days after one of ours",
          f"{followed / len(changes):.0%}", followed == len(changes))

    flash = next(shop for shop in ms.competitor_settings.values() if "sale_events_per_year" in shop)
    mine = offers[offers["competitor_name"] == flash["name"]]
    sale = mine["is_promotion"]
    other_sales = int(offers.loc[offers["is_promotion"], "competitor_name"].ne(flash["name"]).sum())
    check("H", f"sale prices outside {flash['name']}", other_sales, other_sales == 0)
    before = mine.groupby("product_id")["price_gross"].shift(1)
    after = mine.groupby("product_id")["price_gross"].shift(-1)
    priced = sale & (before >= 50)
    discount = 1 - mine.loc[priced, "price_gross"] / before[priced]
    low, high = min(flash["sale_discounts"]), max(flash["sale_discounts"])
    check("H", f"{flash['name']} sale discount to the price before, from 50 PLN (settings {low:.0%}-{high:.0%}): "
               "min / mean / max", f"{discount.min():.1%} / {discount.mean():.1%} / {discount.max():.1%}",
          discount.between(low - 0.02, high + 0.02).all())
    ended = sale & mine["valid_to"].notna() & after.notna()
    days = (mine.loc[ended, "valid_to"] - mine.loc[ended, "valid_from"]).dt.days + 1
    back = (after[ended] == before[ended]).mean()
    check("H", f"{flash['name']} sales {flash['sale_days'][0]}-{flash['sale_days'][1]} days long; back to the price "
               "before", f"{days.min()}-{days.max()} days; {back:.0%}",
          days.between(*flash["sale_days"]).all() and back >= 0.9)
    days_on_sale = (mine["valid_to"].fillna(end) - mine["valid_from"]).dt.days + 1
    share = days_on_sale[sale].sum() / days_on_sale.sum()
    friday = calendar.black_friday(s.end_year)
    on_friday = mine[(mine["valid_from"] <= friday) & (mine["valid_to"].isna() | (mine["valid_to"] >= friday))]
    whole = mine["price_gross"] / mine["true_market_price_gross"]
    average = (whole * days_on_sale).sum() / days_on_sale.sum()
    check("H", f"{flash['name']} offer-days on sale; offers on sale on Black Friday {s.end_year}; average level "
               "with sales", f"{share:.1%}; {on_friday['is_promotion'].mean():.0%}; {average:.3f}",
          0.02 <= share <= 0.10 and abs(on_friday["is_promotion"].mean() - flash["black_friday_share"]) <= 0.1
          and abs(average - 1) <= 0.02)


def check_i(data):
    import settings.commerce_settings as cs
    import settings.market_settings as ms
    lines, shipments, returns = data["order_data"], data["shipment_data"], data["return_data"]
    payments = data["payment_data"]
    shipped = realised(lines)
    net = (shipped["quantity"] * shipped["unit_price_gross"] * (1 - shipped["discount_rate"])).sum() / (1 + ms.vat_rate)
    free = shipments["shipping_cost"] == 0
    check("I", "free shipments that still cost the shop; carrier cost per shipment, free / paid by the customer",
          f"{(shipments.loc[free, 'carrier_cost'] > 0).mean():.0%}; {shipments.loc[free, 'carrier_cost'].mean():.2f} / "
          f"{shipments.loc[~free, 'carrier_cost'].mean():.2f} PLN",
          (shipments.loc[free, "carrier_cost"] > 0).all())
    bulky = shipments.groupby("is_bulky")["carrier_cost"].mean()
    check("I", "carrier cost of a bulky shipment / any other", f"{bulky[True] / bulky[False]:.1f}",
          bulky[True] / bulky[False] >= 4)
    refunded = returns[returns["return_status"] == "refunded"].groupby("return_reason")[
        ["written_off_quantity", "returned_quantity"]].sum()
    share = refunded["written_off_quantity"] / refunded["returned_quantity"]
    reasons = ["defective", "damaged", "changed_mind", "wrong_size"]
    check("I", "returned units written off, " + " / ".join(reasons) + " (settings "
               + " / ".join(f"{cs.write_off_share[r]:.0%}" for r in reasons) + ")",
          " / ".join(f"{share[r]:.0%}" for r in reasons),
          all(abs(share[r] - cs.write_off_share[r]) <= 0.05 for r in reasons))
    method = payments["order_id"].map(lines.drop_duplicates("order_id").set_index("order_id")["payment_method"])
    paid = payments[payments["fee_rate"] > 0]
    rate = (paid["payment_fee"].groupby(method[paid.index]).sum()
            / paid["payment_amount"].groupby(method[paid.index]).sum())
    names = ["BLIK", "Card", "Deferred payment"]
    check("I", "payment fee / amount paid, " + " / ".join(names) + " (rates "
               + " / ".join(f"{cs.payment_fee_rate[n]:.1%}" for n in names) + " plus a fixed fee)",
          " / ".join(f"{rate[n]:.2%}" for n in names),
          rate["BLIK"] < rate["Card"] < rate["Deferred payment"]
          and all(0 <= rate[n] - cs.payment_fee_rate[n] <= 0.003 for n in names))
    affiliate = shipped[shipped["channel"] == "affiliate"]
    value = (affiliate["quantity"] * affiliate["unit_price_gross"] * (1 - affiliate["discount_rate"])).sum()
    outside = int((lines.loc[lines["channel"] != "affiliate", "affiliate_commission"] != 0).sum())
    check("I", "affiliate commission / affiliate net revenue; commission outside the affiliate channel",
          f"{affiliate['affiliate_commission'].sum() / (value / (1 + ms.vat_rate)):.1%}; {outside}",
          0.03 <= affiliate["affiliate_commission"].sum() / (value / (1 + ms.vat_rate)) <= 0.10 and outside == 0)
    parts = {"carrier": shipments["carrier_cost"].sum(),
             "returns": returns[["return_shipping_cost", "handling_cost", "write_off_cost"]].sum().sum(),
             "payments": payments["payment_fee"].sum(), "commission": lines["affiliate_commission"].sum()}
    check("I", "shop costs / net revenue of shipped orders: " + " / ".join(parts),
          " / ".join(f"{value / net:.1%}" for value in parts.values()),
          all(0.002 <= value / net <= 0.05 for value in parts.values()))


# ---------------------------------------------------------------------------------------------------------------- #
# Pack J: suppliers, purchase orders and stock

STOCKOUT_RUN = {"products": 1_500, "order_lines": 100_000}  # a denser catalog: most products sell every month


def regular_orders(orders):
    """One row per regular (not express) purchase order that arrived, with its lead time in days."""
    regular = orders[~orders["is_express"] & orders["received_date"].notna()].drop_duplicates("purchase_order_id")
    return regular.assign(lead_days=(regular["received_date"] - regular["order_date"]).dt.days)


def end_stock_value(data):
    movements = data["stock_movement_data"].sort_values("stock_movement_id")
    last = movements.groupby("product_id")["stock_after"].last()
    cost = data["product_data"].set_index("product_id")["net_purchase_price"]
    return last * cost.reindex(last.index)


def check_j(data):
    import settings.inventory_settings as inv
    suppliers = data["supplier_data"].set_index("supplier_id")
    orders = regular_orders(data["purchase_order_data"])
    stats = orders.groupby("supplier_id")["lead_days"].agg(["mean", "std", "size"])
    stats = stats[stats["size"] >= 20]
    ratio = stats["mean"] / suppliers.loc[stats.index, "true_lead_time_mean_days"]
    check("J", f"mean lead time / true mean, {len(stats)} suppliers with 20+ orders (lowest / highest)",
          f"{ratio.min():.2f} / {ratio.max():.2f}", ratio.between(0.9, 1.1).all())
    late = (orders["received_date"] > orders["promised_date"]).mean()
    check("J", "regular purchase orders received after the promised date", f"{late:.0%}", 0.2 <= late <= 0.6)
    origin = orders.groupby(orders["supplier_id"].map(suppliers["country"]))["lead_days"].mean()
    check("J", "mean lead time by origin, " + " / ".join(origin.index), " / ".join(f"{v:.1f}" for v in origin) +
          " days", origin.get("CN", 99) > 3 * max(origin.drop("CN", errors="ignore")))
    received = data["purchase_order_data"].dropna(subset=["received_date"])
    express = received.loc[received["is_express"], "received_quantity"].sum() / received["received_quantity"].sum()
    check("J", "stockouts off: units that came by express delivery / all units received", f"{express:.1%}",
          0 < express <= 0.15 and data["lost_demand_data"].empty)

    with service.overridden_settings({"stockouts": True}, inv):
        short = generate(**STOCKOUT_RUN)
    lines, lost = short["order_data"], short["lost_demand_data"]
    served, missed = lines["quantity"].sum(), lost["quantity"].sum()
    check("J", f"stockouts on ({STOCKOUT_RUN['products']:,} products): units served / units asked for",
          f"{served / (served + missed):.1%}", 0.88 <= served / (served + missed) <= 0.96)
    month = lambda frame: frame["order_date"].dt.month.isin([11, 12])  # noqa: E731
    peak = lambda frame: frame.groupby(month(frame))["quantity"].sum()  # noqa: E731
    share = peak(lost) / (peak(lost) + peak(lines))
    check("J", "stockouts on: lost share of demand, November-December / other months",
          f"{share[True]:.1%} / {share[False]:.1%}", share[True] >= 1.4 * share[False])
    value = end_stock_value(short)
    sold = lines.loc[lines["order_date"] > lines["order_date"].max() - pd.Timedelta(days=90), "product_id"]
    idle = value[~value.index.isin(sold)].sum() / value.sum()
    check("J", "stockouts on: stock value at the end in products with no sale in the last 90 days",
          f"{idle:.0%}", 0.05 <= idle <= 0.5)
    sessions = short["session_data"]
    check("J", "stockouts on: sessions linked to an order / orders", f"{sessions['order_id'].notna().sum():,} / "
          f"{lines['order_id'].nunique():,}", sessions["order_id"].notna().sum() == lines["order_id"].nunique())


PACKS = {"E": check_e, "A": check_a, "D": check_d, "B": check_b, "C": check_c, "F": check_f, "G": check_g,
         "H": check_h, "I": check_i, "J": check_j}


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
