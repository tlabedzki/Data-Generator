"""
List prices of the same products at five fictional competing shops (competitor_prices).

The table only adds data: competitor prices never change demand, orders or any other table, and they draw from their
own random stream. The market price of a product comes from its cost (see market_reference), so our own price lands
above the market for some products and below it for others. settings.market_settings, section Competitor prices,
holds every shop's strategy and its true price level. The flash sale shop also runs short, deep sales; its sale
prices are flagged in is_promotion and its true price level is the regular price outside sales.
"""
import numpy as np
import pandas as pd

import settings.market_settings as ms
from func import calendar, prices

COMPETITOR_COLUMNS = ["competitor_price_id", "product_id", "competitor_id", "competitor_name", "valid_from", "valid_to",
                      "price_gross", "price_net", "change_type", "is_promotion", "competitor_strategy",
                      "true_price_level", "true_market_price_gross"]
CHEAP_PRICE_GROSS = 20


def market_reference(product_data):
    """
    Net market price of every product: net_purchase_price times the median sales_price_net / net_purchase_price of
    its product type, or of its category when the type has fewer than competitor_reference_min_products products.

    Parameters:
    product_data (pd.DataFrame): Clean products (before data quality issues).

    Returns:
    pd.Series: Net market price in PLN, with the index of product_data.
    """
    markup = product_data["sales_price_net"] / product_data["net_purchase_price"]
    by_type = markup.groupby(product_data["product_type"]).transform("median")
    by_category = markup.groupby(product_data["category"]).transform("median")
    type_size = product_data.groupby("product_type")["product_id"].transform("size")
    median_markup = by_type.where(type_size >= ms.competitor_reference_min_products, by_category)
    return product_data["net_purchase_price"] * median_markup


def round_price(price, ending):
    """Round gross prices to the shop's ending: "99" = nearest x.99, "9" = nearest whole price ending in 9."""
    price = np.asarray(price, dtype=float)
    to_99 = np.maximum(np.round(price + 0.01), 1) - 0.01
    if ending == "99":
        return np.round(to_99, 2)
    if ending == "9":
        to_9 = np.maximum(np.round((price + 1) / 10), 1) * 10 - 1
        return np.round(np.where(price < CHEAP_PRICE_GROSS, to_99, to_9), 2)
    raise ValueError(f"Unsupported price_ending: {ending}. Use '99' or '9'.")


def selling_period(product_data):
    """First and last day every product is on sale inside the period, and the number of days between them."""
    start, end = prices.period()
    first = np.maximum(product_data["launch_date"].to_numpy(), np.datetime64(start))
    last = product_data["discontinued_date"].fillna(end).to_numpy()
    span_days = np.maximum((last - first).astype("timedelta64[D]").astype(int), 0)
    return first, last, span_days


def random_shop_prices(shop, covered, anchor, first, span_days, generator):
    """
    Price periods of a shop that changes prices at random: every change draws a new short-term deviation around the
    shop's lasting price (anchor), so the shop stays at its price level for the whole period.

    Returns:
    tuple: Product positions, valid_from dates and unrounded gross prices, oldest first per product.
    """
    rate = shop["changes_per_year"] * span_days / 365
    counts = generator.poisson(rate) * covered
    change_product = np.repeat(np.arange(len(anchor)), counts)
    offsets = (generator.random(len(change_product)) * np.maximum(span_days[change_product], 1)).astype(int) + 1
    initial_product = np.flatnonzero(covered)
    product = np.concatenate([initial_product, change_product])
    valid_from = np.concatenate([first[initial_product], first[change_product] + offsets.astype("timedelta64[D]")])
    deviation = np.maximum(1 + shop["change_sd"] * generator.standard_normal(len(product)), 0.5)
    return product, valid_from, anchor[product] * deviation


