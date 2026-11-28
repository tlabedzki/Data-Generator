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
    "payment_data": "the payment of an order, with the payment operator's fee",
    "review_data": "a rating of a delivered order line",
    "campaign_data": "a marketing campaign",
    "session_data": "a web session",
    "experiment_data": "an A/B experiment",
    "experiment_assignment_data": "a unit (session or customer) in an experiment",
    "anomaly_data": "a labelled anomaly: fraud ring, shop outage or return spike",
    "quality_issue_data": "one injected data quality issue (empty at data_quality_level none)",
    "supplier_data": "a supplier the shop buys from",
    "product_supplier_data": "the supplier of a product, with its pack size and minimum order",
    "purchase_order_data": "a purchase order line: units of one product the shop ordered from its supplier",
    "stock_movement_data": "a change in the stock of a product: opening stock, a delivery or the units sold on a day",
    "lost_demand_data": "an order line the customer could not place because the product was out of stock (empty "
                        "unless stockouts is on)",
    "markdown_data": "a markdown: the shop lowered the list price of a slow product or cleared the stock of a product "
                     "about to be withdrawn (empty unless markdowns is on)",
    "outlet_data": "stock of a withdrawn product sold to an outlet on its withdrawal day (empty unless markdowns is "
                   "on)",
}

# Columns that hold the answer an analysis should find (hide them before you analyse).
TRUTH = {"customer_segment", "preferred_category", "price_tier", "true_purchase_rate", "true_churn_date", "is_fraud",
         "true_daily_lift", "true_effect", "has_sample_ratio_mismatch", "anomaly_type", "clean_value",
         "competitor_strategy", "true_price_level", "true_market_price_gross", "true_lead_time_mean_days",
         "true_lead_time_cv", "true_elasticity", "true_uplift"}
