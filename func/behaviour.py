"""
Customer behaviour: hidden segments, signup dates, purchase frequency and churn ("buy till you die").

Every customer gets a segment, a signup date, a personal purchase rate (gamma-distributed inside the segment) and a
lifetime after which they stop buying. The order engine (func/order.py) turns this into orders.
"""
import numpy as np
import pandas as pd

import func.data as d
import settings.behaviour_settings as bs
import settings.main_settings as s
import settings.market_settings as ms

NO_DAY = -1


def segment_table():
    """Segment settings as a DataFrame indexed by segment name."""
    table = pd.DataFrame(bs.customer_segments).T
    table["share"] = table["share"].astype(float) / table["share"].astype(float).sum()
    return table


def draw_customer_behaviour(customer_data, calendar, generator):
    """
    Draw the behaviour of every customer.

    Parameters:
    customer_data (pd.DataFrame): Customers (customer_id, age, gender).
    calendar (pd.DataFrame): Daily calendar from func.calendar.build_calendar.
    generator (np.random.Generator): Random stream.

    Returns:
    pd.DataFrame: One row per customer with customer_id, customer_segment, signup_date, first_order_day (calendar
    index or -1), window_start and window_end (calendar indexes of the period in which repeat orders can happen,
    empty when start > end), purchase_rate, usual_payment and usual_delivery.
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
    buys = (generator.random((~existing).sum()) >= bs.no_order_share) & (candidate < days)
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
    window_end = np.where(rate > 0, window_end, -1)
    window_start = np.where(window_end >= window_start, window_start, days)

    usual_payment = draw_from(ms.payment_method_with_probabilities, generator, count)
    usual_delivery = draw_from(ms.delivery_method_with_probabilities, generator, count)

    return pd.DataFrame({
        "customer_id": customer_data["customer_id"].to_numpy(),
        "customer_segment": segment,
        "signup_date": pd.to_datetime(signup).normalize(),
        "existing": existing,
        "first_order_day": first_order_day,
        "window_start": window_start,
        "window_end": window_end,
        "purchase_rate": rate,
        "usual_payment": usual_payment,
        "usual_delivery": usual_delivery,
        "age": customer_data["age"].to_numpy(),
        "gender": customer_data["gender"].to_numpy(),
    })


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


def add_behaviour_columns(customer_data, behaviour):
    """Add signup_date and customer_segment to the customer table (after customer_id and personal data)."""
    customer_data = customer_data.copy()
    customer_data["signup_date"] = behaviour["signup_date"].to_numpy()
    customer_data["customer_segment"] = behaviour["customer_segment"].to_numpy()
    return customer_data
