"""
Markdowns, clearance and the outlet (Data Generator 1.9.0, off by default).

A shop manager marks down slow stock "by eye" once a week, and stock of a product about to be withdrawn gets a
clearance markdown; what is left on the withdrawal day goes to an outlet. The stock simulation in func/inventory.py
calls the MarkdownDesk every day. A markdown raises demand by (markdown price / regular price) ** -elasticity: for
every order line of the marked-down product, a Poisson number of other lines of the same day (of its category
first) switch to it, so the expected demand is the regular demand times true_uplift and the number of order lines stays as set.

All draws come from the "markdowns" stream; with markdowns off nothing is drawn and no table changes.
"""
import math

import numpy as np
import pandas as pd

import func.data as d
import func.prices as pr
import settings.inventory_settings as inv
import settings.market_settings as ms

MARKDOWN_COLUMNS = ["markdown_id", "product_id", "start_date", "end_date", "reason", "regular_price_gross",
                    "markdown_price_gross", "markdown_rate", "end_reason", "true_elasticity", "true_uplift"]
OUTLET_COLUMNS = ["outlet_sale_id", "product_id", "sale_date", "quantity", "unit_price_net", "revenue_net"]


def markdown_price(regular, rate):
    """The regular gross price lowered by rate, ending in ,99 and never above the lowered price."""
    target = regular * (1 - rate)
    price = math.floor(target) + 0.99
    if price > target + 1e-9:
        price -= 1
    return round(max(price, 0.99), 2)


