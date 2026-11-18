"""
Product life cycle (launch and discontinuation) and list price history.

The last list price of every product equals sales_price_gross in product_data; price_history holds every price
with its validity period. PriceBook answers "what was the price of product P on day D?" for many lines at once.
"""
import numpy as np
import pandas as pd

import func.data as d
import settings.commerce_settings as cs
import settings.main_settings as s

PRICE_HISTORY_COLUMNS = ["product_id", "valid_from", "valid_to", "sales_price_gross", "sales_price_net", "change_type"]
HISTORY_YEARS_BEFORE = 3


def period():
    return pd.Timestamp(s.start_year, 1, 1), pd.Timestamp(s.end_year, 12, 31)


def add_life_cycle(product_data, generator):
    """
    Add launch_date and discontinued_date (NaT = still on sale) to the products.

    Products launched during the period appear on a random day; the others existed before. A discontinued product
    stays on sale for at least min_product_life_days.
    """
    start, end = period()
    days = (end - start).days + 1
    count = len(product_data)
    launched_inside = generator.random(count) < cs.launched_during_period_share
    inside_offset = generator.integers(0, max(days - 30, 1), size=count)
    before_offset = -generator.integers(1, HISTORY_YEARS_BEFORE * 365, size=count)
    launch_offset = np.where(launched_inside, inside_offset, before_offset)

    discontinued = generator.random(count) < cs.discontinued_share
    earliest = np.maximum(launch_offset, 0) + cs.min_product_life_days
    possible = earliest < days - 1
    stop_offset = earliest + (generator.random(count) * np.maximum(days - 1 - earliest, 0)).astype(int)
    discontinued &= possible

    product_data = product_data.copy()
    product_data["launch_date"] = start + pd.to_timedelta(launch_offset, unit="D")
    product_data["discontinued_date"] = pd.Series(
        np.where(discontinued, (start + pd.to_timedelta(stop_offset, unit="D")).to_numpy(), np.datetime64("NaT")),
        index=product_data.index, dtype="datetime64[ns]")
    return product_data


def build_price_history(product_data, generator):
    """
    Draw list price changes inside every product's selling period.

    Returns:
    pd.DataFrame: price_history with one row per product and price, oldest first.
    """
    start, end = period()
    first = np.maximum(product_data["launch_date"].to_numpy(), np.datetime64(start))
    last = product_data["discontinued_date"].fillna(end).to_numpy()
    span_days = np.maximum((last - first).astype("timedelta64[D]").astype(int), 0)
    changes = generator.poisson(cs.price_changes_per_year * span_days / 365)

    product_index = np.repeat(np.arange(len(product_data)), changes)
    offsets = (generator.random(len(product_index)) * np.maximum(span_days[product_index], 1)).astype(int) + 1
    change_dates = first[product_index] + offsets.astype("timedelta64[D]")
    increase = generator.random(len(product_index)) < cs.price_increase_share
    low_up, high_up = cs.price_increase_range
    low_down, high_down = cs.price_decrease_range
    size = np.where(increase, low_up + generator.random(len(product_index)) * (high_up - low_up),
                    -(low_down + generator.random(len(product_index)) * (high_down - low_down)))
    changes = pd.DataFrame({"product": product_index, "valid_from": change_dates, "factor": 1 + size,
                            "change_type": np.where(increase, "increase", "decrease")})
    changes = changes.sort_values(["product", "valid_from"], kind="stable")
    changes = changes[~changes.duplicated(["product", "valid_from"])].reset_index(drop=True)

    # Walk back from the current price: suffix = product of this and all later factors of the product, so the price
    # valid from a change is current × factor / suffix and the initial price is current / (all factors).
    current = product_data["sales_price_gross"].to_numpy(dtype=float)
    suffix = changes.iloc[::-1].groupby("product")["factor"].cumprod().iloc[::-1]
    changes["price"] = current[changes["product"].to_numpy()] * changes["factor"] / suffix
    total = np.ones(len(product_data))
    all_factors = changes.groupby("product")["factor"].prod()
    total[all_factors.index.to_numpy()] = all_factors.to_numpy()
    initial = pd.DataFrame({"product": np.arange(len(product_data)), "valid_from": first, "price": current / total,
                            "change_type": "initial"})

    rows = pd.concat([initial, changes[["product", "valid_from", "price", "change_type"]]], ignore_index=True)
    rows = rows.sort_values(["product", "valid_from"], kind="stable").reset_index(drop=True)
    product = rows["product"].to_numpy()
    rounded = np.array([d.round_to_9(price) for price in rows["price"].to_numpy()], dtype=float)
    is_last = rows["product"].ne(rows["product"].shift(-1)).to_numpy()
    rounded[is_last] = current[product[is_last]]
    net_ratio = (product_data["sales_price_net"] / product_data["sales_price_gross"]).to_numpy()

    history = pd.DataFrame({
        "product_id": product_data["product_id"].to_numpy()[product],
        "valid_from": pd.to_datetime(rows["valid_from"]).dt.normalize(),
        "sales_price_gross": rounded,
        "sales_price_net": np.round(rounded * net_ratio[product], 2),
        "change_type": rows["change_type"].to_numpy(),
    })
    next_from = history.groupby("product_id")["valid_from"].shift(-1)
    history["valid_to"] = next_from - pd.Timedelta(days=1)
    end_of_sale = history["product_id"].map(product_data.set_index("product_id")["discontinued_date"])
    history["valid_to"] = history["valid_to"].fillna(end_of_sale)
    return history[PRICE_HISTORY_COLUMNS]