def matcher_prices(shop, covered, anchor, product_data, price_history, last, generator):
    """
    Price periods of the matcher: it follows our list price changes (price_history) by the same ratio, with
    reaction_probability, reaction_delay_days later. Its price on the last day of sale is the anchor; earlier
    prices are walked back from it, as in price_history.

    Returns:
    tuple: Product positions, valid_from dates and unrounded gross prices, oldest first per product.
    """
    position = pd.Series(np.arange(len(product_data)), index=product_data["product_id"].to_numpy())
    history = price_history[["product_id", "valid_from", "sales_price_gross"]]
    ratio = (history["sales_price_gross"] / history.groupby("product_id")["sales_price_gross"].shift(1)).to_numpy()
    changed = ~np.isnan(ratio)
    low, high = shop["reaction_delay_days"]
    reacts = generator.random(len(history)) < shop["reaction_probability"]
    delay = generator.integers(low, high + 1, size=len(history))

    product = position.reindex(history["product_id"]).to_numpy()
    date = (history["valid_from"].to_numpy() + delay.astype("timedelta64[D]")).astype("datetime64[ns]")
    keep = changed & reacts & covered[product] & (date <= last[product])
    changes = pd.DataFrame({"product": product[keep], "valid_from": date[keep], "factor": ratio[keep]})
    changes = changes.groupby(["product", "valid_from"], as_index=False, sort=True)["factor"].prod()

    # Walk back from the last price: the price valid from a change is anchor / (product of all later factors).
    later = changes.iloc[::-1].groupby("product")["factor"].cumprod().iloc[::-1] / changes["factor"]
    total = np.ones(len(anchor))
    all_factors = changes.groupby("product")["factor"].prod()
    total[all_factors.index.to_numpy()] = all_factors.to_numpy()
    initial_product = np.flatnonzero(covered)
    first, _, _ = selling_period(product_data)
    product = np.concatenate([initial_product, changes["product"].to_numpy()])
    valid_from = np.concatenate([first[initial_product], changes["valid_from"].to_numpy()])
    gross = np.concatenate([anchor[initial_product] / total[initial_product],
                            anchor[changes["product"].to_numpy()] / later.to_numpy()])
    return product, valid_from, gross


def sale_events(shop, generator):
    """
    Dates of the flash sale shop's sales: sale_events_per_year random sales a year, each sale_days long, and one from
    Black Friday to Cyber Monday unless black_friday_share is 0. Sales start at least sale_gap_days apart, so they
    never overlap; a random sale too close to an earlier one (or to Black Friday) is dropped.

    Returns:
    pd.DataFrame: start and end (both inclusive) of every sale and the share of offers that join it, oldest first.
    """
    start, end = prices.period()
    low, high = shop["sale_days"]
    fixed, drawn = [], []
    for year in range(start.year, end.year + 1):
        first_day = pd.Timestamp(year, 1, 1)
        days = (pd.Timestamp(year, 12, 31) - first_day).days + 1
        count = shop["sale_events_per_year"]
        offsets = np.sort(generator.integers(0, days, size=count))
        lengths = generator.integers(low, high + 1, size=count)
        drawn += [(first_day + pd.Timedelta(days=int(offset)), int(length), shop["sale_share"])
                  for offset, length in zip(offsets, lengths, strict=True)]
        if shop["black_friday_share"] > 0:
            fixed.append((calendar.black_friday(year), 4, shop["black_friday_share"]))
    gap = pd.Timedelta(days=shop["sale_gap_days"])
    kept = list(fixed)
    for day, length, share in drawn:
        if all(abs(day - other) >= gap for other, _, _ in kept):
            kept.append((day, length, share))
    kept.sort()
    starts = pd.to_datetime([day for day, _, _ in kept])
    ends = pd.to_datetime([min(day + pd.Timedelta(days=length - 1), end) for day, length, _ in kept])
    return pd.DataFrame({"start": starts, "end": ends, "share": [share for _, _, share in kept]})


