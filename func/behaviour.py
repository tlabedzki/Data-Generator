"""
Customer behaviour: hidden segments, signup dates, purchase frequency and churn ("buy till you die").

Every customer gets a segment, a signup date, a personal purchase rate (gamma-distributed inside the segment) and a
lifetime after which they stop buying. The order engine (func/order.py) turns this into orders.
"""
import numpy as np
import pandas as pd

import func.data as d
import settings.basket_settings as bk
import settings.behaviour_settings as bs
import settings.main_settings as s
import settings.market_settings as ms

NO_DAY = -1


def segment_table():
    """Segment settings as a DataFrame indexed by segment name."""
    table = pd.DataFrame(bs.customer_segments).T
    table["share"] = table["share"].astype(float) / table["share"].astype(float).sum()
    return table


def draw_customer_behaviour(customer_data, calendar, generator, category_weights=None):
    """
    Draw the behaviour of every customer.

    Parameters:
    customer_data (pd.DataFrame): Customers (customer_id, age, gender).
    calendar (pd.DataFrame): Daily calendar from func.calendar.build_calendar.
    generator (np.random.Generator): Random stream.
    category_weights (dict, optional): Base category probabilities of order lines, for the favourite category.

    Returns:
    pd.DataFrame: One row per customer with customer_id, customer_segment, signup_date, first_order_day (calendar
    index or -1), window_start and window_end (calendar indexes of the period in which repeat orders can happen,
    empty when start > end), purchase_rate, churn_day (calendar index of the last day the customer can buy; can lie
    outside the period), usual_payment, usual_delivery, preferred_category, price_tier,
    replenishment_type and replenishment_cycle.
    """
    count = len(customer_data)
    days = len(calendar)
    segments = segment_table()
    segment = generator.choice(segments.index.to_numpy(), size=count, p=segments["share"].to_numpy(dtype=float))
    seg = segments.loc[segment]

    # Signup: existing customers before the period, new customers following the demand calendar.
    existing = generator.random(count) < bs.existing_customer_share
    first_day = pd.Timestamp(s.start_year, 1, 1)
    history_days = int(bs.existing_customer_years * 365)
    signup = np.empty(count, dtype="datetime64[ns]")
    signup_offset = -generator.integers(1, history_days + 1, size=existing.sum())
    signup[existing] = (first_day + pd.to_timedelta(signup_offset, unit="D")).to_numpy()
    new_signup_day = draw_days_from(calendar, generator, (~existing).sum())
    signup[~existing] = calendar["date"].to_numpy()[new_signup_day]

    # First order of new customers: the same day or after a short delay; some never order.
    first_order_day = np.full(count, NO_DAY)
    delay = np.where(generator.random((~existing).sum()) < bs.first_order_same_day_share, 0,
                     generator.geometric(1 / max(bs.first_order_delay_mean_days, 1), (~existing).sum()))
    candidate = new_signup_day + delay
    orders_ever = generator.random((~existing).sum()) >= bs.no_order_share
    buys = orders_ever & (candidate < days)
    new_first = np.where(buys, candidate, NO_DAY)
    first_order_day[~existing] = new_first

    # Lifetime and purchase rate.
    mean_lifetime = seg["lifetime_days"].to_numpy(dtype=float)
    lifetime = np.where(mean_lifetime > 0, generator.exponential(np.maximum(mean_lifetime, 1)), 0.0)
    mean_rate = seg["orders_per_year"].to_numpy(dtype=float) / 365
    shape = bs.purchase_rate_shape
    rate = np.where(mean_rate > 0, generator.gamma(shape, np.maximum(mean_rate, 1e-12) / shape), 0.0)

    # Window of repeat orders, as calendar indexes.
    signup_index = ((pd.DatetimeIndex(signup) - first_day).days).to_numpy()
    window_start = np.where(existing, 0, np.where(first_order_day >= 0, first_order_day + 1, days))
    lifetime_end = np.where(existing, signup_index, first_order_day) + np.floor(lifetime).astype(int)
    window_end = np.minimum(lifetime_end, days - 1)
    # The day the customer stops buying (truth): the end of the lifetime, also when it falls before or after the
    # period; new customers who never order are gone from their signup day, customers whose first order would fall
    # after the period keep the end of the lifetime they would have had.
    churn_day = lifetime_end.copy()
    new_churn = np.where(orders_ever, candidate + np.floor(lifetime[~existing]).astype(int), new_signup_day)
    churn_day[~existing] = new_churn
    window_end = np.where(rate > 0, window_end, -1)
    window_start = np.where(window_end >= window_start, window_start, days)

    usual_payment = draw_from(ms.payment_method_with_probabilities, generator, count)
    usual_delivery = draw_from(ms.delivery_method_with_probabilities, generator, count)

    ages, genders = customer_data["age"].to_numpy(), customer_data["gender"].to_numpy()
    preferred = draw_preferred_categories(ages, genders, category_weights, generator)
    tiers = pd.Series({name: tier["share"] for name, tier in bk.price_tiers.items()})
    price_tier = generator.choice(tiers.index.to_numpy(), size=count, p=(tiers / tiers.sum()).to_numpy())
    replenishment_type, replenishment_cycle = draw_replenishment(segment, ages, generator)

    return pd.DataFrame({
        "customer_id": customer_data["customer_id"].to_numpy(),
        "customer_segment": segment,
        "signup_date": pd.to_datetime(signup).normalize(),
        "existing": existing,
        "first_order_day": first_order_day,
        "window_start": window_start,
        "window_end": window_end,
        "purchase_rate": rate,
        "churn_day": churn_day,
        "usual_payment": usual_payment,
        "usual_delivery": usual_delivery,
        "age": ages,
        "gender": genders,
        "preferred_category": preferred,
        "price_tier": price_tier,
        "replenishment_type": replenishment_type,
        "replenishment_cycle": replenishment_cycle,
    })


