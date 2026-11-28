"""
Suppliers, purchase orders and stock.

Every product gets one supplier (by category and brand) with a pack size and a minimum order. A buyer orders "by eye"
on the supplier's order days (settings/inventory_settings.py), deliveries arrive after a random lead time, and the
stock goes down on the order day of every order line. With stockouts off, an express delivery covers an empty shelf,
so the order lines stay as they are; with stockouts on, a line that does not fit the stock is lost and kept in
lost_demand_data.

All draws come from the "inventory" stream, so the other tables do not change unless stockouts is on.
"""
import numpy as np
import pandas as pd

import func.data as d
import settings.inventory_settings as inv

SUPPLIER_COLUMNS = ["supplier_id", "supplier_name", "country", "order_weekdays", "promised_lead_time_days",
                    "true_lead_time_mean_days", "true_lead_time_cv"]
PRODUCT_SUPPLIER_COLUMNS = ["product_id", "supplier_id", "pack_size", "min_order_quantity"]
PURCHASE_ORDER_COLUMNS = ["purchase_order_id", "purchase_order_line_id", "supplier_id", "product_id", "order_date",
                          "ordered_quantity", "promised_date", "received_date", "received_quantity", "unit_cost_net",
                          "is_express"]
MOVEMENT_COLUMNS = ["stock_movement_id", "product_id", "movement_date", "movement_type", "quantity", "stock_after",
                    "purchase_order_line_id"]
LOST_DEMAND_COLUMNS = ["lost_line_id", "order_date", "order_datetime", "customer_id", "product_id", "quantity",
                       "unit_price_gross", "discount_rate", "lost_revenue_gross", "channel", "session_id"]
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MOVEMENT_ORDER = {"opening": 0, "receipt": 1, "sale": 2, "outlet": 3}
FIRST_SUPPLIER_ID = 1

# Invented company names (no real firms), one per supplier; the legal form follows the country.
NAME_STEMS = ["Arvena", "Borvik", "Calmeta", "Dravio", "Elkora", "Fenmar", "Galvio", "Hartla", "Istrena", "Jorvel",
              "Kalvena", "Lumira", "Morvant", "Nestria", "Olvaro", "Prestil", "Quarvo", "Rendal", "Sorvia", "Tavrel",
              "Ulmera", "Valtrix", "Wendor", "Xarvel", "Yorvana", "Zelmar", "Altrea", "Brenvo", "Korvenna", "Delmira",
              "Estrol", "Farvion", "Gorvane", "Helvra", "Irvana", "Kelvaro"]
NAME_SUFFIX = {"PL": ["Dystrybucja Sp. z o.o.", "Hurt Sp. z o.o.", "Trade Sp. j."], "DE": ["Handels GmbH", "GmbH"],
               "CN": ["Trading Co., Ltd.", "Industrial Co., Ltd."]}


def draw(probabilities, generator, size):
    values, p = d.get_param_list_and_normalized_probabilities(probabilities)
    return np.asarray(values)[generator.choice(len(values), size=size, p=p)]


