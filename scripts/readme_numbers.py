"""
Numbers and tables for README.md, computed from the same default run as the README charts (scripts/make_charts.py).

README.md marks each generated part with `<!-- generated:<name> -->` and `<!-- /generated:<name> -->`; update_readme()
replaces only the text between a pair, so the hand-written text around it stays as it is.
"""
import re
import textwrap
from pathlib import Path

import pandas as pd

import func.charts as ch
import func.number_format as nf
import settings.main_settings as s

SAMPLE_COLUMNS = ["order_date", "order_id", "category", "product_name", "quantity", "revenue_gross", "order_status",
                  "city"]
LANGUAGE_NAMES = {"en": "English", "pl": "Polish"}
CHARTS = [  # file name stem, function that gives the takeaway sentence under the chart
    ("monthly-revenue", lambda sales, weights: monthly_takeaway(sales)),
    ("weekday-profile", lambda sales, weights: weekday_takeaway(sales, weights)),
    ("category-mix", lambda sales, weights: category_takeaway(sales)),
]


def wrap(text):
    """README source lines stay within 120 characters."""
    return textwrap.fill(text, width=118, break_long_words=False, break_on_hyphens=False)


def pct(value, digits=0):
    return nf.percent(value, digits)


def sample_block(datasets):
    """Three order lines of sales_data as a Markdown table, with one sentence under it."""
    sales = datasets["sales_data"]
    rows = sales.iloc[[0, len(sales) // 3, 2 * len(sales) // 3]][SAMPLE_COLUMNS]
    lines = ["| " + " | ".join(SAMPLE_COLUMNS) + " |", "|" + "---|" * len(SAMPLE_COLUMNS)]
    for _, row in rows.iterrows():
        cells = [f"{row['order_date']:%Y-%m-%d}", str(row["order_id"]), row["category"], row["product_name"],
                 str(row["quantity"]), nf.number(row["revenue_gross"], 2), row["order_status"], row["city"]]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", wrap(f"Three of the {nf.number(len(sales))} rows of `sales_data` ({len(sales.columns)} columns: each "
                       "order line joined with its customer and product), exactly as `python main.py` writes them "
                       f"with the default {LANGUAGE_NAMES[s.data_language]} values.")]
    return "\n".join(lines)


def metrics_block(datasets):
    """Numbers of the default run that the tables support without any hidden answer: money, funnel and accounts."""
    sales, orders = datasets["sales_data"], datasets["order_data"].drop_duplicates("order_id")
    paid = ch.realised(sales)
    net = (paid["quantity"] * paid["unit_price_net"] * (1 - paid["discount_rate"])).sum()
    cost = (paid["quantity"] * paid["net_purchase_price"]).sum()
    refunds = datasets["return_data"]["refund_amount"].sum() / paid["revenue_gross"].sum()
    lost = 1 - paid["revenue_gross"].sum() / sales["revenue_gross"].sum()
    campaigns = datasets["campaign_data"]
    attributed = paid.groupby("campaign_id")["revenue_gross"].sum().reindex(campaigns["campaign_id"]).fillna(0)
    roas = (attributed.groupby(campaigns["channel"].to_numpy()).sum()
            / campaigns.groupby("channel")["total_cost"].sum()).sort_values()
    sessions = datasets["session_data"]
    abandoned = (sessions["added_to_cart"] & sessions["order_id"].isna()).sum() / sessions["added_to_cart"].sum()
    voucher = orders["voucher_code"].notna().mean()
    free = (datasets["shipment_data"]["shipping_cost"] == 0).mean()
    products, customers = datasets["product_data"], datasets["customer_data"]
    start = pd.Timestamp(s.start_year, 1, 1)
    launched = (products["launch_date"] >= start).mean()
    discontinued = products["discontinued_date"].notna().mean()
    buyers = orders["customer_id"].nunique()
    earlier = (customers["signup_date"] < start).mean()
    names = {"affiliate": "affiliate", "email": "e-mail", "paid_search": "paid search", "social": "social"}
    return "\n".join([
        wrap(f"The same run keeps the money side of every order. Lines carry the purchase price, so the gross margin "
             f"of shipped orders is {pct(1 - cost / net)}; refunds take {pct(refunds, 1)} off revenue, and cancelled "
             f"or unpaid orders hold {pct(lost, 1)} of the value ordered. Campaign costs with "
             f"`acquisition_channel` give CAC and ROAS, which runs from {nf.number(roas.iloc[0], 1)} "
             f"({names.get(roas.index[0], roas.index[0])}) to {nf.number(roas.iloc[-1], 1)} "
             f"({names.get(roas.index[-1], roas.index[-1])})."),
        "",
        wrap(f"{pct(abandoned)} of carts are abandoned, {pct(voucher)} of orders use a campaign voucher code and "
             f"{pct(free)} of shipments go free (above the free-delivery threshold or picked up in store). "
             f"{pct(launched)} of products launch during the period and {pct(discontinued)} are discontinued, and "
             f"{nf.number(buyers)} of the {nf.number(len(customers))} accounts order in it: {pct(earlier)} signed up "
             "earlier, so their cohorts start before the data does."),
        "",
        shop_costs_sentence(datasets, paid),
    ])


def shop_costs_sentence(datasets, paid):
    """What selling costs the shop beyond the purchase price, as shares of net revenue of shipped orders."""
    import settings.market_settings as ms
    net = (paid["quantity"] * paid["unit_price_gross"] * (1 - paid["discount_rate"])).sum() / (1 + ms.vat_rate)
    shipments, returns = datasets["shipment_data"], datasets["return_data"]
    free = shipments["shipping_cost"] == 0
    back = returns[returns["return_status"] == "refunded"]
    written_off = back["written_off_quantity"].sum() / back["returned_quantity"].sum()
    returns_cost = returns[["return_shipping_cost", "handling_cost", "write_off_cost"]].sum().sum()
    return wrap(f"The shop's own selling costs are in the data too, without VAT. Carriers take "
                f"{pct(shipments['carrier_cost'].sum() / net, 1)} of net revenue (a free shipment still costs the "
                f"shop {nf.number(shipments.loc[free, 'carrier_cost'].mean(), 2)} PLN on average), returns "
                f"{pct(returns_cost / net, 1)} on top of the refunds, with {pct(written_off)} of returned units "
                f"written off, payment fees {pct(datasets['payment_data']['payment_fee'].sum() / net, 1)} and "
                f"affiliate commission {pct(datasets['order_data']['affiliate_commission'].sum() / net, 1)}.")


def chart_image(stem, alt):
    """A light chart, shown the same in GitHub's light and dark themes."""
    return f"![{alt}](docs/img/{stem}.png)"


def monthly_takeaway(sales):
    data = ch.monthly_revenue_data(sales)
    peak = data.loc[data["is_peak"]].iloc[0]
    growth = ch.yearly_growth(sales)
    trend = f"grows {pct(growth)} a year and " if growth is not None and growth >= 0 else ""
    return (f"Revenue {trend}peaks at {nf.compact(peak['revenue'])} PLN in {peak['month']:%B %Y}, "
            "the Black Friday month.")


def weekday_takeaway(sales, weights):
    data = ch.weekday_data(sales, weights)
    gap = (data["share"] - data["configured"]).abs().max()
    return (f"Every weekday lands within {nf.number(gap * 100, 1)} percentage points of its configured weight: "
            "special days such as Black Friday and the weekly e-mail campaigns on Tuesdays or Thursdays move it, as "
            "they would in a real shop.")


def category_takeaway(sales):
    data = ch.category_data(sales)
    gap = (data["share"] - data["target"]).abs().max()
    return (f"Category revenue lands within {nf.number(gap * 100, 1)} percentage points of the target mix: the "
            "generator corrects for average price, so expensive categories do not take over revenue just because "
            "their unit prices are high.")


PACK_NAMES = {"E": "Dirty data and anomalies", "A": "Customer behaviour",
              "D": "Prices, promotions, returns and shipping", "B": "Basket and preferences",
              "C": "Marketing and traffic", "F": "A/B experiments", "G": "Order status, reviews and churn",
              "H": "Competitor prices", "I": "Shop costs",
              "J": "Suppliers and stock", "K": "Markdowns, clearance and the outlet"}
HEADLINES = [  # (pack, start of the check label in scripts/check_realism.py, wording in the README)
    ("A", "order growth first to last year", "Orders grow year over year (setting: 20% a year)"),
    ("D", f"Black Friday {s.end_year}", f"Black Friday {s.end_year} against an average November day"),
    ("G", "failed payments, deferred payment / BLIK", "Failed payments, deferred payment against BLIK (setting: "
                                                         "10% / 1.2%)"),
    ("A", "revenue share of the top 10% customers", "Revenue from the top 10% of customers"),
    ("A", "cohort retention month 1 / month 12", "Cohort retention after 1 and 12 months"),
    ("B", "lift Laptop + Wireless Mouse", "Lift of laptop and wireless mouse in one basket (orders)"),
    ("D", "return rate Clothing / Electronics", "Return rate, Clothing against Electronics"),
    ("G", "average rating on time / late", "Average rating: on time / late / defective or damaged"),
    ("F", "checkout_redesign: conversion lift", "A/B test with a true +10% lift: measured lift and 95% CI"),
    ("E", "fraud order value / other orders", "Labelled fraud orders: value against other orders (orders)"),
]


def realism_checks(datasets):
    """Run every criterion of scripts/check_realism.py on the README run and return (pack, label, value, passed)."""
    import check_realism as cr  # noqa: E402  (scripts/ is on sys.path; the import silences the generator log)

    rows = []
    original = cr.check
    cr.check = lambda pack, label, value, passed: rows.append((pack, label, str(value), bool(passed)))
    try:
        for check_pack in cr.PACKS.values():
            check_pack(datasets)
    finally:
        cr.check = original
    return rows


def realism_block(rows):
    """Headline criteria as a table; docs/realism.md lists all of them."""
    passed = sum(row[3] for row in rows)
    found = {}
    for pack, label, value, _ in rows:
        found.setdefault((pack, label), value)
    lines = ["| What a real shop does | Default run |", "|---|---|"]
    for pack, prefix, wording in HEADLINES:
        value = next(v for (p, label), v in found.items() if p == pack and label.startswith(prefix))
        lines.append(f"| {wording} | **{value}** |")
    return "\n".join(lines), passed, len(rows)


def results_block(datasets, weights, rows):
    sales = datasets["sales_data"]
    texts = {"monthly-revenue": ch.monthly_revenue_text(sales), "weekday-profile": ch.weekday_text(sales, weights),
             "category-mix": ch.category_text(sales)}
    parts = []
    for stem, takeaway in CHARTS:
        parts += [chart_image(stem, texts[stem][0]), "", wrap(takeaway(sales, weights)), ""]
    table, passed, total = realism_block(rows)
    parts += [wrap(f"Beyond the charts, {passed} of {total} realism criteria pass on the same run. The table shows ten "
                   "of them; [docs/realism.md](docs/realism.md) lists all with their values."), "", table]
    return "\n".join(parts)


def data_block(datasets, postal_codes):
    """Postal code source numbers and how customers spread over localities."""
    city_share = datasets["customer_data"]["city"].value_counts(normalize=True)
    return wrap(f"Customer addresses take a real postal code and its main locality from `source/pl_postal_code.csv` "
                f"({nf.number(len(postal_codes))} Polish postal codes, {nf.number(postal_codes['city'].nunique())} "
                "localities), drawn with a weight equal to the number of addresses. Addresses count buildings rather "
                "than residents, so cities with large apartment blocks get fewer customers than their population "
                f"would suggest: {city_share.index[0]} has {pct(city_share.iloc[0], 1)} of customers.")


def cli_block(datasets):
    sales = datasets["sales_data"]
    years = sorted(sales["order_date"].dt.year.unique())
    period = f"{years[0]} and {years[-1]}" if len(years) == 2 else f"{years[0]} to {years[-1]}"
    return wrap(f"`python main.py` writes {nf.number(len(datasets['customer_data']))} customers, "
            f"{nf.number(len(datasets['product_data']))} products and {nf.number(len(sales))} order lines "
            f"({nf.number(sales['order_id'].nunique())} orders in {period}) with seed 42 and "
            f"{LANGUAGE_NAMES[s.data_language]} values, and saves {len(s.generated_files)} tables as "
            f"{s.saving_format.capitalize()} files in `export/`.")


def update_readme(path, blocks):
    """Replace the text between each pair of generated markers in README.md."""
    text = "\n".join(Path(path).read_text(encoding="utf-8").splitlines()) + "\n"
    for name, content in blocks.items():
        pattern = re.compile(rf"(<!-- generated:{name} -->\n).*?(<!-- /generated:{name} -->)", re.S)
        if not pattern.search(text):
            raise SystemExit(f"README.md has no <!-- generated:{name} --> block")
        text = pattern.sub(lambda m, body=content: f"{m.group(1)}\n{body}\n\n{m.group(2)}", text)
    Path(path).write_text(text, encoding="utf-8", newline="\n")
