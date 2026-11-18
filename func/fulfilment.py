"""
After the orders are drawn: time of day, the list price on the order day, delivery of bulky goods, shipments and
returns.
"""
import numpy as np
import pandas as pd

import func.data as d
import settings.commerce_settings as cs
import settings.quality_settings as qs
import settings.market_settings as ms

SHIPMENT_COLUMNS = ["shipment_id", "order_id", "delivery_method", "is_bulky", "shipping_cost", "shipped_at",
                    "delivered_at", "promised_delivery_date", "is_late"]
RETURN_COLUMNS = ["return_id", "order_id", "order_line_id", "product_id", "customer_id", "return_date",
                  "returned_quantity", "return_reason", "refund_amount", "return_status"]
NON_WORKING_EVENTS = {"christmas_eve", "christmas", "new_year", "easter_monday", "easter_sunday"}
REJECTED_RETURN_SHARE = 0.04


def order_level(order_data):
    """First line of every order (orders share date, customer, payment and delivery)."""
    return order_data.drop_duplicates("order_id")


def add_order_times(order_data, generator):
    """Add order_datetime: the order day plus an hour from hour_weights (fraud: fraud_hour_weights)."""
    orders = order_level(order_data)
    fraud = orders["is_fraud"].to_numpy() if "is_fraud" in orders else np.zeros(len(orders), dtype=bool)
    normal_p = np.asarray(cs.hour_weights, dtype=float)
    fraud_p = np.asarray(cs.fraud_hour_weights, dtype=float)
    hours = np.where(fraud, generator.choice(24, size=len(orders), p=fraud_p / fraud_p.sum()),
                     generator.choice(24, size=len(orders), p=normal_p / normal_p.sum()))
    seconds = hours * 3600 + generator.integers(0, 3600, size=len(orders))
    stamps = pd.Series(orders["order_date"].to_numpy() + seconds.astype("timedelta64[s]"), index=orders["order_id"])
    position = order_data.columns.get_loc("order_date") + 1
    order_data.insert(position, "order_datetime", order_data["order_id"].map(stamps).to_numpy())
    return order_data


def add_unit_prices(order_data, price_book):
    """Add the list price valid on the order day (gross and net, before the line discount)."""
    days = (order_data["order_date"] - price_book.start).dt.days.clip(0, price_book.days - 1).to_numpy()
    gross, net = price_book.lookup(order_data["product_id"].to_numpy(), days)
    position = order_data.columns.get_loc("quantity") + 1
    order_data.insert(position, "unit_price_gross", gross)
    order_data.insert(position + 1, "unit_price_net", net)
    return order_data


def fit_delivery_to_products(order_data, product_data, generator):
    """Orders with a bulky product cannot go to a parcel locker: they get a courier instead."""
    bulky_products = product_data.loc[product_data["product_type"].isin(cs.bulky_product_types), "product_id"]
    bulky_orders = order_data.loc[order_data["product_id"].isin(bulky_products), "order_id"].unique()
    orders = order_level(order_data).set_index("order_id")["delivery_method"]
    wrong = orders[orders.index.isin(bulky_orders) & orders.isin(cs.locker_delivery_methods)]
    values, p = d.get_param_list_and_normalized_probabilities(cs.bulky_delivery_methods)
    replacement = pd.Series(np.asarray(values, dtype=object)[generator.choice(len(values), size=len(wrong), p=p)],
                            index=wrong.index)
    lines = order_data["order_id"].isin(wrong.index)
    order_data.loc[lines, "delivery_method"] = order_data.loc[lines, "order_id"].map(replacement)
    return order_data, set(bulky_orders)


def next_working_days(days, holidays):
    """Move every date forward to the nearest working day (Monday-Friday, not a shop holiday)."""
    return np.busday_offset(days.astype("datetime64[D]"), 0, roll="forward", holidays=holidays)


