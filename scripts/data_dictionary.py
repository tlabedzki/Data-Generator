"""
docs/columns.md (every column of every table) and docs/realism.md (every realism criterion), written from the default
run by scripts/make_charts.py. The meaning of each column lives here; types, examples and row counts come from data.
"""
import textwrap
from pathlib import Path

import pandas as pd

TABLE_ROWS = {
    "customer_data": "a customer account",
    "product_data": "a product",
    "order_data": "an order line",
    "sales_data": "an order line joined with its product and customer",
    "price_history": "a list price of a product with its validity period",
    "competitor_prices": "a list price of a product at one competing shop, with its validity period",
    "shipment_data": "the shipment of an order",
    "return_data": "a returned order line",
    "review_data": "a rating of a delivered order line",
    "campaign_data": "a marketing campaign",
    "session_data": "a web session",
    "experiment_data": "an A/B experiment",
    "experiment_assignment_data": "a unit (session or customer) in an experiment",
    "anomaly_data": "a labelled anomaly: fraud ring, shop outage or return spike",
    "quality_issue_data": "one injected data quality issue (empty at data_quality_level none)",
}

# Columns that hold the answer an analysis should find (hide them before you analyse).
TRUTH = {"customer_segment", "preferred_category", "price_tier", "true_purchase_rate", "true_churn_date", "is_fraud",
         "true_daily_lift", "true_effect", "has_sample_ratio_mismatch", "anomaly_type", "clean_value",
         "competitor_strategy", "true_price_level", "true_market_price_gross"}

