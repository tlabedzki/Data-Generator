"""
Vectorized order engine.

1. The number of orders follows from the target number of order lines (1-5 lines per order).
2. New customers place their first order around their signup date.
3. Repeat orders are allocated to customers in proportion to their purchase rate and the time they stay active;
   each repeat order's day is drawn from the demand calendar inside the customer's active window. Day weights are
   divided by the active customer base of the month, so the total orders per day follow the calendar (seasonality
   and growth) while individual customers churn.
4. Order lines get a category (base mix × category seasonality × age and gender affinity), a product (popularity ×
   brand), a quantity and a discount (category × month × segment).
5. Payment and delivery follow the customer's habits; expensive orders are paid differently.
"""
import numpy as np
import pandas as pd

import func.behaviour as b
import func.data as d
import settings.behaviour_settings as bs
import settings.main_settings as s
import settings.market_settings as ms

FIRST_ORDER_ID = 100001
MAX_FIRST_ORDER_SHARE = 0.9  # with very many customers and few lines, at most this share of orders are first orders


# ---------------------------------------------------------------------------------------------------------------- #
# Helpers

def draw_categorical(cumulative, generator):
    """Draw one index per row from a matrix of row-wise cumulative probabilities."""
    u = generator.random(len(cumulative))[:, None]
    return np.minimum((cumulative < u).sum(axis=1), cumulative.shape[1] - 1)


def draw_values(probabilities, generator, size):
    values, p = d.get_param_list_and_normalized_probabilities(probabilities)
    return np.asarray(values, dtype=object)[generator.choice(len(values), size=size, p=p)]


def age_group_index(ages):
    limits = sorted(bs.age_category_affinity)
    return np.minimum(np.searchsorted(limits, np.asarray(ages), side="left"), len(limits) - 1)


# ---------------------------------------------------------------------------------------------------------------- #
# Orders: who buys and when

def count_orders(num_rows, generator):
    """Draw lines per order until the target number of lines is reached."""
    values, p = d.get_param_list_and_normalized_probabilities(s.order_line_number)
    lines = np.asarray(values)[generator.choice(len(values), size=max(num_rows, 1), p=p)]
    total = np.cumsum(lines)
    orders = int(np.searchsorted(total, num_rows) + 1)
    return lines[:orders]


def active_base(behaviour, calendar, multipliers):
    """Purchase-rate-weighted number of active customers per day, averaged per month."""
    days = len(calendar)
    base = np.zeros(days)
    for segment, multiplier in multipliers.items():
        rows = behaviour[(behaviour["customer_segment"] == segment) & (behaviour["window_start"] <= behaviour["window_end"])]
        diff = np.zeros(days + 1)
        np.add.at(diff, rows["window_start"].to_numpy(), rows["purchase_rate"].to_numpy())
        np.add.at(diff, rows["window_end"].to_numpy() + 1, -rows["purchase_rate"].to_numpy())
        base += np.cumsum(diff)[:days] * multiplier
    month_key = (calendar["year"].to_numpy() - s.start_year) * 12 + calendar["month"].to_numpy() - 1
    return pd.Series(base).groupby(month_key).transform("mean").to_numpy()