def build_shipments(order_data, calendar, bulky_orders, generator):
    """
    One shipment per order: cost, dispatch from the warehouse, delivery and whether it came later than promised.
    """
    orders = order_level(order_data)
    value = (order_data["quantity"] * order_data["unit_price_gross"] * (1 - order_data["discount_rate"])
             ).groupby(order_data["order_id"]).sum().reindex(orders["order_id"]).to_numpy()
    method = orders["delivery_method"].to_numpy()
    info = {name: cs.delivery_methods.get(name, {"cost": 15.0, "transit_days": (1, 3), "promised_days": 3})
            for name in set(method)}
    bulky = orders["order_id"].isin(bulky_orders).to_numpy()
    cost = np.array([info[m]["cost"] for m in method])
    cost = np.where(value >= cs.free_shipping_threshold, 0.0, cost) + np.where(bulky, cs.bulky_shipping_surcharge, 0.0)

    holidays = calendar.loc[calendar["event"].isin(NON_WORKING_EVENTS), "date"].to_numpy().astype("datetime64[D]")
    placed = orders["order_datetime"].to_numpy()
    placed_day = placed.astype("datetime64[D]")
    hour = orders["order_datetime"].dt.hour.to_numpy()
    after_cutoff = hour >= cs.dispatch_cutoff_hour
    dispatch_day = next_working_days(placed_day + after_cutoff.astype("timedelta64[D]"), holidays)
    peak = np.isin(orders["order_date"].dt.month.to_numpy(), cs.peak_months)
    ready_day = dispatch_day
    slow_warehouse = peak & (generator.random(len(orders)) < cs.peak_delay_share)
    dispatch_day = np.busday_offset(dispatch_day, slow_warehouse.astype(int), roll="forward", holidays=holidays)
    shipped_at = dispatch_day.astype("datetime64[s]") + (
        (cs.dispatch_cutoff_hour + generator.integers(0, 6, size=len(orders))) * 3600
        + generator.integers(0, 3600, size=len(orders))).astype("timedelta64[s]")
    shipped_at = np.maximum(shipped_at, placed.astype("datetime64[s]") + np.timedelta64(1800, "s"))

    low = np.array([info[m]["transit_days"][0] for m in method])
    high = np.array([info[m]["transit_days"][1] for m in method])
    transit = low + (generator.random(len(orders)) * (high - low + 1)).astype(int)
    carrier_delay = generator.random(len(orders)) < np.where(peak, cs.peak_delay_share, cs.carrier_delay_share)
    extra = generator.integers(1, cs.peak_extra_days + 1, size=len(orders))
    transit = transit + np.where(carrier_delay, extra, 0)
    delivered_day = np.busday_offset(shipped_at.astype("datetime64[D]"), transit, roll="forward",
                                     weekmask="1111110", holidays=holidays)
    delivered_at = delivered_day.astype("datetime64[s]") + (
        (9 + generator.integers(0, 11, size=len(orders))) * 3600
        + generator.integers(0, 3600, size=len(orders))).astype("timedelta64[s]")
    promised = np.array([info[m]["promised_days"] for m in method])
    promised_day = np.busday_offset(ready_day, promised, roll="forward", holidays=holidays)

    return pd.DataFrame({
        "shipment_id": np.arange(1, len(orders) + 1),
        "order_id": orders["order_id"].to_numpy(),
        "delivery_method": method,
        "is_bulky": bulky,
        "shipping_cost": np.round(cost, 2),
        "shipped_at": pd.to_datetime(shipped_at),
        "delivered_at": pd.to_datetime(delivered_at),
        "promised_delivery_date": pd.to_datetime(promised_day),
        "is_late": delivered_day > promised_day,
    })[SHIPMENT_COLUMNS]


def return_probability(lines, segments):
    rate = lines["category"].map(lambda c: cs.category_return_rate.get(c, cs.default_return_rate)).to_numpy()
    segment = segments.map(lambda s: cs.segment_return_multiplier.get(s, 1.0)).to_numpy()
    discounted = np.where(lines["discount_rate"].to_numpy() > 0, cs.discounted_return_multiplier, 1.0)
    return np.minimum(rate * segment * discounted, 0.95)


