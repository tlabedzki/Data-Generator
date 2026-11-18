"""
Vectorized order engine.

1. The number of orders follows from the target number of order lines (1-5 lines per order).
2. New customers place their first order around their signup date.
3. Repeat orders are allocated to customers in proportion to their purchase rate and the time they stay active;
   each repeat order's day is drawn from the demand calendar inside the customer's active window. Day weights are
   divided by the active customer base of the month, so the total orders per day follow the calendar (seasonality
   and growth) while individual customers churn.
4. Order lines get a category (base mix × category seasonality × age and gender affinity), a product (popularity ×
   brand, only products on sale that day, fewer when their list price is high), a discount (category × month ×
   special day × segment) and a quantity (more units when discounted).
5. Payment and delivery follow the customer's habits; expensive orders are paid differently.
"""
import numpy as np
import pandas as pd

import func.behaviour as b
import func.calendar as cal
import func.data as d
import func.prices as pr
import settings.basket_settings as bk
import settings.behaviour_settings as bs
import settings.commerce_settings as cs
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
    cumulative = segment_intensity(weights, multipliers, base)
    if repeat_count > 0 and len(eligible):
        expected = np.zeros(len(behaviour))
        segment_of = behaviour["customer_segment"].to_numpy()
        start, end = behaviour["window_start"].to_numpy(), behaviour["window_end"].to_numpy()
        for name, c in cumulative.items():
            rows = eligible[segment_of[eligible] == name]
            expected[rows] = behaviour["purchase_rate"].to_numpy()[rows] * (c[end[rows] + 1] - c[start[rows]])
        if expected.sum() > 0:
            counts = generator.multinomial(repeat_count, expected / expected.sum())
            repeat_rows = np.repeat(np.arange(len(behaviour)), counts)
            repeat_days = draw_repeat_days(repeat_rows, behaviour, cumulative, generator)

    days = np.concatenate([first_days, repeat_days]).astype(int)
    rows = np.concatenate([first_rows, repeat_rows]).astype(int)
    is_repeat = np.concatenate([np.zeros(len(first_days), bool), np.ones(len(repeat_days), bool)])
    if len(rows) < order_count:  # degenerate settings (for example only one-time customers): fill up at random
        extra = order_count - len(rows)
        rows = np.concatenate([rows, generator.choice(len(behaviour), size=extra)])
        days = np.concatenate([days, generator.choice(len(weights), size=extra, p=weights)])
        is_repeat = np.concatenate([is_repeat, np.zeros(extra, bool)])

    # Replenishing customers buy on their product's cycle; the other repeat orders fill up each day so that the
    # totals still follow the calendar.
    days, moved = schedule_replenishment(days, rows, behaviour, generator)
    free = is_repeat & ~moved
    if moved.any() and free.any():
        factor = day_correction(days, ~free, free.sum(), calendar, order_count)
        corrected = segment_intensity(weights * factor, multipliers, base)
        days[free] = draw_repeat_days(rows[free], behaviour, corrected, generator)
    order = np.lexsort((generator.random(len(days)), days))
    return days[order], rows[order]


def segment_intensity(weights, multipliers, base):
    """Cumulative per-customer purchase intensity by day for every segment: weight × multiplier / active base."""
    cumulative = {}
    for name, multiplier in multipliers.items():
        with np.errstate(divide="ignore", invalid="ignore"):
            intensity = np.where(base > 0, weights * multiplier / base, 0.0)
        cumulative[name] = np.concatenate([[0.0], np.cumsum(intensity)])
    return cumulative


def draw_repeat_days(rows, behaviour, cumulative, generator):
    """Draw a day inside each customer's active window, following the segment's cumulative intensity."""
    days = np.zeros(len(rows), dtype=int)
    segment_of = behaviour["customer_segment"].to_numpy()[rows]
    for name, c in cumulative.items():
        slots = np.flatnonzero(segment_of == name)
        if not len(slots):
            continue
        start = behaviour["window_start"].to_numpy()[rows[slots]]
        end = behaviour["window_end"].to_numpy()[rows[slots]]
        u = c[start] + generator.random(len(slots)) * (c[end + 1] - c[start])
        days[slots] = np.clip(np.searchsorted(c, u, side="right") - 1, start, end)
    return days


def day_correction(days, fixed, free_count, calendar, order_count):
    """
    Day multipliers that give the free orders the daily totals still missing after the fixed orders (first orders
    and replenishment), so that all orders together follow the calendar, special days included.
    """
    share = calendar["weight"].to_numpy()
    fixed_count = np.bincount(days[fixed], minlength=len(share))
    missing = np.clip(share * order_count - fixed_count, 0, None)
    if missing.sum() <= 0:
        return np.ones(len(share))
    desired = missing / missing.sum() * free_count
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(share > 0, desired / (share * free_count), 1.0)