def flash_sale_prices(shop, covered, anchor, first, last, span_days, generator):
    """
    Price periods of the flash sale shop: regular prices as in random_shop_prices, cut by short sales. In every sale
    (sale_events) an offer on sale for the whole sale joins with the sale's share and costs one of sale_discounts
    less than its regular price on the day before; the day after the sale the regular price returns. A regular price
    change that falls inside a sale (also on its first day) starts when the sale ends.

    Returns:
    tuple: Product positions, valid_from dates, unrounded gross prices and the sale flag.
    """
    product, valid_from, gross = random_shop_prices(shop, covered, anchor, first, span_days, generator)
    regular = pd.DataFrame({"product": product, "valid_from": pd.to_datetime(valid_from), "gross": gross})
    regular = regular.sort_values(["product", "valid_from"], kind="stable")
    regular = regular[~regular.duplicated(["product", "valid_from"])]  # as in shop_periods: the first change wins
    regular = regular.sort_values("valid_from", kind="stable").reset_index(drop=True)

    sales = []
    discounts = np.asarray(shop["sale_discounts"], dtype=float)
    for sale in sale_events(shop, generator).itertuples(index=False):
        eligible = covered & (first < np.datetime64(sale.start)) & (last >= np.datetime64(sale.end))
        joins = eligible & (generator.random(len(anchor)) < sale.share)
        discount = generator.choice(discounts, size=len(anchor))
        chosen = np.flatnonzero(joins)
        sales.append(pd.DataFrame({"product": chosen, "start": sale.start, "end": sale.end,
                                   "discount": discount[chosen]}))
    sales = pd.concat(sales, ignore_index=True).sort_values("start", kind="stable").reset_index(drop=True)

    def regular_price_on(days):
        """Unrounded regular gross price of every sale's product on the given day (one day per sale)."""
        query = pd.DataFrame({"product": sales["product"], "day": days, "row": np.arange(len(sales))})
        query = query.sort_values("day", kind="stable")
        found = pd.merge_asof(query, regular, left_on="day", right_on="valid_from", by="product",
                              direction="backward")
        return found.sort_values("row")["gross"].to_numpy()

    restart = sales["end"] + pd.Timedelta(days=1)
    returns = (restart.to_numpy() <= last[sales["product"].to_numpy()])
    before = regular_price_on(sales["start"] - pd.Timedelta(days=1))
    sale_rows = pd.DataFrame({"product": sales["product"], "valid_from": sales["start"],
                              "gross": before * (1 - sales["discount"]), "promotion": True})
    back_rows = pd.DataFrame({"product": sales["product"], "valid_from": restart,
                              "gross": regular_price_on(restart), "promotion": False})[returns]

    inside = pd.merge_asof(regular.reset_index(), sales[["product", "start", "end"]], left_on="valid_from",
                           right_on="start", by="product", direction="backward").sort_values("index")
    in_sale = (inside["valid_from"] <= inside["end"]).to_numpy()
    kept = regular[~in_sale].assign(promotion=False)

    rows = pd.concat([sale_rows, back_rows, kept], ignore_index=True)
    return (rows["product"].to_numpy(), rows["valid_from"].to_numpy(), rows["gross"].to_numpy(),
            rows["promotion"].to_numpy(dtype=bool))