def build_returns(order_data, product_data, customer_data, shipments, generator):
    """
    Draw returns of order lines.

    Returns:
    tuple: (return_data, list of anomaly records for return spikes).
    """
    lines = order_data.merge(product_data[["product_id", "category"]], on="product_id", how="left")
    segments = lines["customer_id"].map(customer_data.set_index("customer_id")["customer_segment"]) \
        if "customer_segment" in customer_data else pd.Series("", index=lines.index)
    delivered = lines["order_id"].map(shipments.set_index("order_id")["delivered_at"])
    probability = return_probability(lines, segments)
    if "is_fraud" in lines:
        probability = np.where(lines["is_fraud"].to_numpy(), 0.0, probability)

    records, spike = [], np.zeros(len(lines), dtype=bool)
    for _ in range(cs.return_spikes if qs.inject_anomalies else 0):
        product, start = pick_spike(lines, generator)
        if product is None:
            continue
        end = start + pd.Timedelta(days=cs.return_spike_days - 1)
        window = (lines["product_id"] == product).to_numpy() & lines["order_date"].between(start, end).to_numpy()
        probability = np.where(window, np.maximum(probability, cs.return_spike_rate), probability)
        spike |= window
        records.append({
            "anomaly_type": "return_spike", "start_date": start, "end_date": end, "table_name": "return_data",
            "affected_rows": int(window.sum()), "customer_id": pd.NA,
            "description": f"Defective batch of product {product}: lines ordered in these days are returned "
                           f"{cs.return_spike_rate:.0%} of the time.",
        })

    returned = generator.random(len(lines)) < probability
    picked = lines[returned]
    count = len(picked)
    late = generator.random(count) >= cs.return_within_14_days_share
    low, high = cs.return_delay_days
    delay = np.where(late, generator.integers(15, max(high, 15) + 1, size=count),
                     generator.integers(low, 15, size=count))
    return_date = (delivered[returned].dt.normalize() + pd.to_timedelta(delay, unit="D")).to_numpy()

    quantity = picked["quantity"].to_numpy()
    partial = (quantity > 1) & (generator.random(count) < 0.3)
    returned_quantity = np.where(partial, 1 + (generator.random(count) * (quantity - 1)).astype(int), quantity)
    reasons = np.empty(count, dtype=object)
    categories = picked["category"].to_numpy()
    for key in sorted(set(categories) | {"default"}):  # sorted: same draws in every process
        slots = categories == key if key != "default" else ~np.isin(categories, list(cs.return_reasons))
        if key != "default" and key not in cs.return_reasons:
            continue
        values, p = d.get_param_list_and_normalized_probabilities(cs.return_reasons[key])
        reasons[slots] = np.asarray(values, dtype=object)[generator.choice(len(values), size=slots.sum(), p=p)]
    reasons[spike[returned]] = "defective"
    rejected = generator.random(count) < REJECTED_RETURN_SHARE
    refund = returned_quantity * picked["unit_price_gross"].to_numpy() * (1 - picked["discount_rate"].to_numpy())

    return_data = pd.DataFrame({
        "order_id": picked["order_id"].to_numpy(),
        "order_line_id": picked["order_line_id"].to_numpy(),
        "product_id": picked["product_id"].to_numpy(),
        "customer_id": picked["customer_id"].to_numpy(),
        "return_date": pd.to_datetime(return_date),
        "returned_quantity": returned_quantity.astype(np.int64),
        "return_reason": reasons,
        "refund_amount": np.where(rejected, 0.0, np.round(refund, 2)),
        "return_status": np.where(rejected, "rejected", "refunded"),
    }).sort_values(["return_date", "order_line_id"], kind="stable").reset_index(drop=True)
    return_data.insert(0, "return_id", np.arange(1, len(return_data) + 1))
    return return_data[RETURN_COLUMNS], records


def pick_spike(lines, generator):
    """A popular product and a start day in the middle part of the period."""
    if lines.empty:
        return None, None
    popular = lines["product_id"].value_counts().head(20).index.to_numpy()
    product = generator.choice(popular)
    dates = lines.loc[lines["product_id"] == product, "order_date"]
    first, last = dates.min(), dates.max() - pd.Timedelta(days=cs.return_spike_days)
    if last <= first:
        return product, first
    offset = int(generator.integers(0, (last - first).days + 1))
    return product, first + pd.Timedelta(days=offset)