class MarkdownDesk:
    """The manager's markdowns and the outlet, decided day by day inside the stock simulation."""

    def __init__(self, sim, product_data, price_book, line_fraud, generator):
        self.sim = sim
        self.generator = generator
        self.price_book = price_book
        count = len(sim.products)
        self.category = pd.factorize(product_data["category"])[0]
        self.elasticity = np.array([pr.price_elasticity(c) for c in product_data["category"]])
        self.unit_cost = product_data["net_purchase_price"].to_numpy(dtype=float)
        self.clearance_start = sim.stop_day - inv.clearance_days
        self.history = np.zeros((inv.markdown_history_days, count), dtype=np.int64)
        self.active = {}  # product position -> index of its open record
        self.cooldown_until = np.zeros(count, dtype=np.int64)
        values, p = d.get_param_list_and_normalized_probabilities(inv.clearance_rates)
        self.clearance_rate = np.asarray(values)[generator.choice(len(values), size=count, p=p)]
        self.line_fraud = np.asarray(line_fraud, dtype=bool)
        self.records = []
        self.outlet = []  # (day, product, quantity, unit price net)

    # -- daily hooks --------------------------------------------------------------------------------------------- #

    def in_clearance(self, t):
        return (self.clearance_start <= t) & (t < self.sim.stop_day)

    def start_of_day(self, t, stock, movements):
        """Send withdrawn stock to the outlet and open clearance markdowns for stock that is about to be withdrawn."""
        withdrawn = np.flatnonzero((self.sim.stop_day <= t) & (stock > 0))
        for p in withdrawn:
            if p in self.active:
                self.close(p, t - 1, "withdrawn")
            price = round(inv.outlet_recovery_rate * self.unit_cost[p], 2)
            self.outlet.append((t, p, int(stock[p]), price))
            movements.append((t, p, "outlet", -int(stock[p]), -1))
            stock[p] = 0
        for p in np.flatnonzero(self.in_clearance(t) & (stock > 0)):
            record = self.active.get(p)
            if record is not None and self.records[record]["reason"] == "clearance":
                continue
            if record is not None:
                self.close(p, t - 1, "clearance")
            self.open(p, t, self.clearance_rate[p], "clearance", self.sim.stop_day[p] - 1)

    def switch_lines(self, t, index):
        """
        Switch other lines of the day to the marked-down products: for every line of a product on markdown, a Poisson
        (true_uplift - 1) number of lines, not fraud and not of a marked-down product. Lines of the same category go
        first; when a small category runs out of lines that day, lines of other categories make up the rest.
        """
        if not self.active or not len(index):
            return
        product = self.sim.line_product[index]
        marked = np.array(sorted(self.active), dtype=np.int64)
        is_marked = np.isin(product, marked)
        taken = is_marked | self.line_fraud[index]
        for p in marked:
            natural = int((product == p).sum())
            if not natural:
                continue
            uplift = self.records[self.active[p]]["true_uplift"]
            extra = int(self.generator.poisson((uplift - 1) * natural))
            if not extra:
                continue
            same = np.flatnonzero(~taken & (self.category[product] == self.category[p]))
            chosen = self.generator.choice(same, size=min(extra, len(same)), replace=False)
            if len(chosen) < extra:
                other = np.flatnonzero(~taken & (self.category[product] != self.category[p]))
                more = self.generator.choice(other, size=min(extra - len(chosen), len(other)), replace=False)
                chosen = np.concatenate([chosen, more])
            if not len(chosen):
                continue
            self.sim.line_product[index[chosen]] = p
            taken[chosen] = True

    def end_of_day(self, t, stock, sold):
        """Record the day's sales and close markdowns that sold out or reached their planned end."""
        self.history[t % inv.markdown_history_days] = sold
        for p in list(self.active):
            record = self.records[self.active[p]]
            if stock[p] == 0:
                self.close(p, t, "sold_out")
            elif t >= record["planned_end"]:
                self.close(p, t, "withdrawn" if record["reason"] == "clearance" else "planned")

    def review(self, t, stock):
        """
        The weekly look at slow stock after the day's sales: products whose stock outlasts markdown_cover_days get a
        markdown from the next day on.
        """
        if self.sim.dates[t].weekday() != inv.markdown_review_weekday or t + 1 >= self.sim.days:
            return
        average = self.history.sum(axis=0) / inv.markdown_history_days
        with np.errstate(divide="ignore"):
            cover = np.where(average > 0, stock / np.maximum(average, 1e-12), np.inf)
        candidates = np.flatnonzero(
            (self.sim.launch_day <= t - inv.markdown_min_age_days) & (t + 1 < self.clearance_start)
            & (stock >= inv.markdown_min_stock) & (cover > inv.markdown_cover_days)
            & (self.cooldown_until <= t) & (t >= inv.markdown_history_days))
        candidates = np.array([p for p in candidates if p not in self.active], dtype=np.int64)
        if not len(candidates):
            return
        noticed = candidates[self.generator.random(len(candidates)) < inv.markdown_notice_rate]
        values, p_rate = d.get_param_list_and_normalized_probabilities(inv.markdown_rates)
        rates = np.asarray(values)[self.generator.choice(len(values), size=len(noticed), p=p_rate)]
        low, high = inv.markdown_days
        lengths = self.generator.integers(low, high + 1, size=len(noticed))
        for p, rate, length in zip(noticed, rates, lengths, strict=True):
            end = min(t + int(length), int(self.clearance_start[p]) - 1)
            self.open(p, t + 1, rate, "slow_stock", end)

    # -- records ------------------------------------------------------------------------------------------------- #

    def open(self, p, t, rate, reason, planned_end):
        regular, _ = self.price_book.lookup(np.array([self.sim.products[p]]), np.array([min(t, self.sim.days - 1)]))
        regular = float(regular[0])
        price = markdown_price(regular, float(rate))
        if price >= regular:
            return
        uplift = (price / regular) ** -self.elasticity[p]
        self.records.append({"product": p, "start": t, "end": None, "planned_end": int(planned_end),
                             "reason": reason, "regular": regular, "price": price,
                             "rate": round(1 - price / regular, 4), "end_reason": "ongoing",
                             "elasticity": float(self.elasticity[p]), "true_uplift": round(float(uplift), 4)})
        self.active[p] = len(self.records) - 1

    def close(self, p, t, reason):
        record = self.records[self.active.pop(p)]
        if t < record["start"]:  # opened and closed on the same morning: drop the empty markdown
            record["end_reason"] = "dropped"
            return
        record["end"], record["end_reason"] = t, reason
        self.cooldown_until[p] = t + 1 + inv.markdown_cooldown_days

    # -- tables -------------------------------------------------------------------------------------------------- #

    def markdown_frame(self):
        records = [r for r in self.records if r["end_reason"] != "dropped"]
        if not records:
            return empty_markdowns()
        start = self.sim.dates[0]
        raw = pd.DataFrame(records).sort_values(["start", "product"], kind="stable")
        end = raw["end"].astype("float").to_numpy()
        frame = pd.DataFrame({
            "markdown_id": np.arange(1, len(raw) + 1),
            "product_id": self.sim.products[raw["product"].to_numpy()],
            "start_date": start + pd.to_timedelta(raw["start"].to_numpy(), unit="D"),
            "end_date": pd.Series(start + pd.to_timedelta(np.nan_to_num(end), unit="D")).where(~np.isnan(end)),
            "reason": raw["reason"].to_numpy(),
            "regular_price_gross": raw["regular"].to_numpy(),
            "markdown_price_gross": raw["price"].to_numpy(),
            "markdown_rate": raw["rate"].to_numpy(),
            "end_reason": raw["end_reason"].to_numpy(),
            "true_elasticity": raw["elasticity"].to_numpy(),
            "true_uplift": raw["true_uplift"].to_numpy(),
        })
        return frame[MARKDOWN_COLUMNS].reset_index(drop=True)

    def outlet_frame(self):
        if not self.outlet:
            return empty_outlet()
        raw = pd.DataFrame(self.outlet, columns=["day", "product", "quantity", "price"])
        raw = raw.sort_values(["day", "product"], kind="stable")
        frame = pd.DataFrame({
            "outlet_sale_id": np.arange(1, len(raw) + 1),
            "product_id": self.sim.products[raw["product"].to_numpy()],
            "sale_date": self.sim.dates[0] + pd.to_timedelta(raw["day"].to_numpy(), unit="D"),
            "quantity": raw["quantity"].to_numpy().astype(np.int64),
            "unit_price_net": raw["price"].to_numpy(),
            "revenue_net": np.round(raw["quantity"].to_numpy() * raw["price"].to_numpy(), 2),
        })
        return frame[OUTLET_COLUMNS]