def category_probability_matrix(categories, base_probabilities):
    """Cumulative category probabilities for every (month, special day, age group, gender) combination."""
    age_limits = sorted(bs.age_category_affinity)
    genders = ["Female", "Male"]
    events = cal.event_names()
    rows = []
    for month in range(1, 13):
        season = np.array([ms.category_monthly_seasonality.get(c, {}).get(month, 1.0) for c in categories])
        for event in events:
            boosts = cs.special_days[event]["categories"] if event else {}
            boost = np.array([boosts.get(c, 1.0) for c in categories])
            for limit in age_limits:
                age = np.array([bs.age_category_affinity[limit].get(c, 1.0) for c in categories])
                for gender in genders:
                    sex = np.array([bs.gender_category_affinity.get(gender, {}).get(c, 1.0) for c in categories])
                    p = np.asarray(base_probabilities) * season * boost * age * sex
                    rows.append(np.cumsum(p / p.sum()))
    return np.array(rows), len(events), len(age_limits), genders


def draw_categories(line_month, line_event, line_age, line_gender, params, generator):
    categories, base = d.get_param_list_and_normalized_probabilities(params["product_category_weights"])
    matrix, events, age_groups, genders = category_probability_matrix(categories, base)
    gender_index = np.where(np.asarray(line_gender) == "Male", 1, 0)
    key = (((np.asarray(line_month) - 1) * events + np.asarray(line_event)) * age_groups
           + age_group_index(line_age)) * 2 + gender_index
    return np.asarray(categories, dtype=object)[draw_categorical(matrix[key], generator)]


def draw_from_pool(ids, weights, slots, line_day, price_book, generator, tier_exponent=None, rounds=12):
    """
    Draw products from one pool (a category or a product type) by popularity x brand, keeping each with the chance
    price_book.acceptance gives (0 when not on sale that day, lower for a high list price or the wrong price tier).
    """
    p = weights / weights.sum()
    chosen = np.zeros(len(slots), dtype=np.int64)
    pending = np.arange(len(slots))
    for _ in range(rounds):
        if not len(pending):
            break
        candidates = ids[generator.choice(len(ids), size=len(pending), p=p)]
        exponent = None if tier_exponent is None else tier_exponent[slots[pending]]
        keep = generator.random(len(pending)) < price_book.acceptance(candidates, line_day[slots[pending]], exponent)
        chosen[pending[keep]] = candidates[keep]
        pending = pending[~keep]
    for index in pending:  # rare: take any product of the pool on sale that day, else any product
        on_sale = price_book.available(ids, np.full(len(ids), line_day[slots[index]]))
        pool, pool_p = (ids[on_sale], p[on_sale] / p[on_sale].sum()) if on_sale.any() else (ids, p)
        chosen[index] = pool[generator.choice(len(pool), p=pool_p)]
    return chosen


def draw_products(line_category, line_day, params, price_book, generator, tier_exponent=None):
    """Draw a product for every line inside its category."""
    product_ids = np.zeros(len(line_category), dtype=np.int64)
    for category in np.unique(line_category):
        slots = np.flatnonzero(line_category == category)
        product_ids[slots] = draw_from_pool(params["product_ids_by_category"][category],
                                            params["product_weights_by_category"][category], slots, line_day,
                                            price_book, generator, tier_exponent)
    return product_ids


def apply_complements(product_id, line_category, line_order, first_line, line_day, params, price_book, generator,
                      tier_exponent=None):
    """
    Turn further lines of an order into complements of the first line's product type (settings.basket_settings).
    """
    type_of = params["product_type_by_id"]
    anchor_type = type_of.reindex(product_id[first_line[line_order]]).to_numpy()
    later = np.flatnonzero(np.arange(len(product_id)) != first_line[line_order])
    u = generator.random(len(later))
    for anchor, partners in bk.complements.items():
        slots = later[anchor_type[later] == anchor]
        if not len(slots):
            continue
        names = [name for name in partners if name in params["product_ids_by_type"]]
        if not names:
            continue
        edges = np.cumsum([partners[name] for name in names])
        draw = u[np.searchsorted(later, slots)]
        pick = np.searchsorted(edges, draw, side="right")
        for index, name in enumerate(names):
            chosen = slots[pick == index]
            if not len(chosen):
                continue
            product_id[chosen] = draw_from_pool(params["product_ids_by_type"][name],
                                                params["product_weights_by_type"][name], chosen, line_day,
                                                price_book, generator, tier_exponent)
            line_category[chosen] = params["category_by_type"][name]
    return product_id, line_category


def schedule_replenishment(days, rows, behaviour, generator):
    """
    Move the repeat orders of replenishing customers onto their product's cycle (first order + cycle × k with a
    small random spread), as long as they stay inside the customer's active window.

    Returns:
    tuple: (days, mask of moved orders).
    """
    moved = np.zeros(len(days), dtype=bool)
    cycle = behaviour["replenishment_cycle"].to_numpy()[rows]
    frame = pd.DataFrame({"row": rows, "day": days, "cycle": cycle})
    frame = frame[frame["cycle"] > 0].sort_values(["row", "day"], kind="stable")
    if frame.empty:
        return days, moved
    step = frame["cycle"].to_numpy() * (1 + generator.normal(0, bk.replenishment_jitter, len(frame)))
    is_first = frame["row"].ne(frame["row"].shift()).to_numpy()
    step = np.where(is_first, 0.0, np.maximum(step, 1.0))
    start = frame.groupby("row")["day"].transform("min").to_numpy()
    planned = start + np.round(pd.Series(step, index=frame.index).groupby(frame["row"]).cumsum().to_numpy())
    end = behaviour["window_end"].to_numpy()[frame["row"].to_numpy()]
    keep = (planned <= np.maximum(end, start)) & ~is_first
    days = days.copy()
    index = frame.index.to_numpy()[keep]
    days[index] = planned[keep].astype(int)
    moved[index] = True
    return days, moved