# Tables that are truth as a whole: every column is the answer.
TRUTH_TABLES = {"lost_demand_data"}

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
    "sales_margin": "margin the list price leaves: 1 - net_purchase_price / sales_price_net (0.30 = 30%)",
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
    "sales_price_net": "current list price without VAT: sales_price_gross / 1.23, PLN",
    "sales_price_gross": "current list price with VAT, ending in 9, PLN",
    "launch_date": "first day the product can sell",
    "discontinued_date": "last day the product can sell; empty while on sale",
    "parcel_size": "small, medium, large or bulky: parcel size of the product, by category and product type",
    "order_id": "order key; one order has 1-5 lines",
    "order_line_id": "order line key",
    "order_date": "order day",
    "order_datetime": "order time, to the second",
    "quantity": "units on the line",
    "unit_price_gross": "list price with VAT on the order day, PLN",
    "unit_price_net": "list price without VAT on the order day: unit_price_gross / 1.23, PLN",
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
    "affiliate_commission": "commission paid to the affiliate network for the units kept, without VAT, PLN; 0 outside "
                            "the affiliate channel and for cancelled or failed orders",
    "sales_price_gross_after_discount": "unit_price_gross after discount_rate, PLN",
    "sales_price_net_after_discount": "unit_price_net after discount_rate, PLN",
    "revenue_gross": "quantity × sales_price_gross_after_discount, PLN, as ordered: also for cancelled orders",
    "valid_from": "first day of this list price",
    "valid_to": "last day of this list price; empty for the current price",
    "change_type": "initial, increase or decrease; with markdowns on also markdown (start of a markdown) and "
                   "markdown_end (the regular price is back)",
    ("price_history", "sales_price_gross"): "list price with VAT in this period, PLN",
    ("price_history", "sales_price_net"): "list price without VAT in this period, PLN",
    "competitor_price_id": "competitor price key (from 1)",
    "competitor_id": "competing shop key, 1-5",
    "competitor_name": "fictional shop name: Frugalia, Aequo, Maison Orvelle, Mercatoria or Fulmina",
    ("competitor_prices", "valid_from"): "first day of this competitor price",
    ("competitor_prices", "valid_to"): "last day of this price; empty when the offer is on sale at the end",
    "price_gross": "competitor price with VAT (the sale price while is_promotion), ending in ,99 or 9 by shop, PLN",
    "price_net": "competitor price without VAT: price_gross / 1.23, PLN",
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
    ("shipment_data", "parcel_size"): "size of the parcel: its largest product, one size up from 4 units",
    "carrier_cost": "what the carrier charges the shop by method and parcel size, plus the cash-on-delivery fee, "
                    "without VAT, PLN",
    "return_id": "return key",
    "return_date": "day the return was registered",
    "returned_quantity": "units returned",
    "return_reason": "for example wrong_size, changed_mind or defective",
    "refund_amount": "money refunded, PLN",
    "return_status": "refunded or rejected",
    "return_shipping_cost": "return label paid by the shop, without VAT, PLN; 0 when the customer pays (changed_mind)",
    "handling_cost": "receiving and checking the return, without VAT, PLN",
    "written_off_quantity": "returned units that cannot be sold again; 0 for a rejected return",
    "write_off_cost": "written_off_quantity × net_purchase_price, PLN",
    "payment_id": "payment key; one payment per order",
    "payment_amount": "amount charged at checkout: lines after discount plus the delivery fee, PLN gross; 0 when a "
                      "cash-on-delivery order is cancelled",
    "fee_rate": "operator's share of the amount by payment method; 0 for cash on delivery and failed payments",
    "fixed_fee": "operator's fixed fee by provider, or the fee of a declined card; 0 for cash on delivery, PLN",
    "payment_fee": "payment_amount × fee_rate + fixed_fee, PLN; kept by the operator when the order is refunded",
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
    "supplier_id": "supplier key (from 1)",
    "supplier_name": "fictional company name",
    "country": "where the supplier ships from: PL, DE or CN",
    "order_weekdays": "weekdays the supplier takes orders on, for example Mon,Thu",
    "promised_lead_time_days": "lead time the supplier promises, in days: its true mean, rounded",
    "true_lead_time_mean_days": "mean of the actual lead time, in days",
    "true_lead_time_cv": "spread of the actual lead time: standard deviation / mean",
    "pack_size": "units in one pack; the shop orders whole packs",
    "min_order_quantity": "smallest order of the product in units (whole packs)",
    "purchase_order_id": "purchase order key; the lines of one supplier on one day share it",
    "purchase_order_line_id": "purchase order line key",
    ("purchase_order_data", "order_date"): "day the shop ordered; the first delivery of a product launched in the "
                                           "period is ordered a lead time before its launch",
    "ordered_quantity": "units ordered",
    "promised_date": "order day plus the promised lead time",
    "received_date": "day the delivery arrived (never on Sunday); empty while still on the way at the end",
    "received_quantity": "units received, all that were ordered; empty while on the way",
    "unit_cost_net": "purchase price of one unit without VAT (net_purchase_price), PLN",
    "is_express": "express delivery that filled an empty shelf the same day (only with stockouts off)",
    "stock_movement_id": "movement key, oldest first",
    "movement_date": "day of the movement",
    "movement_type": "opening (stock on the first day), receipt (a delivery), sale (units of the day's order lines) "
                     "or outlet (stock left on the withdrawal day, with markdowns on)",
    ("stock_movement_data", "quantity"): "change in units: plus for opening and receipts, minus for sales and the "
                                         "outlet",
    "stock_after": "units in stock after the movement",
    ("stock_movement_data", "purchase_order_line_id"): "purchase order line of a receipt; empty otherwise",
    "lost_line_id": "lost line key",
    ("lost_demand_data", "quantity"): "units the customer wanted",
    ("lost_demand_data", "unit_price_gross"): "list price with VAT on that day, PLN",
    "lost_revenue_gross": "quantity × unit_price_gross × (1 - discount_rate), PLN",
    ("lost_demand_data", "session_id"): "session in which the customer found the product out of stock",
    "markdown_id": "markdown key, oldest first",
    ("markdown_data", "start_date"): "first day at the markdown price",
    ("markdown_data", "end_date"): "last day at the markdown price; empty while the markdown runs at the end",
    "reason": "slow_stock (stock that outlasts markdown_cover_days at recent sales) or clearance (stock of a product "
              "withdrawn within clearance_days)",
    "regular_price_gross": "list price with VAT on the first day, before the markdown, PLN",
    "markdown_price_gross": "list price with VAT during the markdown, ending in ,99, PLN",
    "markdown_rate": "1 - markdown_price_gross / regular_price_gross (0.30 = 30% off)",
    "end_reason": "planned (the planned length passed), sold_out, clearance (a clearance took over), withdrawn (the "
                  "product was withdrawn) or ongoing",
    "true_elasticity": "price elasticity of the product's category",
    "true_uplift": "demand during the markdown against demand at the regular price: (markdown price / regular price) "
                   "** -true_elasticity",
    "outlet_sale_id": "outlet sale key",
    "sale_date": "withdrawal day: the outlet takes the stock left",
    ("outlet_data", "quantity"): "units sold to the outlet",
    ("outlet_data", "unit_price_net"): "price the outlet pays per unit without VAT: outlet_recovery_rate × "
                                       "net_purchase_price, PLN",
    "revenue_net": "quantity × unit_price_net, PLN",
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
                         f"{note(table, column)} | {'yes' if column in TRUTH or table in TRUTH_TABLES else ''} |")
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