# The same column name means the same thing in every table; a (table, column) key overrides it for one table.
NOTES = {
    "customer_id": "customer key (from 100001)",
    "age": "age in years, 18-65",
    "gender": "Male or Female",
    "first_name": "fictional first name (Faker, pl_PL)",
    "last_name": "fictional last name (Faker, pl_PL)",
    "email": "unique address on example.com, example.org or example.net",
    "phone_number": "fictional Polish phone number",
    "bank_account_number": "fictional IBAN",
    "postal_code": "real Polish postal code of the address, drawn by number of addresses",
    "city": "main locality of the postal code",
    "signup_date": "account creation date; can be years before the period",
    "customer_segment": "behaviour given to the customer: one_time, occasional, regular, loyal or deal_hunter",
    "preferred_category": "category the customer buys most from",
    "price_tier": "budget, standard or premium: how expensive the products they keep are",
    "acquisition_channel": "channel that brought the customer",
    "true_purchase_rate": "repeat orders a year while active, at an average time of the year (0 for one-time buyers)",
    "true_churn_date": "last day the customer can buy; can lie outside the period, signup day if never ordering",
    "product_id": "product key (from 200001)",
    "net_purchase_price": "purchase price without VAT, PLN",
    "sales_margin": "gross margin of the list price (0.30 = 30%)",
    "currency": "always PLN",
    "category": "top level of the catalog, 15 categories",
    "subcategory": "second level of the catalog",
    "product_type": "for example Laptop or Running Shoes",
    "brand": "brand label (real names, fictional products)",
    "product_series": "series within the brand",
    "product_model": "model within the series",
    "product_name": "type, brand, series and model",
    "product_popularity": "long-tail sales weight (log-normal)",
    "color": "product colour",
    "sales_price_net": "current list price without VAT, PLN",
    "sales_price_gross": "current list price with VAT, ending in 9, PLN",
    "launch_date": "first day the product can sell",
    "discontinued_date": "last day the product can sell; empty while on sale",
    "order_id": "order key; one order has 1-5 lines",
    "order_line_id": "order line key",
    "order_date": "order day",
    "order_datetime": "order time, to the second",
    "quantity": "units on the line",
    "unit_price_gross": "list price with VAT on the order day, PLN",
    "unit_price_net": "list price without VAT on the order day, PLN",
    "payment_method": "for example BLIK, Card or Fast transfer",
    "payment_provider": "payment operator",
    "delivery_method": "carrier or pickup",
    "discount_rate": "discount on the line (0.15 = 15%)",
    "shipping_postal_code": "postal code the order ships to; usually the customer's own",
    "is_fraud": "the order belongs to a fraud ring",
    "channel": "traffic channel",
    "device": "mobile, desktop or tablet",
    "campaign_id": "campaign credited with the order or session; empty without one",
    "voucher_code": "campaign voucher used; empty without one",
    "session_id": "session key; in order_data, the session that converted",
    "order_status": "delivered, returned (every line refunded in full), cancelled or payment_failed",
    "payment_status": "paid, refunded, failed, or unpaid for a cancelled cash-on-delivery order",
    "cancel_reason": "customer_request, out_of_stock, duplicate_order or address_problem; empty unless cancelled",
    "cancelled_at": "cancellation time, before the planned dispatch; empty unless cancelled",
    "sales_price_gross_after_discount": "unit_price_gross after discount_rate, PLN",
    "sales_price_net_after_discount": "unit_price_net after discount_rate, PLN",
    "revenue_gross": "quantity × sales_price_gross_after_discount, PLN, as ordered: also for cancelled orders",
    "valid_from": "first day of this list price",
    "valid_to": "last day of this list price; empty for the current price",
    "change_type": "initial, increase or decrease",
    ("price_history", "sales_price_gross"): "list price with VAT in this period, PLN",
    ("price_history", "sales_price_net"): "list price without VAT in this period, PLN",
    "competitor_price_id": "competitor price key (from 1)",
    "competitor_id": "competing shop key, 1-5",
    "competitor_name": "fictional shop name: Frugalia, Aequo, Maison Orvelle, Mercatoria or Fulmina",
    ("competitor_prices", "valid_from"): "first day of this competitor price",
    ("competitor_prices", "valid_to"): "last day of this price; empty when the offer is on sale at the end",
    "price_gross": "competitor price with VAT (the sale price while is_promotion), ending in ,99 or 9 by shop, PLN",
    "price_net": "competitor price without VAT, at the VAT of the product, PLN",
    ("competitor_prices", "change_type"): "initial, increase or decrease (the matcher follows our changes; a sale "
                                         "starts with a decrease and ends with an increase)",
    "is_promotion": "a short sale price of the flash sale shop Fulmina; false at the other shops",
    "competitor_strategy": "discounter, matcher, premium, marketplace or flash_sale",
    "true_price_level": "price level of the shop against the market price (0.92 = 8% below), sale prices aside",
    "true_market_price_gross": "market price with VAT: cost × median markup of the product type, PLN",
    "shipment_id": "shipment key; only orders that shipped have one",
    "is_bulky": "furniture or other goods too large for a parcel locker",
    "shipping_cost": "delivery fee paid by the customer, PLN",
    "shipped_at": "dispatch time",
    "delivered_at": "delivery time",
    "promised_delivery_date": "delivery date promised at checkout",
    "is_late": "delivered after the promised date",
    "return_id": "return key",
    "return_date": "day the return was registered",
    "returned_quantity": "units returned",
    "return_reason": "for example wrong_size, changed_mind or defective",
    "refund_amount": "money refunded, PLN",
    "return_status": "refunded or rejected",
    "review_id": "review key",
    "review_date": "day of the review, after delivery",
    "review_score": "rating from 1 to 5 stars",
    "review_comment": "one of the ready sentences; empty without a comment",
    "campaign_name": "channel and start date",
    ("campaign_data", "channel"): "paid_search, social, email or affiliate",
    "start_date": "first day",
    "end_date": "last day",
    "total_cost": "campaign cost, PLN",
    ("campaign_data", "voucher_code"): "voucher of the campaign; empty for campaigns without one",
    "true_daily_lift": "extra demand per campaign day as a share of an ordinary day",
    "session_start": "session start time",
    ("session_data", "customer_id"): "logged-in customer; empty for anonymous visits",
    "pages_viewed": "pages viewed in the session",
    "added_to_cart": "the session added a product to the cart",
    "reached_checkout": "the session reached the checkout",
    ("session_data", "order_id"): "order placed in the session; empty when it did not convert",
    "experiment_id": "experiment key",
    "experiment_name": "for example checkout_redesign",
    "unit": "session or customer",
    "metric": "conversion_rate or units_per_line",
    "planned_split_b": "share of units meant for variant B",
    "true_effect": "effect built into the data: relative for conversion_rate, absolute for units_per_line",
    "has_sample_ratio_mismatch": "B got a different share than planned (a bug to detect)",
    "unit_id": "session_id or customer_id, depending on unit",
    "variant": "A (control) or B (change)",
    "assigned_at": "first time the unit was seen in the experiment",
    "anomaly_id": "anomaly key",
    "anomaly_type": "fraud_ring, shop_outage or return_spike",
    "table_name": "table the rows belong to",
    "affected_rows": "rows of that table affected",
    ("anomaly_data", "customer_id"): "account used by the fraud ring; empty for other anomalies",
    "description": "what happened, in one sentence",
    "issue_id": "issue key",
    "key_column": "key column of the affected row",
    "key_value": "key value of the affected row",
    "column_name": "column that was changed",
    "issue_type": "missing, typo, format, outlier, duplicate_customer or duplicate_row",
    "dirty_value": "value in the file",
    "clean_value": "value before the issue was injected",
}