def replenishment_products(behaviour, params, price_book, calendar, generator):
    """The consumable product each replenishing customer buys again and again (0 for nobody)."""
    kinds = behaviour["replenishment_type"].to_numpy()
    product = np.zeros(len(behaviour), dtype=np.int64)
    first_day = np.clip(behaviour["first_order_day"].to_numpy(), 0, len(calendar) - 1)
    for kind in sorted(set(kinds) - {""}):  # sorted: a set of strings iterates in a per-process order
        if kind not in params["product_ids_by_type"]:
            continue
        slots = np.flatnonzero(kinds == kind)
        product[slots] = draw_from_pool(params["product_ids_by_type"][kind], params["product_weights_by_type"][kind],
                                        slots, first_day, price_book, generator)
    return product


def draw_quantities(line_category, discount, generator):
    """Quantity from the category profile; a discount adds units: expected x (1 - discount) ** -elasticity."""
    quantities = np.ones(len(line_category), dtype=np.int64)
    for category in np.unique(line_category):
        slots = np.flatnonzero(line_category == category)
        profile = ms.category_quantity_profiles.get(category, s.quantity_per_order_line)
        values, p = d.get_param_list_and_normalized_probabilities(profile)
        base = np.asarray(values)[generator.choice(len(values), size=len(slots), p=p)]
        uplift = (1 - discount[slots]) ** -pr.price_elasticity(category) - 1
        quantities[slots] = base + generator.poisson(base * uplift)
    return quantities


def draw_discounts(line_category, line_month, line_boost, line_segment, generator):
    base = np.array([ms.discount_probability_by_category.get(c, 0.0) for c in line_category])
    month = np.array([ms.discount_monthly_multiplier.get(m, 1.0) for m in range(1, 13)])[np.asarray(line_month) - 1]
    affinity = b.segment_table()["discount_affinity"].astype(float)
    segment = affinity.reindex(line_segment).fillna(1.0).to_numpy()
    probability = np.minimum(base * month * np.asarray(line_boost) * segment, 0.95)
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

def generate_order_data(num_rows, params, behaviour, calendar, price_book, generator, progress=None):
    """
    Generate order lines.

    Parameters:
    num_rows (int): Target number of order lines (the result can be up to four lines more).
    params (dict): Product selection parameters (product_ids_by_category, product_weights_by_category,
        product_category_weights).
    behaviour (pd.DataFrame): Customer behaviour from func.behaviour.draw_customer_behaviour.
    calendar (pd.DataFrame): Daily calendar.
    price_book (func.prices.PriceBook): List prices and availability of products by day.
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
    first_line = np.concatenate([[0], np.cumsum(lines_per_order)[:-1]])
    line_row = order_row[line_order]
    line_day = order_day[line_order]
    line_month = calendar["month"].to_numpy()[line_day]
    line_segment = behaviour["customer_segment"].to_numpy()[line_row]
    line_category = draw_categories(line_month, calendar["event_index"].to_numpy()[line_day],
                                    behaviour["age"].to_numpy()[line_row], behaviour["gender"].to_numpy()[line_row],
                                    params, generator)
    loyal_line = generator.random(len(line_row)) < bk.category_loyalty
    line_category = np.where(loyal_line, behaviour["preferred_category"].to_numpy()[line_row], line_category)
    tier_exponent = pd.Series({name: tier["exponent"] for name, tier in bk.price_tiers.items()}).reindex(
        behaviour["price_tier"].to_numpy()[line_row]).fillna(0.0).to_numpy()
    product_id = draw_products(line_category, line_day, params, price_book, generator, tier_exponent)
    product_id, line_category = apply_complements(product_id, line_category, line_order, first_line, line_day,
                                                  params, price_book, generator, tier_exponent)

    # Replenishing customers start every order with their consumable, while it is on sale.
    habit = replenishment_products(behaviour, params, price_book, calendar, generator)[order_row]
    slots = first_line[habit > 0]
    on_sale = price_book.available(habit[habit > 0], line_day[slots])
    product_id[slots[on_sale]] = habit[habit > 0][on_sale]
    line_category[slots[on_sale]] = params["category_by_id"].reindex(product_id[slots[on_sale]]).to_numpy()
    discount = draw_discounts(line_category, line_month, calendar["discount_boost"].to_numpy()[line_day],
                              line_segment, generator)
    quantity = draw_quantities(line_category, discount, generator)
    d.report_progress(progress, 2, 3, steps=3)

    unit_price, _ = price_book.lookup(product_id, line_day)
    line_value = unit_price * quantity * (1 - discount)
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
