"""
Labelled anomalies added to generated orders: shipping addresses, fraud rings and shop outages.

Every anomaly is written to anomaly_data (type, period, affected rows, description) and fraudulent order lines get
is_fraud = True, so anomaly and fraud detection can be scored against the truth.
"""
import numpy as np
import pandas as pd

import func.customer as c
import func.rng as rng
import settings.main_settings as s
import settings.quality_settings as qs

ANOMALY_COLUMNS = ["anomaly_id", "anomaly_type", "start_date", "end_date", "table_name", "affected_rows",
                   "customer_id", "description"]
FIRST_ORDER_ID = 100001
FIRST_ORDER_LINE_ID = 1000001


def empty_anomaly_data():
    return pd.DataFrame({column: pd.Series(dtype=dtype) for column, dtype in zip(
        ANOMALY_COLUMNS, ["int64", "object", "datetime64[ns]", "datetime64[ns]", "object", "int64", "Int64", "object"])})


def draw_postal_codes(generator, size):
    """Draw postal codes weighted by their number of addresses."""
    weights = c.code_df["address_count"].to_numpy(dtype=float)
    index = generator.choice(len(c.code_df), size=size, p=weights / weights.sum())
    return c.code_df["postal_code"].to_numpy()[index]


def add_shipping_postal_codes(order_data, customer_data, generator):
    """
    Ship every order to the customer's postal code, except a small share sent elsewhere (gifts, work address).

    Parameters:
    order_data (pd.DataFrame): Order lines.
    customer_data (pd.DataFrame): Customers with postal_code.
    generator (np.random.Generator): Random stream.

    Returns:
    pd.DataFrame: Order lines with shipping_postal_code.
    """
    home = order_data["customer_id"].map(customer_data.set_index("customer_id")["postal_code"])
    order_ids = order_data["order_id"].unique()
    other = order_ids[generator.random(len(order_ids)) < qs.other_shipping_address_share]
    other_codes = pd.Series(draw_postal_codes(generator, len(other)), index=other)
    shipping = order_data["order_id"].map(other_codes)
    order_data["shipping_postal_code"] = shipping.fillna(home).to_numpy()
    return order_data


def renumber_orders(order_data):
    """
    Sort order lines by date and give orders consecutive IDs and lines unique IDs.

    Lines of one order keep their order: they share the old order_id, which is used as the tie-breaker.
    """
    order_data = order_data.sort_values(["order_date", "order_id"], kind="stable").reset_index(drop=True)
    new_order = order_data["order_id"].ne(order_data["order_id"].shift())
    order_data["order_id"] = new_order.cumsum() + FIRST_ORDER_ID - 1
    order_data["order_line_id"] = np.arange(FIRST_ORDER_LINE_ID, FIRST_ORDER_LINE_ID + len(order_data))
    first = ["order_id", "order_line_id", "order_date"]
    return order_data[first + [column for column in order_data.columns if column not in first]]


def shop_outage_days(generator):
    """Draw outage days: shop_outages_per_year days per year, outside the November-December peak."""
    days = []
    for year in range(s.start_year, s.end_year + 1):
        candidates = pd.date_range(f"{year}-01-01", f"{year}-10-31", freq="D")
        count = min(qs.shop_outages_per_year, len(candidates))
        days.extend(sorted(generator.choice(candidates, size=count, replace=False)))
    return [pd.Timestamp(day) for day in days]


def apply_shop_outages(order_data, generator):
    """
    Move most orders of each outage day to the following days (customers come back once the shop works again).

    Returns:
    tuple: (order lines, list of anomaly records).
    """
    records = []
    last_day = pd.Timestamp(s.end_year, 12, 31)
    for day in shop_outage_days(generator):
        order_ids = order_data.loc[order_data["order_date"] == day, "order_id"].unique()
        moved = order_ids[generator.random(len(order_ids)) >= qs.outage_kept_order_share]
        shift_days = generator.integers(1, qs.outage_recovery_days + 1, size=len(moved))
        new_dates = pd.Series([min(day + pd.Timedelta(days=int(n)), last_day) for n in shift_days], index=moved,
                              dtype="datetime64[ns]")
        lines = order_data["order_id"].isin(moved)
        order_data.loc[lines, "order_date"] = order_data.loc[lines, "order_id"].map(new_dates)
        records.append({
            "anomaly_type": "shop_outage",
            "start_date": day,
            "end_date": day,
            "table_name": "order_data",
            "affected_rows": int(lines.sum()),
            "customer_id": pd.NA,
            "description": f"Shop down for the whole day; {len(moved)} of {len(order_ids)} orders came back within "
                           f"{qs.outage_recovery_days} days.",
        })
    return order_data, records