def build_suppliers(product_data, generator):
    """
    Suppliers and the supplier of every product.

    Each category gets suppliers_per_category suppliers; its brands are dealt among them at random, so a brand comes
    from one supplier within a category. Returns (supplier_data, product_supplier_data).
    """
    categories = sorted(product_data["category"].unique())
    counts = [inv.suppliers_per_category.get(category, 1) for category in categories]
    total = sum(counts)
    if total > len(NAME_STEMS):
        raise ValueError(f"At most {len(NAME_STEMS)} suppliers are supported (got {total}).")

    origins = list(inv.supplier_origins)
    country = draw({o: inv.supplier_origins[o]["share"] for o in origins}, generator, total)
    low = np.array([inv.supplier_origins[c]["lead_time_days"][0] for c in country], dtype=float)
    high = np.array([inv.supplier_origins[c]["lead_time_days"][1] for c in country], dtype=float)
    mean_lead = np.round(generator.uniform(low, high), 1)
    cv = np.round(generator.uniform(*inv.lead_time_cv, size=total), 2)
    weekday_count = draw(inv.order_weekday_count, generator, total)
    weekdays = [",".join(WEEKDAY_NAMES[day] for day in sorted(generator.choice(5, size=int(n), replace=False)))
                for n in weekday_count]
    stems = generator.permutation(NAME_STEMS)[:total]
    names = [f"{stem} {NAME_SUFFIX[c][int(generator.integers(len(NAME_SUFFIX[c])))]}"
             for stem, c in zip(stems, country, strict=True)]
    supplier_data = pd.DataFrame({
        "supplier_id": np.arange(FIRST_SUPPLIER_ID, FIRST_SUPPLIER_ID + total),
        "supplier_name": names,
        "country": country,
        "order_weekdays": weekdays,
        "promised_lead_time_days": np.maximum(1, np.round(mean_lead)).astype(int),
        "true_lead_time_mean_days": mean_lead,
        "true_lead_time_cv": cv,
    })[SUPPLIER_COLUMNS]

    # Deal the brands of every category among its suppliers.
    supplier_of_pair = {}
    first = FIRST_SUPPLIER_ID
    for category, count in zip(categories, counts, strict=True):
        brands = sorted(product_data.loc[product_data["category"] == category, "brand"].astype(str).unique())
        owners = generator.integers(0, count, size=len(brands))
        owners[:min(count, len(brands))] = np.arange(min(count, len(brands)))  # every supplier gets a brand
        for brand, owner in zip(generator.permutation(brands), owners, strict=True):
            supplier_of_pair[(category, brand)] = first + int(owner)
        first += count

    pairs = zip(product_data["category"], product_data["brand"].astype(str), strict=True)
    supplier_id = np.array([supplier_of_pair[pair] for pair in pairs])
    pack = np.ones(len(product_data), dtype=int)
    for category, rows in product_data.groupby("category").indices.items():
        pack[rows] = draw(inv.pack_sizes.get(category, inv.default_pack_sizes), generator, len(rows))
    packs = draw(inv.min_order_packs, generator, len(product_data)).astype(int)
    product_supplier_data = pd.DataFrame({
        "product_id": product_data["product_id"].to_numpy(),
        "supplier_id": supplier_id,
        "pack_size": pack,
        "min_order_quantity": pack * packs,
    })[PRODUCT_SUPPLIER_COLUMNS]
    return supplier_data, product_supplier_data


def lead_time_sigma(cv):
    """Log-normal sigma that gives the coefficient of variation cv."""
    return np.sqrt(np.log1p(np.asarray(cv, dtype=float) ** 2))


def draw_lead_times(mean, cv, generator):
    """Actual lead times in whole days (at least 1) around the mean, log-normal with the given spread."""
    sigma = lead_time_sigma(cv)
    mu = np.log(mean) - sigma ** 2 / 2
    return np.maximum(1, np.round(np.exp(mu + sigma * generator.standard_normal(np.shape(mean))))).astype(int)


def round_up_to_pack(quantity, pack):
    return (np.ceil(np.maximum(quantity, 0) / pack) * pack).astype(int)