def draw_order_customers(behaviour, calendar, order_count, generator):
    """
    Decide who places each order and on which day.

    Returns:
    tuple: (day index per order, customer row index per order).
    """
    first_rows = np.flatnonzero(behaviour["first_order_day"].to_numpy() >= 0)
    cap = int(MAX_FIRST_ORDER_SHARE * order_count)
    if len(first_rows) > cap:
        first_rows = np.sort(generator.choice(first_rows, size=cap, replace=False))
    first_days = behaviour["first_order_day"].to_numpy()[first_rows]
    repeat_count = order_count - len(first_rows)

    segments = b.segment_table()
    multipliers = {name: b.promo_multiplier(calendar, float(row["promo_month_power"])) for name, row in segments.iterrows()}
    base = active_base(behaviour, calendar, multipliers)
    weights = calendar["weight"].to_numpy()

    repeat_rows, repeat_days = np.array([], dtype=int), np.array([], dtype=int)
    eligible = np.flatnonzero((behaviour["window_start"] <= behaviour["window_end"]).to_numpy()
                              & (behaviour["purchase_rate"].to_numpy() > 0))
    if repeat_count > 0 and len(eligible):
        cumulative = {}
        expected = np.zeros(len(behaviour))
        for name, multiplier in multipliers.items():
            with np.errstate(divide="ignore", invalid="ignore"):
                intensity = np.where(base > 0, weights * multiplier / base, 0.0)
            cumulative[name] = np.concatenate([[0.0], np.cumsum(intensity)])
            rows = eligible[behaviour["customer_segment"].to_numpy()[eligible] == name]
            start, end = behaviour["window_start"].to_numpy()[rows], behaviour["window_end"].to_numpy()[rows]
            expected[rows] = behaviour["purchase_rate"].to_numpy()[rows] * (cumulative[name][end + 1] - cumulative[name][start])
        if expected.sum() > 0:
            counts = generator.multinomial(repeat_count, expected / expected.sum())
            repeat_rows = np.repeat(np.arange(len(behaviour)), counts)
            repeat_days = np.empty(len(repeat_rows), dtype=int)
            segment_of = behaviour["customer_segment"].to_numpy()[repeat_rows]
            for name in multipliers:
                slots = np.flatnonzero(segment_of == name)
                if not len(slots):
                    continue
                rows = repeat_rows[slots]
                start = behaviour["window_start"].to_numpy()[rows]
                end = behaviour["window_end"].to_numpy()[rows]
                c = cumulative[name]
                u = c[start] + generator.random(len(rows)) * (c[end + 1] - c[start])
                repeat_days[slots] = np.clip(np.searchsorted(c, u, side="right") - 1, start, end)

    days = np.concatenate([first_days, repeat_days]).astype(int)
    rows = np.concatenate([first_rows, repeat_rows]).astype(int)
    if len(rows) < order_count:  # degenerate settings (for example only one-time customers): fill up at random
        extra = order_count - len(rows)
        rows = np.concatenate([rows, generator.choice(len(behaviour), size=extra)])
        days = np.concatenate([days, generator.choice(len(weights), size=extra, p=weights)])
    order = np.lexsort((generator.random(len(days)), days))
    return days[order], rows[order]


# ---------------------------------------------------------------------------------------------------------------- #
# Order lines: what is bought

def category_probability_matrix(categories, base_probabilities):
    """Cumulative category probabilities for every (month, age group, gender) combination."""
    age_limits = sorted(bs.age_category_affinity)
    genders = ["Female", "Male"]
    rows = []
    for month in range(1, 13):
        season = np.array([ms.category_monthly_seasonality.get(c, {}).get(month, 1.0) for c in categories])
        for limit in age_limits:
            age = np.array([bs.age_category_affinity[limit].get(c, 1.0) for c in categories])
            for gender in genders:
                sex = np.array([bs.gender_category_affinity.get(gender, {}).get(c, 1.0) for c in categories])
                p = np.asarray(base_probabilities) * season * age * sex
                rows.append(np.cumsum(p / p.sum()))
    return np.array(rows), len(age_limits), genders


def draw_categories(line_month, line_age, line_gender, params, generator):
    categories, base = d.get_param_list_and_normalized_probabilities(params["product_category_weights"])
    matrix, age_groups, genders = category_probability_matrix(categories, base)
    gender_index = np.where(np.asarray(line_gender) == "Male", 1, 0)
    key = (np.asarray(line_month) - 1) * age_groups * 2 + age_group_index(line_age) * 2 + gender_index
    return np.asarray(categories, dtype=object)[draw_categorical(matrix[key], generator)]


def draw_products(line_category, params, generator):
    product_ids = np.zeros(len(line_category), dtype=np.int64)
    for category in np.unique(line_category):
        slots = np.flatnonzero(line_category == category)
        ids = params["product_ids_by_category"][category]
        weights = params["product_weights_by_category"][category]
        product_ids[slots] = ids[generator.choice(len(ids), size=len(slots), p=weights / weights.sum())]
    return product_ids


def draw_quantities(line_category, generator):
    quantities = np.ones(len(line_category), dtype=np.int64)
    for category in np.unique(line_category):
        slots = np.flatnonzero(line_category == category)
        profile = ms.category_quantity_profiles.get(category, s.quantity_per_order_line)
        values, p = d.get_param_list_and_normalized_probabilities(profile)
        quantities[slots] = np.asarray(values)[generator.choice(len(values), size=len(slots), p=p)]
    return quantities