def fraud_products(product_data, generator, size):
    """Pick expensive products from the fraud categories, weighted by price."""
    categories = list(qs.fraud_category_weights)
    weights = np.array(list(qs.fraud_category_weights.values()), dtype=float)
    chosen_categories = generator.choice(categories, size=size, p=weights / weights.sum())
    product_ids = np.empty(size, dtype=product_data["product_id"].dtype)
    for category in categories:
        slots = chosen_categories == category
        if not slots.any():
            continue
        pool = product_data[product_data["category"] == category]
        if pool.empty:
            pool = product_data
        pool = pool[pool["sales_price_gross"] >= pool["sales_price_gross"].quantile(0.75)]
        prices = pool["sales_price_gross"].to_numpy(dtype=float)
        product_ids[slots] = generator.choice(pool["product_id"].to_numpy(), size=slots.sum(), p=prices / prices.sum())
    return product_ids


def add_fraud_rings(order_data, customer_data, product_data, generator, blocked_days=()):
    """
    Add bursts of fraudulent orders from a few stolen accounts.

    Returns:
    tuple: (order lines with is_fraud, list of anomaly records).
    """
    order_data["is_fraud"] = False
    target = int(round(order_data["order_id"].nunique() * qs.fraud_order_share))
    if target == 0 or customer_data is None or customer_data.empty or product_data is None:
        return order_data, []

    low, high = qs.fraud_orders_per_account
    first_day, last_day = pd.Timestamp(s.start_year, 1, 1), pd.Timestamp(s.end_year, 12, 31)
    days = pd.date_range(first_day, last_day - pd.Timedelta(days=qs.fraud_burst_days), freq="D")
    days = days[~days.isin(list(blocked_days))]
    next_order_id = int(order_data["order_id"].max()) + 1
    template = order_data.iloc[0]
    rows, records = [], []
    created = 0
    while created < target:
        orders = int(min(generator.integers(low, high + 1), target - created))
        customer = customer_data.iloc[int(generator.integers(len(customer_data)))]
        start = pd.Timestamp(generator.choice(days))
        drop_code = draw_postal_codes(generator, 1)[0]
        provider = generator.choice(["Stripe", "PayU", "Przelewy24"])
        line_counts = generator.integers(1, 3, size=orders)
        products = fraud_products(product_data, generator, int(line_counts.sum()))
        offsets = np.sort(generator.integers(0, qs.fraud_burst_days, size=orders))
        product_index = 0
        for order_offset, lines in zip(offsets, line_counts):
            for _ in range(lines):
                rows.append({
                    "order_date": start + pd.Timedelta(days=int(order_offset)),
                    "order_id": next_order_id,
                    "product_id": products[product_index],
                    "quantity": int(generator.integers(1, 3)),
                    "customer_id": customer["customer_id"],
                    "payment_method": "Card",
                    "payment_provider": provider,
                    "delivery_method": generator.choice(["InPost courier", "DPD"]),
                    "discount_rate": 0.0,
                    "shipping_postal_code": drop_code,
                    "is_fraud": True,
                })
                product_index += 1
            next_order_id += 1
        records.append({
            "anomaly_type": "fraud_ring",
            "start_date": start,
            "end_date": start + pd.Timedelta(days=int(offsets.max())),
            "table_name": "order_data",
            "affected_rows": int(line_counts.sum()),
            "customer_id": int(customer["customer_id"]),
            "description": f"Stolen account: {orders} card orders of expensive goods shipped to {drop_code} "
                           f"instead of {customer['postal_code']}.",
        })
        created += orders

    fraud = pd.DataFrame(rows).astype({column: order_data[column].dtype for column in order_data.columns
                                       if column in rows[0] and column != "order_date"})
    return pd.concat([order_data, fraud], ignore_index=True), records


def inject_anomalies(order_data, customer_data, product_data):
    """
    Add shipping addresses and, when enabled, shop outages and fraud rings; give orders final IDs.

    Parameters:
    order_data (pd.DataFrame): Order lines.
    customer_data (pd.DataFrame or None): Customers.
    product_data (pd.DataFrame or None): Products.

    Returns:
    tuple: (order lines, anomaly_data).
    """
    generator = rng.stream("anomalies")
    if customer_data is not None:
        order_data = add_shipping_postal_codes(order_data, customer_data, generator)
    records = []
    if qs.inject_anomalies:
        order_data, outage_records = apply_shop_outages(order_data, generator)
        blocked = [record["start_date"] for record in outage_records]
        order_data, fraud_records = add_fraud_rings(order_data, customer_data, product_data, generator, blocked)
        records = outage_records + fraud_records
    elif "is_fraud" not in order_data:
        order_data["is_fraud"] = False
    order_data = renumber_orders(order_data)

    anomaly_data = empty_anomaly_data() if not records else pd.DataFrame(records)
    if records:
        anomaly_data = anomaly_data.sort_values("start_date", kind="stable").reset_index(drop=True)
        anomaly_data.insert(0, "anomaly_id", np.arange(1, len(anomaly_data) + 1))
        anomaly_data["customer_id"] = anomaly_data["customer_id"].astype("Int64")
        anomaly_data = anomaly_data[ANOMALY_COLUMNS]
    return order_data, anomaly_data
