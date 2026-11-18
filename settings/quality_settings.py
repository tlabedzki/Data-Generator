# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Data quality issues (dirty data for cleaning exercises):

# Choose how dirty the generated files are. Available options: "none", "low", "medium", "high".
# "none" gives clean data. Every injected issue is listed in quality_issue_data with the clean value, so a cleaning
# notebook can be scored against the truth.
data_quality_level = "none"

# Base share of rows affected by one issue type at each level.
data_quality_rates = {
    "none": 0.0,
    "low": 0.01,
    "medium": 0.03,
    "high": 0.08,
}

# Issue types: (table, column, issue type, multiplier of the base share).
# - missing: the value is removed (empty cell),
# - typo: a misspelled city (lower or upper case, no Polish letters, swapped letters, extra spaces),
# - format: the same value written differently (phone 600-100-200, postal code 00123, e-mail in capitals),
# - outlier: an impossible value (age 0 or 150, quantity 250, purchase price entered in grosze),
# - duplicate_customer: the same person with a second account (new customer_id); part of their orders moves to it,
# - duplicate_row: an order line saved twice (same order_line_id).
data_quality_issues = [
    ("customer_data", "phone_number", "missing", 1.0),
    ("customer_data", "email", "missing", 0.3),
    ("customer_data", "city", "missing", 0.5),
    ("customer_data", "age", "missing", 0.5),
    ("customer_data", "city", "typo", 1.0),
    ("customer_data", "phone_number", "format", 2.0),
    ("customer_data", "postal_code", "format", 0.5),
    ("customer_data", "email", "format", 0.5),
    ("customer_data", "age", "outlier", 0.2),
    ("customer_data", "customer_id", "duplicate_customer", 1.0),
    ("product_data", "color", "missing", 1.0),
    ("product_data", "net_purchase_price", "outlier", 0.2),
    ("order_data", "payment_provider", "missing", 0.5),
    ("order_data", "quantity", "outlier", 0.1),
    ("order_data", "order_line_id", "duplicate_row", 0.5),
]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Anomalies (labelled events for anomaly and fraud detection):

# Anomalies are part of the shop's behaviour and are on by default. Each one is listed in anomaly_data;
# fraudulent order lines also carry is_fraud = True.
inject_anomalies = True

# Fraud rings: a stolen account places a burst of orders within a few days. Most are expensive, paid by card and sent
# to one of the ring's drop addresses, but no single sign is always there: some parcels go to a locker near the
# customer's home, some orders are paid with BLIK or a deferred payment, and half of the rings start with a cheap
# test order. Detection rules catch most rings, not all of them.
fraud_order_share = 0.004
fraud_orders_per_account = (3, 8)
fraud_burst_days = 3
fraud_category_weights = {"Electronics": 0.75, "Jewelry & Accessories": 0.25}
fraud_drop_addresses = (1, 3)  # postal codes a ring ships to (min, max)
fraud_home_area_share = 0.2  # orders sent to a parcel locker in the customer's own postal code
fraud_payment_methods = {"Card": 0.75, "BLIK": 0.15, "Deferred payment": 0.10}
fraud_test_order_share = 0.5  # rings whose first order is a cheap test of the account
fraud_delivery_methods = {"InPost courier": 0.35, "DPD": 0.35, "InPost parcel locker": 0.30}
fraud_channels = {"direct": 0.5, "organic_search": 0.3, "paid_search": 0.2}

# Shop outages: on these days the shop is down; most orders of the day come back on the next two days.
shop_outages_per_year = 1
outage_kept_order_share = 0.05
outage_recovery_days = 2

# Share of legitimate orders shipped to another address than the customer's (gifts, work address).
other_shipping_address_share = 0.06
# Share of those orders that go to the customer's second address (work, family), the same one each time; the rest are
# gifts to random addresses.
second_address_share = 0.7