class Simulation:
    """Day-by-day stock of every product: receipts, sales (or lost lines) and the buyer's orders."""

    def __init__(self, order_data, product_data, supplier_data, product_supplier_data, dates, generator, stockouts,
                 clearance_days=0):
        self.generator = generator
        self.stockouts = stockouts
        self.clearance_days = clearance_days
        self.desk = None  # func.markdowns.MarkdownDesk with markdowns on
        self.dates = pd.DatetimeIndex(dates)
        self.days = len(self.dates)
        self.products = product_data["product_id"].to_numpy()
        self.position = pd.Series(np.arange(len(self.products)), index=self.products)
        supply = product_supplier_data.set_index("product_id").reindex(self.products)
        suppliers = supplier_data.set_index("supplier_id")
        self.supplier_ids = suppliers.index.to_numpy()
        supplier_position = pd.Series(np.arange(len(self.supplier_ids)), index=self.supplier_ids)
        self.product_supplier = supplier_position.reindex(supply["supplier_id"]).to_numpy()
        self.pack = supply["pack_size"].to_numpy()
        self.moq = supply["min_order_quantity"].to_numpy()
        self.unit_cost = product_data["net_purchase_price"].to_numpy()
        self.promised = suppliers["promised_lead_time_days"].to_numpy()
        self.mean_lead = suppliers["true_lead_time_mean_days"].to_numpy()
        self.cv = suppliers["true_lead_time_cv"].to_numpy()
        order_days = [set(WEEKDAY_NAMES.index(day) for day in text.split(",")) for text in suppliers["order_weekdays"]]
        self.orders_on = np.array([[weekday in days for weekday in range(7)] for days in order_days])
        self.review = 7 / self.orders_on.sum(axis=1)

        start = self.dates[0]
        launch = ((product_data["launch_date"] - start).dt.days).to_numpy()
        self.launch_day = np.clip(launch, 0, None)
        self.launched_before = launch <= 0
        stop = ((product_data["discontinued_date"] - start).dt.days).to_numpy(dtype=float)
        self.stop_day = np.where(np.isnan(stop), self.days + 10_000, stop).astype(int)

        # Order lines sorted by day, product and time: lines of one product on one day are served first come first.
        day = (order_data["order_date"] - start).dt.days.to_numpy()
        when = order_data["order_datetime"].to_numpy() if "order_datetime" in order_data else order_data[
            "order_date"].to_numpy()
        self.line_product = self.position.reindex(order_data["product_id"]).to_numpy()
        self.line_quantity = order_data["quantity"].to_numpy().astype(np.int64)
        self.line_when = when
        self.line_order = np.lexsort((np.arange(len(day)), when, self.line_product, day))
        self.line_day = day[self.line_order]
        self.day_start = np.searchsorted(self.line_day, np.arange(self.days + 1))

    def guess(self, cover_low, cover_high, first_day):
        """The buyer's guess of sales over a cover drawn per product from its first day on, at least one pack."""
        cover = self.generator.integers(cover_low, cover_high + 1, size=len(self.products))
        units = np.zeros(len(self.products))
        sorted_product = self.line_product[self.line_order]
        sorted_quantity = self.line_quantity[self.line_order]
        window = (self.line_day >= first_day[sorted_product]) & (self.line_day < first_day[sorted_product]
                                                                 + cover[sorted_product])
        np.add.at(units, sorted_product[window], sorted_quantity[window])
        noise = np.exp(self.generator.normal(0, 0.3, size=len(self.products)))
        return np.maximum(round_up_to_pack(units * noise, self.pack), self.pack)

    def run(self):
        count = len(self.products)
        stock = np.zeros(count, dtype=np.int64)
        on_order = np.zeros(count, dtype=np.int64)
        history = np.zeros((inv.buyer_history_days, count), dtype=np.int64)
        served_lines = np.ones(len(self.line_quantity), dtype=bool)
        arrivals = {}
        movements = []  # (day, product, type, quantity, po line)
        po_lines = []  # (supplier, product, order day, quantity, promised day, arrival day, express)

        # Opening stock and the first delivery of products launched later.
        opening = self.guess(*inv.opening_cover_days, self.launch_day)
        before = np.flatnonzero(self.launched_before & (self.stop_day > 0))
        stock[before] = opening[before]
        movements += [(0, p, "opening", int(opening[p]), -1) for p in before]
        later = np.flatnonzero(~self.launched_before & (self.launch_day < self.days))
        first_delivery = self.guess(*inv.launch_cover_days, self.launch_day)
        lead = draw_lead_times(self.mean_lead[self.product_supplier[later]], self.cv[self.product_supplier[later]],
                               self.generator)
        for p, lt in zip(later, lead, strict=True):
            arrive = int(self.launch_day[p])
            if (self.dates[0] + pd.Timedelta(days=arrive)).weekday() == 6:
                arrive -= 1  # no deliveries on Sunday: the first delivery comes the day before the launch
            s = self.product_supplier[p]
            po_lines.append((s, p, arrive - int(lt), int(first_delivery[p]), arrive - int(lt) + int(self.promised[s]),
                             arrive, False))
            arrivals.setdefault(arrive, []).append((p, int(first_delivery[p]), len(po_lines) - 1))
            on_order[p] += first_delivery[p]

        for t in range(self.days):
            for p, quantity, line in arrivals.pop(t, []):
                stock[p] += quantity
                on_order[p] -= quantity
                movements.append((t, p, "receipt", quantity, line))

            lo, hi = self.day_start[t], self.day_start[t + 1]
            if self.desk is not None:
                self.desk.start_of_day(t, stock, movements)
                if hi > lo:
                    index = self.line_order[lo:hi]
                    self.desk.switch_lines(t, index)
                    product = self.line_product[index]
                    self.line_order[lo:hi] = index[np.lexsort((index, self.line_when[index], product))]
            sold = np.zeros(count, dtype=np.int64)
            if hi > lo:
                index = self.line_order[lo:hi]
                product = self.line_product[index]
                quantity = self.line_quantity[index]
                np.add.at(sold, product, quantity)
                if self.stockouts:
                    # Products with enough stock serve every line; the others serve lines first come first while
                    # they fit, and a line that does not fit is lost (a later, smaller one may still fit).
                    for position in np.flatnonzero(sold[product] > stock[product]):
                        p = product[position]
                        if sold[p] > stock[p]:
                            sold[p], left = 0, stock[p]
                            for k in np.flatnonzero(product == p):
                                if quantity[k] <= left:
                                    left -= quantity[k]
                                    sold[p] += quantity[k]
                                else:
                                    served_lines[index[k]] = False
                else:
                    short = np.flatnonzero(sold > stock)
                    if len(short):
                        express = round_up_to_pack(sold[short] - stock[short], self.pack[short])
                        for p, q in zip(short, express, strict=True):
                            s = self.product_supplier[p]
                            po_lines.append((s, p, t, int(q), t, t, True))
                            movements.append((t, p, "receipt", int(q), len(po_lines) - 1))
                        stock[short] += express
                stock -= sold
                sold_products = np.flatnonzero(sold)
                movements += [(t, p, "sale", -int(sold[p]), -1) for p in sold_products]
            history[t % inv.buyer_history_days] = sold
            if self.desk is not None:
                self.desk.end_of_day(t, stock, sold)
                self.desk.review(t, stock)
            self.buy(t, stock, on_order, history, arrivals, po_lines)

        return served_lines, movements, po_lines

    def buy(self, t, stock, on_order, history, arrivals, po_lines):
        """The buyer's orders at the end of day t for the suppliers that take orders on this weekday."""
        ordering = np.flatnonzero(self.orders_on[:, self.dates[t].weekday()])
        if not len(ordering):
            return
        supplier = self.product_supplier
        promised, review = self.promised[supplier], self.review[supplier]
        active = (np.isin(supplier, ordering) & (self.launch_day <= t)
                  & (t + promised + review < self.stop_day - self.clearance_days))
        if not active.any():
            return
        seen = np.minimum(inv.buyer_history_days, t - self.launch_day + 1).clip(1)
        average = history.sum(axis=0) / seen
        noise = np.exp(self.generator.normal(0, inv.buyer_quantity_sigma, size=len(stock)))
        target = average * (promised + review + inv.buyer_cover_days) * noise
        position = stock + on_order
        need = np.where(active & (average > 0) & (position < target), target - position, 0)
        empty = (active & (average == 0) & (position == 0)
                 & (self.generator.random(len(stock)) < inv.empty_shelf_notice_rate))
        quantity = np.where(need > 0, np.maximum(round_up_to_pack(need, self.pack), self.moq), 0)
        quantity = np.where(empty, self.moq, quantity)
        products = np.flatnonzero(quantity)
        if not len(products):
            return
        lead = draw_lead_times(self.mean_lead[ordering], self.cv[ordering], self.generator)
        arrival = dict(zip(ordering, lead, strict=True))
        for p in products:
            s = supplier[p]
            arrive = t + int(arrival[s])
            if (self.dates[0] + pd.Timedelta(days=arrive)).weekday() == 6:
                arrive += 1  # no deliveries on Sunday
            po_lines.append((s, p, t, int(quantity[p]), t + int(self.promised[s]), arrive, False))
            arrivals.setdefault(arrive, []).append((p, int(quantity[p]), len(po_lines) - 1))
            on_order[p] += quantity[p]