def draw_discounts(line_category, line_month, line_segment, generator):
    base = np.array([ms.discount_probability_by_category.get(c, 0.0) for c in line_category])
    month = np.array([ms.discount_monthly_multiplier.get(m, 1.0) for m in range(1, 13)])[np.asarray(line_month) - 1]
    affinity = b.segment_table()["discount_affinity"].astype(float)
    segment = affinity.reindex(line_segment).fillna(1.0).to_numpy()
    probability = np.minimum(base * month * segment, 0.95)
    discounted = generator.random(len(base)) < probability
    types, type_p = d.get_param_list_and_normalized_probabilities(ms.discount_type_probabilities)
    chosen = generator.choice(len(types), size=len(base), p=type_p)
    low = np.array([ms.discount_rate_ranges[t][0] for t in types])[chosen]
    high = np.array([ms.discount_rate_ranges[t][1] for t in types])[chosen]
    rates = np.round(low + generator.random(len(base)) * (high - low), 4)
    return np.where(discounted, rates, 0.0)


def draw_payments(order_value, usual_payment, generator):
    """Usual payment method most of the time; expensive orders follow the high-value mix."""
    normal = draw_values(ms.payment_method_with_probabilities, generator, len(order_value))
    high_mix = {method: p * bs.high_value_payment_multipliers.get(method, 1.0)
                for method, p in ms.payment_method_with_probabilities.items()}
    high = draw_values(high_mix, generator, len(order_value))
    habit = generator.random(len(order_value)) < bs.usual_payment_share
    expensive = order_value > bs.high_value_order_threshold
    return np.where(expensive, high, np.where(habit, usual_payment, normal))


def draw_deliveries(usual_delivery, generator):
    normal = draw_values(ms.delivery_method_with_probabilities, generator, len(usual_delivery))
    habit = generator.random(len(usual_delivery)) < bs.usual_delivery_share
    return np.where(habit, usual_delivery, normal)


# ---------------------------------------------------------------------------------------------------------------- #
# Main entry point

def generate_order_data(num_rows, params, behaviour, calendar, generator, progress=None):
    """
    Generate order lines.

    Parameters:
    num_rows (int): Target number of order lines (the result can be up to four lines more).
    params (dict): Product selection parameters (product_ids_by_category, product_weights_by_category,
        product_category_weights) and product prices (price_by_product).
    behaviour (pd.DataFrame): Customer behaviour from func.behaviour.draw_customer_behaviour.
    calendar (pd.DataFrame): Daily calendar.
    generator (np.random.Generator): Random stream.
    progress (callable, optional): Called with the completed fraction (0-1).

    Returns:
    pd.DataFrame: Order lines sorted by date with order_id, order_date, product_id, quantity, customer_id,
    payment_method, payment_provider, delivery_method and discount_rate.
    """
    lines_per_order = count_orders(num_rows, generator)
    order_count = len(lines_per_order)
    order_day, order_row = draw_order_customers(behaviour, calendar, order_count, generator)
    d.report_progress(progress, 1, 3, steps=3)

    line_order = np.repeat(np.arange(order_count), lines_per_order)
    line_row = order_row[line_order]
    line_day = order_day[line_order]
    line_month = calendar["month"].to_numpy()[line_day]
    line_segment = behaviour["customer_segment"].to_numpy()[line_row]
    line_category = draw_categories(line_month, behaviour["age"].to_numpy()[line_row],
                                    behaviour["gender"].to_numpy()[line_row], params, generator)
    product_id = draw_products(line_category, params, generator)
    quantity = draw_quantities(line_category, generator)
    discount = draw_discounts(line_category, line_month, line_segment, generator)
    d.report_progress(progress, 2, 3, steps=3)

    prices = params["price_by_product"]
    line_value = prices.reindex(product_id).to_numpy() * quantity * (1 - discount)
    order_value = np.bincount(line_order, weights=line_value, minlength=order_count)
    payment = draw_payments(order_value, behaviour["usual_payment"].to_numpy()[order_row], generator)
    provider = draw_values(ms.payment_provider_with_probabilities, generator, order_count)
    delivery = draw_deliveries(behaviour["usual_delivery"].to_numpy()[order_row], generator)

    data = pd.DataFrame({
        "order_id": line_order + FIRST_ORDER_ID,
        "order_date": calendar["date"].to_numpy()[line_day],
        "product_id": product_id,
        "quantity": quantity,
        "customer_id": behaviour["customer_id"].to_numpy()[line_row],
        "payment_method": payment[line_order],
        "payment_provider": provider[line_order],
        "delivery_method": delivery[line_order],
        "discount_rate": discount,
    })
    d.report_progress(progress, 3, 3, steps=3)
    return data