def wrap(text: str) -> str:
    return textwrap.fill(text, width=118, break_long_words=False, break_on_hyphens=False)


def note(table: str, column: str) -> str:
    return NOTES.get((table, column)) or NOTES.get(column, "")


def dtype_name(series: pd.Series) -> str:
    kind = str(series.dtype)
    if kind.startswith("datetime64"):
        return "datetime"
    return {"object": "text", "Int64": "int (nullable)", "int64": "int", "float64": "float", "bool": "bool"}.get(kind,
                                                                                                                  kind)


def example(series: pd.Series) -> str:
    values = series.dropna()
    if values.empty:
        return ""
    value = values.iloc[0]
    if isinstance(value, pd.Timestamp):
        return f"{value:%Y-%m-%d %H:%M}" if value.time().isoformat() != "00:00:00" else f"{value:%Y-%m-%d}"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value).replace("|", "/")[:40]


def columns_markdown(datasets: dict[str, pd.DataFrame]) -> str:
    """Every table with one row per column: type, an example from the default run, meaning, truth or not."""
    lines = ["# Columns", "", wrap(
             "Every table of the default run (`python main.py`, seed 42), generated by `scripts/make_charts.py`. "
             "Examples come from the first row with a value, in English. Truth columns hold the answer an analysis "
             "should find; leave them out of the analysis and use them to check it. "
             "[data-model.md](data-model.md) shows how the tables link."), ""]
    for table, frame in datasets.items():
        lines += [f"## {table}", "", f"One row is {TABLE_ROWS[table]}. {len(frame):,} rows in the default run.", ""]
        if table == "sales_data":
            joined = [c for c in frame.columns if c in set().union(*(datasets[t].columns for t in
                                                                     ("order_data", "product_data", "customer_data")))]
            lines += [f"All {len(joined)} columns of `order_data`, `product_data` and `customer_data` (joined on "
                      "`product_id` and `customer_id`), plus:", ""]
            frame = frame[[c for c in frame.columns if c not in joined]]
        lines += ["| Column | Type | Example | Meaning | Truth |", "|---|---|---|---|---|"]
        for column in frame.columns:
            lines.append(f"| `{column}` | {dtype_name(frame[column])} | {example(frame[column])} | "
                         f"{note(table, column)} | {'yes' if column in TRUTH else ''} |")
        lines.append("")
    return "\n".join(lines)


def realism_markdown(rows: list[tuple[str, str, str, bool]], pack_names: dict[str, str]) -> str:
    """Every realism criterion of scripts/check_realism.py with its value on the default run."""
    passed = sum(row[3] for row in rows)
    lines = ["# Realism criteria", "", wrap(
             f"{passed} of {len(rows)} criteria pass on the default run (seed 42). `python scripts/check_realism.py` "
             "runs the same checks and exits with 1 when any of them fails; `scripts/make_charts.py` writes this "
             "page."), ""]
    for pack, name in pack_names.items():
        lines += [f"## {name}", ""]
        lines += [f"- {'✅' if ok else '❌'} {label}: {value}" for p, label, value, ok in rows if p == pack]
        lines.append("")
    return "\n".join(lines)


def write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