def empty_markdowns():
    return pd.DataFrame({
        "markdown_id": pd.Series(dtype="int64"), "product_id": pd.Series(dtype="int64"),
        "start_date": pd.Series(dtype="datetime64[ns]"), "end_date": pd.Series(dtype="datetime64[ns]"),
        "reason": pd.Series(dtype="object"), "regular_price_gross": pd.Series(dtype="float64"),
        "markdown_price_gross": pd.Series(dtype="float64"), "markdown_rate": pd.Series(dtype="float64"),
        "end_reason": pd.Series(dtype="object"), "true_elasticity": pd.Series(dtype="float64"),
        "true_uplift": pd.Series(dtype="float64"),
    })[MARKDOWN_COLUMNS]


def empty_outlet():
    return pd.DataFrame({
        "outlet_sale_id": pd.Series(dtype="int64"), "product_id": pd.Series(dtype="int64"),
        "sale_date": pd.Series(dtype="datetime64[ns]"), "quantity": pd.Series(dtype="int64"),
        "unit_price_net": pd.Series(dtype="float64"), "revenue_net": pd.Series(dtype="float64"),
    })[OUTLET_COLUMNS]


def add_markdowns_to_price_history(price_history, markdown_data, product_data):
    """
    Cut the markdown periods into the list price history: a "markdown" row for each markdown and a "markdown_end"
    row when the regular price comes back. Products without markdowns keep their rows as they were.
    """
    if markdown_data.empty:
        return price_history
    end_of_period = pd.Timestamp(pr.period()[1])
    marked = set(markdown_data["product_id"])
    keep = price_history[~price_history["product_id"].isin(marked)]
    rows = []
    by_product = markdown_data.groupby("product_id")
    for product_id, regular in price_history[price_history["product_id"].isin(marked)].groupby("product_id",
                                                                                                sort=False):
        regular = regular.sort_values("valid_from")
        last_day = regular["valid_to"].iloc[-1]
        last_day = end_of_period if pd.isna(last_day) else last_day
        markdowns = by_product.get_group(product_id).sort_values("start_date")
        cuts = set(regular["valid_from"])
        cuts |= set(markdowns["start_date"])
        ends = markdowns["end_date"].fillna(end_of_period) + pd.Timedelta(days=1)
        cuts |= {day for day in ends if day <= last_day}
        cuts = sorted(cuts)
        regular_from = regular["valid_from"].to_numpy()
        markdown_ends = set(ends)
        for day in cuts:
            inside = markdowns[(markdowns["start_date"] <= day)
                               & (markdowns["end_date"].fillna(end_of_period) >= day)]
            if len(inside):
                row = inside.iloc[0]
                kind = "markdown" if day == row["start_date"] else "markdown_continued"
                price = float(row["markdown_price_gross"])
            else:
                position = int(np.searchsorted(regular_from, np.datetime64(day), side="right") - 1)
                price = float(regular["sales_price_gross"].iloc[position])
                kind = "markdown_end" if day in markdown_ends else regular["change_type"].iloc[position]
            rows.append((product_id, day, price, kind))
    merged = pd.DataFrame(rows, columns=["product_id", "valid_from", "sales_price_gross", "change_type"])
    # A regular change inside a markdown does not show: drop rows that repeat the markdown price.
    merged = merged[merged["change_type"] != "markdown_continued"]
    merged["sales_price_net"] = (merged["sales_price_gross"] / (1 + ms.vat_rate)).round(2)
    history = pd.concat([keep, merged], ignore_index=True)
    order = history["product_id"].map(pd.Series(np.arange(len(product_data)), index=product_data["product_id"]))
    history = history.assign(_order=order).sort_values(["_order", "valid_from"], kind="stable").drop(columns="_order")
    next_from = history.groupby("product_id")["valid_from"].shift(-1)
    history["valid_to"] = next_from - pd.Timedelta(days=1)
    end_of_sale = history["product_id"].map(product_data.set_index("product_id")["discontinued_date"])
    history["valid_to"] = history["valid_to"].fillna(end_of_sale)
    return history[pr.PRICE_HISTORY_COLUMNS].reset_index(drop=True)