def build_inventory(order_data, product_data, dates, generator, stockouts=None, price_book=None,
                    markdown_generator=None, markdowns=None):
    """
    Suppliers, purchase orders, stock movements and the order lines the stock could serve.

    Parameters:
    order_data (pd.DataFrame): Order lines with order_date (and order_datetime when present), product_id, quantity.
    product_data (pd.DataFrame): Products with category, brand, net_purchase_price, launch_date, discontinued_date.
    dates (sequence): Every day of the period, in order.
    generator (np.random.Generator): The "inventory" stream.
    stockouts (bool, optional): Lose lines that do not fit the stock; defaults to inventory_settings.stockouts.
    price_book (func.prices.PriceBook, optional): Regular list prices; needed with markdowns on.
    markdown_generator (np.random.Generator, optional): The "markdowns" stream; needed with markdowns on.
    markdowns (bool, optional): Markdowns, clearance and the outlet; defaults to inventory_settings.markdowns.

    Returns:
    dict: supplier_data, product_supplier_data, purchase_order_data, stock_movement_data, served (a boolean array
    over the rows of order_data: False for a lost line) and, with markdowns on, product_id (the product of every
    row of order_data after the markdowns took their lines), markdown_data and outlet_data.
    """
    stockouts = inv.stockouts if stockouts is None else stockouts
    markdowns = inv.markdowns if markdowns is None else markdowns
    if markdowns and not stockouts:
        raise ValueError("markdowns needs stockouts = True: a sold-out markdown is not refilled by express delivery.")
    supplier_data, product_supplier_data = build_suppliers(product_data, generator)
    sim = Simulation(order_data, product_data, supplier_data, product_supplier_data, dates, generator, stockouts,
                     inv.clearance_days if markdowns else 0)
    if markdowns:
        from func.markdowns import MarkdownDesk
        fraud = order_data["is_fraud"].to_numpy() if "is_fraud" in order_data else np.zeros(len(order_data), bool)
        sim.desk = MarkdownDesk(sim, product_data, price_book, fraud, markdown_generator)
    served, movements, po_lines = sim.run()
    purchase_orders, line_ids = purchase_order_frame(po_lines, sim)
    result = {
        "supplier_data": supplier_data,
        "product_supplier_data": product_supplier_data,
        "purchase_order_data": purchase_orders,
        "stock_movement_data": movement_frame(movements, sim, line_ids),
        "served": served,
    }
    if markdowns:
        result["product_id"] = sim.products[sim.line_product]
        result["markdown_data"] = sim.desk.markdown_frame()
        result["outlet_data"] = sim.desk.outlet_frame()
    return result