def price_elasticity(category):
    return cs.category_price_elasticity.get(category, cs.default_price_elasticity)


class PriceBook:
    """Fast lookups of list prices and availability by (product, day index)."""

    def __init__(self, product_data, price_history, calendar):
        self.start = calendar["date"].iloc[0]
        self.days = len(calendar)
        products = product_data["product_id"].to_numpy()
        self.product_position = pd.Series(np.arange(len(products)), index=products)
        position = self.product_position.reindex(price_history["product_id"]).to_numpy()
        day = ((price_history["valid_from"] - self.start).dt.days).clip(lower=0).to_numpy()
        self.key = position.astype(np.int64) * (self.days + 10) + day
        order = np.argsort(self.key, kind="stable")
        self.key = self.key[order]
        self.gross = price_history["sales_price_gross"].to_numpy()[order]
        self.net = price_history["sales_price_net"].to_numpy()[order]
        launch = ((product_data["launch_date"] - self.start).dt.days).to_numpy()
        stop = ((product_data["discontinued_date"] - self.start).dt.days).fillna(self.days + 1).to_numpy()
        self.launch_day, self.stop_day = launch, stop
        lowest = price_history.groupby("product_id")["sales_price_gross"].min()
        self.lowest = lowest.reindex(products).to_numpy()
        self.elasticity = np.array([price_elasticity(c) for c in product_data["category"]])

    def positions(self, product_ids):
        return self.product_position.reindex(product_ids).to_numpy()

    def lookup(self, product_ids, days):
        """List gross and net price of each product on each day index."""
        position = self.positions(product_ids)
        query = position.astype(np.int64) * (self.days + 10) + np.asarray(days)
        index = np.searchsorted(self.key, query, side="right") - 1
        return self.gross[index], self.net[index]

    def available(self, product_ids, days):
        position = self.positions(product_ids)
        days = np.asarray(days)
        return (self.launch_day[position] <= days) & (days < self.stop_day[position])

    def acceptance(self, product_ids, days):
        """Chance to keep a drawn product: 0 when not on sale, else (price / lowest price) ** -elasticity."""
        gross, _ = self.lookup(product_ids, days)
        position = self.positions(product_ids)
        ratio = gross / self.lowest[position]
        return np.where(self.available(product_ids, days), ratio ** -self.elasticity[position], 0.0)