def draw_preferred_categories(ages, genders, category_weights, generator):
    """Favourite category of every customer: base category mix × age and gender affinity."""
    weights = category_weights or ms.category_revenue_target_weights
    categories, base = d.get_param_list_and_normalized_probabilities(weights)
    preferred = np.empty(len(ages), dtype=object)
    limits = sorted(bs.age_category_affinity)
    group = np.minimum(np.searchsorted(limits, ages, side="left"), len(limits) - 1)
    for g, limit in enumerate(limits):
        for gender in ("Female", "Male"):
            slots = (group == g) & (genders == gender)
            if not slots.any():
                continue
            p = np.asarray(base) * np.array([bs.age_category_affinity[limit].get(c, 1.0) for c in categories]) \
                * np.array([bs.gender_category_affinity.get(gender, {}).get(c, 1.0) for c in categories])
            preferred[slots] = np.asarray(categories, dtype=object)[
                generator.choice(len(categories), size=slots.sum(), p=p / p.sum())]
    return preferred


def draw_replenishment(segment, ages, generator):
    """Consumable product type some loyal and regular customers buy on a cycle ("" for nobody)."""
    count = len(segment)
    kinds = list(bk.replenishment_products)
    shares = np.array([bk.replenishment_products[k][1] for k in kinds])
    baby = np.array([k in ("Diapers", "Baby Formula") for k in kinds])
    young_parent = (ages >= 25) & (ages <= 44)
    p = np.tile(shares, (count, 1))
    p[:, baby] *= np.where(young_parent, 2.0, 0.2)[:, None]
    p[~np.isin(segment, bk.replenishment_segments)] = 0.0
    none = np.clip(1 - p.sum(axis=1), 0, None)
    cumulative = np.cumsum(np.column_stack([p, none]), axis=1)
    cumulative /= cumulative[:, -1:]
    choice = (cumulative < generator.random(count)[:, None]).sum(axis=1)
    kind = np.array(kinds + [""], dtype=object)[np.minimum(choice, len(kinds))]
    cycle = np.array([bk.replenishment_products[k][0] if k else 0 for k in kind])
    return kind, cycle


def draw_days_from(calendar, generator, size):
    weights = calendar["weight"].to_numpy()
    return generator.choice(len(weights), size=size, p=weights / weights.sum())


def draw_from(probabilities, generator, size):
    values, p = d.get_param_list_and_normalized_probabilities(probabilities)
    return generator.choice(np.asarray(values, dtype=object), size=size, p=p)


def promo_multiplier(calendar, power):
    """Day multiplier of a segment that follows promotional months (discount_monthly_multiplier ** power)."""
    months = calendar["month"].to_numpy()
    multiplier = np.array([ms.discount_monthly_multiplier.get(month, 1.0) for month in range(1, 13)])
    return multiplier[months - 1] ** power


TRUTH_COLUMNS = ["customer_segment", "preferred_category", "price_tier"]
CHURN_TRUTH_COLUMNS = ["true_purchase_rate", "true_churn_date"]


def add_behaviour_columns(customer_data, behaviour):
    """
    Add signup_date and the hidden truth columns (customer_segment, preferred_category, price_tier) to the
    customer table. The truth columns are the answers for segmentation and recommendation exercises.
    """
    customer_data = customer_data.copy()
    customer_data["signup_date"] = behaviour["signup_date"].to_numpy()
    for column in TRUTH_COLUMNS:
        customer_data[column] = behaviour[column].to_numpy()
    return customer_data


def add_churn_truth(customer_data, behaviour, annual_rate):
    """
    Add the answers for churn and customer value models to the customer table:

    - true_purchase_rate: repeat orders a year the customer places while active, at an average time of the year
      (the lambda of a BG/NBD or Pareto/NBD model; 0 for one-time buyers),
    - true_churn_date: the last day the customer can buy; before the period for accounts that were already gone,
      after it for customers still active at the end, the signup day for accounts that never order.
    """
    customer_data = customer_data.copy()
    first_day = pd.Timestamp(s.start_year, 1, 1)
    churn = pd.Series(behaviour["churn_day"].to_numpy(), index=behaviour["customer_id"].to_numpy())
    rate = pd.Series(np.round(annual_rate, 4), index=behaviour["customer_id"].to_numpy())
    customer_data["true_purchase_rate"] = customer_data["customer_id"].map(rate).to_numpy()
    customer_data["true_churn_date"] = first_day + pd.to_timedelta(customer_data["customer_id"].map(churn), unit="D")
    return customer_data