def purchase_order_frame(po_lines, sim):
    """One row per purchase order line; lines of one supplier, day and kind (express or not) share an order."""
    if not po_lines:
        return pd.DataFrame(columns=PURCHASE_ORDER_COLUMNS), np.array([], dtype=int)
    raw = pd.DataFrame(po_lines, columns=["supplier", "product", "order_day", "quantity", "promised_day",
                                          "arrival_day", "is_express"])
    raw["raw_line"] = np.arange(len(raw))
    raw = raw.sort_values(["order_day", "supplier", "is_express", "product", "raw_line"], kind="stable")
    new_order = (raw[["order_day", "supplier", "is_express"]] != raw[["order_day", "supplier", "is_express"]].shift()
                 ).any(axis=1)
    start = sim.dates[0]
    received = raw["arrival_day"].to_numpy() < sim.days
    frame = pd.DataFrame({
        "purchase_order_id": new_order.cumsum().to_numpy(),
        "purchase_order_line_id": np.arange(1, len(raw) + 1),
        "supplier_id": sim.supplier_ids[raw["supplier"].to_numpy()],
        "product_id": sim.products[raw["product"].to_numpy()],
        "order_date": start + pd.to_timedelta(raw["order_day"].to_numpy(), unit="D"),
        "ordered_quantity": raw["quantity"].to_numpy(),
        "promised_date": start + pd.to_timedelta(raw["promised_day"].to_numpy(), unit="D"),
        "received_date": (start + pd.to_timedelta(raw["arrival_day"].to_numpy(), unit="D")).where(received),
        "received_quantity": pd.array(np.where(received, raw["quantity"].to_numpy(), 0), dtype="Int64"),
        "unit_cost_net": sim.unit_cost[raw["product"].to_numpy()],
        "is_express": raw["is_express"].to_numpy(),
    })
    frame.loc[~received, "received_quantity"] = pd.NA
    line_ids = np.empty(len(raw), dtype=int)
    line_ids[raw["raw_line"].to_numpy()] = frame["purchase_order_line_id"].to_numpy()
    return frame[PURCHASE_ORDER_COLUMNS], line_ids