def build_competitor_prices(product_data, price_history, generator):
    """
    Draw the list prices of every competitor (settings.market_settings.competitor_settings) with their validity
    periods.

    Parameters:
    product_data (pd.DataFrame): Clean products with launch_date and discontinued_date.
    price_history (pd.DataFrame): Our list prices; the matcher follows their changes.
    generator (np.random.Generator): Random stream; every shop draws from its own child stream.

    Returns:
    pd.DataFrame: competitor_prices, one row per product, shop and price, ordered by product, shop and date.
    """
    count = len(product_data)
    first, last, span_days = selling_period(product_data)
    vat_ratio = (product_data["sales_price_gross"] / product_data["sales_price_net"]).to_numpy()
    market_gross = market_reference(product_data).to_numpy() * vat_ratio
    shop_ids = sorted(ms.competitor_settings)
    frames = []
    for shop_id, shop_generator in zip(shop_ids, generator.spawn(len(shop_ids)), strict=True):
        shop = ms.competitor_settings[shop_id]
        covered = shop_generator.random(count) < shop["coverage"]
        noise = np.exp(shop["price_sd"] * shop_generator.standard_normal(count) - shop["price_sd"] ** 2 / 2)
        anchor = market_gross * shop["price_level"] * noise
        if "reaction_probability" in shop:
            product, valid_from, gross = matcher_prices(shop, covered, anchor, product_data, price_history, last,
                                                        shop_generator)
            promotion = np.zeros(len(product), dtype=bool)
        elif "sale_events_per_year" in shop:
            product, valid_from, gross, promotion = flash_sale_prices(shop, covered, anchor, first, last, span_days,
                                                                      shop_generator)
        else:
            product, valid_from, gross = random_shop_prices(shop, covered, anchor, first, span_days, shop_generator)
            promotion = np.zeros(len(product), dtype=bool)
        frames.append(shop_periods(shop_id, shop, product, valid_from, gross, promotion, product_data, vat_ratio,
                                   market_gross))

    competitor_prices = pd.concat(frames, ignore_index=True)
    competitor_prices = competitor_prices.sort_values(["product_id", "competitor_id", "valid_from"], kind="stable")
    competitor_prices = competitor_prices.reset_index(drop=True)
    competitor_prices.insert(0, "competitor_price_id", np.arange(1, len(competitor_prices) + 1))
    return competitor_prices[COMPETITOR_COLUMNS]


def shop_periods(shop_id, shop, product, valid_from, gross, promotion, product_data, vat_ratio, market_gross):
    """
    Round the prices of one shop, drop changes that keep the same price and add the validity periods. When rows share
    a day, the first one passed in wins (the flash sale shop passes its sale rows first).
    """
    rows = pd.DataFrame({"product": product, "valid_from": pd.to_datetime(valid_from).normalize(), "gross": gross,
                         "promotion": promotion})
    rows = rows.sort_values(["product", "valid_from"], kind="stable")
    rows = rows[~rows.duplicated(["product", "valid_from"])]
    rows["gross"] = round_price(rows["gross"].to_numpy(), shop["price_ending"])
    same_product = rows["product"].eq(rows["product"].shift())
    rows = rows[~(same_product & rows["gross"].eq(rows["gross"].shift()))].reset_index(drop=True)

    same_product = rows["product"].eq(rows["product"].shift()).to_numpy()
    previous = rows["gross"].shift().to_numpy()
    change_type = np.where(~same_product, "initial", np.where(rows["gross"].to_numpy() > previous, "increase",
                                                              "decrease"))
    position = rows["product"].to_numpy()
    product_id = product_data["product_id"].to_numpy()[position]
    next_from = rows.groupby("product")["valid_from"].shift(-1)
    discontinued = product_data["discontinued_date"].to_numpy()[position]
    valid_to = (next_from - pd.Timedelta(days=1)).fillna(pd.Series(discontinued, index=rows.index))
    return pd.DataFrame({
        "product_id": product_id,
        "competitor_id": shop_id,
        "competitor_name": shop["name"],
        "valid_from": rows["valid_from"].to_numpy(),
        "valid_to": valid_to.to_numpy(),
        "price_gross": rows["gross"].to_numpy(),
        "price_net": np.round(rows["gross"].to_numpy() / vat_ratio[position], 2),
        "change_type": change_type,
        "is_promotion": rows["promotion"].to_numpy(dtype=bool),
        "competitor_strategy": shop["strategy"],
        "true_price_level": shop["price_level"],
        "true_market_price_gross": np.round(market_gross[position], 2),
    })