def movement_frame(movements, sim, line_ids):
    """Stock movements with the stock after each one, oldest first."""
    raw = pd.DataFrame(movements, columns=["day", "product", "movement_type", "quantity", "raw_line"])
    raw["kind"] = raw["movement_type"].map(MOVEMENT_ORDER)
    raw = raw.sort_values(["product", "day", "kind"], kind="stable")
    raw["stock_after"] = raw.groupby("product")["quantity"].cumsum()
    raw = raw.sort_values(["day", "product", "kind"], kind="stable")
    po_line = np.where(raw["raw_line"].to_numpy() >= 0, line_ids[raw["raw_line"].clip(lower=0).to_numpy()]
                       if len(line_ids) else 0, -1)
    frame = pd.DataFrame({
        "stock_movement_id": np.arange(1, len(raw) + 1),
        "product_id": sim.products[raw["product"].to_numpy()],
        "movement_date": sim.dates[0] + pd.to_timedelta(raw["day"].to_numpy(), unit="D"),
        "movement_type": raw["movement_type"].to_numpy(),
        "quantity": raw["quantity"].to_numpy().astype(np.int64),
        "stock_after": raw["stock_after"].to_numpy().astype(np.int64),
        "purchase_order_line_id": pd.array(np.where(po_line >= 0, po_line, 0), dtype="Int64"),
    })
    frame.loc[po_line < 0, "purchase_order_line_id"] = pd.NA
    return frame[MOVEMENT_COLUMNS]


def empty_lost_demand():
    return pd.DataFrame({
        "lost_line_id": pd.Series(dtype="int64"), "order_date": pd.Series(dtype="datetime64[ns]"),
        "order_datetime": pd.Series(dtype="datetime64[ns]"), "customer_id": pd.Series(dtype="int64"),
        "product_id": pd.Series(dtype="int64"), "quantity": pd.Series(dtype="int64"),
        "unit_price_gross": pd.Series(dtype="float64"), "discount_rate": pd.Series(dtype="float64"),
        "lost_revenue_gross": pd.Series(dtype="float64"), "channel": pd.Series(dtype="object"),
        "session_id": pd.Series(dtype="Int64"),
    })[LOST_DEMAND_COLUMNS]


def remove_lost_lines(order_data, session_data, served, price_book, renumber):
    """
    Take the lost lines out of order_data and keep them in lost_demand_data; sessions whose whole order was lost keep
    no order. Orders are numbered again, so IDs stay consecutive.

    Returns:
    tuple: (order lines, sessions, lost_demand_data).
    """
    if served.all():
        return order_data, session_data, empty_lost_demand()
    lost = order_data.loc[~served].copy()
    days = (lost["order_date"] - price_book.start).dt.days.clip(0, price_book.days - 1).to_numpy()
    gross, _ = price_book.lookup(lost["product_id"].to_numpy(), days)
    lost_demand = pd.DataFrame({
        "lost_line_id": np.arange(1, len(lost) + 1),
        "order_date": lost["order_date"].to_numpy(),
        "order_datetime": lost["order_datetime"].to_numpy(),
        "customer_id": lost["customer_id"].to_numpy(),
        "product_id": lost["product_id"].to_numpy(),
        "quantity": lost["quantity"].to_numpy(),
        "unit_price_gross": gross,
        "discount_rate": lost["discount_rate"].to_numpy(),
        "lost_revenue_gross": np.round(lost["quantity"].to_numpy() * gross * (1 - lost["discount_rate"].to_numpy()), 2),
        "channel": lost["channel"].to_numpy(),
        "session_id": pd.array(lost["session_id"].to_numpy(), dtype="Int64"),
    }).sort_values(["order_datetime", "lost_line_id"], kind="stable")
    lost_demand["lost_line_id"] = np.arange(1, len(lost_demand) + 1)

    kept = order_data.loc[served].copy()
    kept["_old_order_id"] = kept["order_id"].to_numpy()
    kept = renumber(kept)
    mapping = kept.drop_duplicates("_old_order_id").set_index("_old_order_id")["order_id"]
    kept = kept.drop(columns="_old_order_id")
    session_data = session_data.copy()
    session_data["order_id"] = pd.array(session_data["order_id"].map(mapping), dtype="Int64")
    return kept, session_data, lost_demand[LOST_DEMAND_COLUMNS].reset_index(drop=True)
