# Generator Settings Guide

The settings live in the `settings/` package:

- `settings/main_settings.py` controls the generation process.
- `settings/behaviour_settings.py` controls the demand calendar, customer segments, churn, demographics and habits.
- `settings/quality_settings.py` controls dirty data (data quality issues) and labelled anomalies.
- `settings/market_settings.py` controls market behavior, products, categories, brands, prices, margins, payments, deliveries, discounts, and sales mix.
- `settings/category_hierarchy.py` controls second-level categories.
- `settings/product_catalog.py` controls product types, product names, type-level prices, type-level margins, series, and models.
- `settings/localization.py` controls translations used in generated output files.

## Reproducibility

Use `random_state` in `settings/main_settings.py`.

```python
random_state = 42
```

Set a number to make generated data repeatable. Set `None` to generate different data on every run.

## Generated Data Language

Use `data_language` in `settings/main_settings.py`.

```python
data_language = "pl"
```

Available values:

- `"pl"` saves display values in Polish.
- `"en"` saves display values in English.

The translation dictionaries are in `settings/localization.py`. They currently cover:

- categories,
- subcategories,
- product types,
- product names,
- selected product series and product models,
- colors,
- payment methods,
- payment providers,
- delivery methods,
- gender.

Market logic still uses English technical keys internally. This keeps category weights, brand weights, margins,
discounts, seasonality, and order generation stable. Translation is applied only to the output datasets.

Product series and product models are translated only for generic descriptive values. Real brand, product line,
and model names such as `Galaxy`, `ThinkPad`, `Air Max`, or `Spider-Man` are intentionally preserved.

## Output Files

Use `generated_files` in `settings/main_settings.py`.

```python
generated_files = ["customer_data", "product_data", "order_data", "sales_data", "anomaly_data", "quality_issue_data"]
```

Available values:

| File | One row is | Notes |
|---|---|---|
| `customer_data` | a customer account | |
| `product_data` | a product | |
| `order_data` | an order line | `order_line_id` is unique unless dirty data duplicates a line |
| `sales_data` | an order line joined with its product and customer | revenue columns added |
| `anomaly_data` | a labelled anomaly (fraud ring, shop outage) | the truth for anomaly detection |
| `quality_issue_data` | one injected data quality issue | empty when `data_quality_level = "none"` |

Source tables needed by a selected file are always generated, but only the selected files are saved.

Examples:

```python
generated_files = ["customer_data"]
generated_files = ["customer_data", "product_data", "order_data"]
generated_files = ["sales_data"]
```

## Random Streams

Every step added after the first version (anomalies, dirty data and the later behaviour models) draws from its own
random stream seeded with `(random_state, stream number)` (`func/rng.py`). Changing one of them, for example the dirty
data level, does not change the random numbers of the other steps.

## Data Quality Issues (Dirty Data)

Use `data_quality_level` in `settings/quality_settings.py`. In the app it is **Advanced → Dirty data**.

```python
data_quality_level = "none"   # "none", "low", "medium" or "high"
```

`data_quality_rates` gives the base share of rows affected by one issue type at each level (1%, 3% and 8% by
default). `data_quality_issues` lists the issue types as `(table, column, issue type, multiplier)`; the share of rows
with an issue is `rate × multiplier`.

| Issue type | What happens | Columns by default |
|---|---|---|
| `missing` | the value is removed (empty cell) | phone, e-mail, city, age, product colour, payment provider |
| `typo` | city in lower or upper case, without Polish letters, with swapped letters or extra spaces | city |
| `format` | the same value written differently: `600-100-200`, `0048600100200`, `00123`, e-mail in capitals or with spaces | phone, postal code, e-mail |
| `outlier` | an impossible value: age 0 or 150, quantity 50-500, purchase price entered in grosze (×100) | age, quantity, net purchase price |
| `duplicate_customer` | the same person gets a second account with a new ID and a slightly different e-mail; about half of their repeat orders move to it | customers |
| `duplicate_row` | an order line is saved twice with the same `order_line_id` | order lines |

Issues are injected into the source tables before the sales lines are joined, so `sales_data` is dirty in the same
way. Every issue has a row in `quality_issue_data`:

| Column | Meaning |
|---|---|
| `table_name`, `key_column`, `key_value` | where the issue is (for example `customer_data`, `customer_id`, `100123`) |
| `column_name`, `issue_type` | what is wrong |
| `dirty_value`, `clean_value` | the value in the file and the correct one (for a duplicate customer: new and original ID) |

## Anomalies

Anomalies are part of the shop's behaviour and are on by default (`inject_anomalies = True` in
`settings/quality_settings.py`). Each one has a row in `anomaly_data`; fraudulent order lines also have
`is_fraud = True` in `order_data` and `sales_data`.

| Setting | Default | Meaning |
|---|---|---|
| `fraud_order_share` | `0.004` | share of orders placed from stolen accounts |
| `fraud_orders_per_account` | `(3, 8)` | orders in one burst |
| `fraud_burst_days` | `3` | days over which a burst is spread |
| `fraud_category_weights` | Electronics 0.75, Jewelry 0.25 | what fraudsters buy (expensive products, paid by card, no discount) |
| `shop_outages_per_year` | `1` | days when the shop is down (January-October) |
| `outage_kept_order_share` | `0.05` | orders that still go through on the outage day |
| `outage_recovery_days` | `2` | the other orders come back within this many days |
| `other_shipping_address_share` | `0.06` | legitimate orders shipped to another postal code (gifts, work) |

`order_data.shipping_postal_code` is the delivery postal code. Fraud orders ship to a postal code far from the
customer's own, which makes them detectable together with the burst and the order value.

## Volumes

Use these settings in `settings/main_settings.py`:

```python
customer_data_rows = 40000
product_data_rows = 50000
order_data_rows = 80000
```

`order_data_rows` is the target number of order lines. The final number can be slightly higher because complete multi-line orders are generated.

## Demand Calendar

Order dates come from a daily calendar (`func/calendar.py`). A day's weight is:

```text
year weight (1 + annual_growth_rate × years since start) × month weight × weekday weight within the month
```

The month weights are `base_monthly_seasonality` with one random fluctuation per month and year
(`monthly_noise_sd = 0.03` in `settings/behaviour_settings.py`, a multiplicative factor around 1.0). Month totals
therefore follow the settings closely; across seeds the fluctuation averages out. Weekday weights split each month
over its days, so the weekday profile follows `base_weekday_seasonality`.

## Customer Behaviour

Customers follow a "buy till you die" model (`func/behaviour.py`, settings in `settings/behaviour_settings.py`):

1. Every customer gets a hidden segment, saved in `customer_data.customer_segment` as the answer for checking a
   segmentation (drop it before clustering).
2. `existing_customer_share` (45%) signed up before the period, spread over `existing_customer_years` (4). The rest
   sign up during the period following the demand calendar; `signup_date` is in `customer_data`.
3. New customers place their first order on the signup day (`first_order_same_day_share`, 60%) or after a short
   delay (`first_order_delay_mean_days`, 10); `no_order_share` (8%) never order.
4. After the first order a customer buys again at a personal rate until their lifetime ends (churn). Rates are
   gamma-distributed inside a segment (`purchase_rate_shape`; lower means more "whales"); lifetimes are exponential.
5. The generator rescales all rates so the total number of order lines matches `order_data_rows`, and divides the
   calendar by the active customer base of each month, so seasonality and growth stay as set while customers churn.

```python
customer_segments = {
    "loyal":       {"share": 0.10, "orders_per_year": 6.0, "lifetime_days": 1600, "discount_affinity": 0.8,
                    "promo_month_power": 0.0},
    "deal_hunter": {"share": 0.15, "orders_per_year": 3.0, "lifetime_days": 500, "discount_affinity": 2.6,
                    "promo_month_power": 2.0},
    # regular, occasional, one_time ...
}
```

| Key | Meaning |
|---|---|
| `share` | share of customers (normalized) |
| `orders_per_year` | relative purchase frequency of an active customer; `0` means one order only |
| `lifetime_days` | mean time from the first order until the customer stops buying |
| `discount_affinity` | multiplier of the chance that the customer's order line is discounted |
| `promo_month_power` | the customer buys more in promotional months: `discount_monthly_multiplier ** power` |

What this gives in the data: cohort retention falls after the first month, orders per customer are over-dispersed
(a few customers place many orders), revenue per customer differs strongly by segment, and deal hunters buy mostly
with discounts and in November.

The ratio of customers to order lines still matters: fewer customers per line means more repeat orders.

## Demographics And Habits

`age_category_affinity` and `gender_category_affinity` multiply category probabilities for the customer of the
order line (keys: upper age of a group, or `"Female"` / `"Male"`; missing categories keep `1.0`). Young customers buy
more electronics and clothing, older ones more health, home and DIY products.

Customers keep habits: `usual_payment_share` (70%) of orders are paid with the customer's usual method and
`usual_delivery_share` (60%) delivered the usual way. Orders above `high_value_order_threshold` (2000 PLN gross) use
`high_value_payment_multipliers`, so expensive orders are paid more often with deferred payment or card.

## Category Catalog Mix

Use `categories_with_probabilities` in `settings/market_settings.py`.

This controls how often categories appear in the product catalog.

```python
categories_with_probabilities = {
    "Electronics": 0.16,
    "Clothing": 0.23,
}
```

Values are normalized automatically.

## Category Hierarchy

Use `subcategory_by_product_type` in `settings/category_hierarchy.py`.

The product hierarchy is:

```text
category -> subcategory -> product_type -> brand -> product_series -> product_model
```

Example:

```text
Electronics -> Mobile Phones -> Smartphone -> Samsung -> Galaxy -> S23
Clothing -> Lifestyle Footwear -> Sneakers -> Adidas -> Grand Court -> Cloudfoam
Books & Media -> Literature and Non-Fiction -> Book -> Znak -> Reportaz -> Paperback
```

`subcategory` should describe the assortment segment. `product_type` should describe the concrete product form.
Do not duplicate levels, for example `Books -> Book`. The validator blocks cases where `subcategory` duplicates
`category` or `product_type`.

```python
subcategory_by_product_type = {
    "Electronics": {
        "Smartphone": "Mobile Phones",
        "Laptop": "Computers",
    },
}
```

## Category Revenue Mix

Use `category_revenue_target_weights` in `settings/market_settings.py`.

This controls the intended category mix in sales revenue. The generator adjusts this by average category price so expensive categories do not dominate only because unit prices are high.

```python
category_revenue_target_weights = {
    "Electronics": 0.215,
    "Clothing": 0.325,
}
```

Values are normalized automatically.

## Category Seasonality

Use `category_monthly_seasonality` in `settings/market_settings.py`.

```python
category_monthly_seasonality = {
    "Toys": {11: 1.45, 12: 1.80},
    "Sports": {5: 1.25, 6: 1.30},
}
```

Month numbers use `1` for January and `12` for December. Values above `1.0` increase category sales probability in that month.

## Brands

Brands are configured in two layers:

1. `categories_brands` defines which brands exist in each category.
2. `brand_weight_profiles` defines brand share tiers inside each category.

Example:

```python
brand_weight_profiles = {
    "Electronics": [
        (["Samsung", "Apple", "Xiaomi"], 0.45),
        (["HP", "Dell", "Asus"], 0.30),
        (["Other Brand"], 0.25),
    ],
}
```

Each tier weight is split equally between brands in that tier.

## Brand Sales Effect

Use `brand_sales_weight_power` in `settings/market_settings.py`.

```python
brand_sales_weight_power = 0.70
```

Higher values make stronger brands sell more often. Lower values reduce the brand effect in sales.

## Product Popularity

Use `product_popularity_sigma` in `settings/market_settings.py`.

```python
product_popularity_sigma = 1.10
```

Higher values create a stronger long-tail effect where a small number of products sell much more often.

## Prices And Margins

Product prices and margins are controlled at product type level in `settings/product_catalog.py`.

Every product type has:

```python
"Smartphone": {
    "weight": 0.30,
    "price_range": (450, 4200),
    "margin_range": (0.10, 0.24),
    "brand_series_models": {
        "Samsung": {"Galaxy": ["S23", "S24"]},
    },
}
```

Product names always use this format:

```text
product_type brand product_series product_model
```

Example:

```text
Smartphone Samsung Galaxy S23
```

Every product must have a non-empty series and model.

Older category-level `price_ranges` and `margin_ranges` in `settings/market_settings.py` are retained as market-level reference ranges, but product generation uses `settings/product_catalog.py`.

`price_range` controls net purchase cost ranges in PLN.

```python
"price_range": (450, 4200)
```

`margin_range` controls gross margin on net sales price, not markup.

```python
"margin_range": (0.10, 0.24)
```

The generator calculates net sales price as:

```python
sales_price_net = net_purchase_price / (1 - sales_margin)
```

## Quantity Per Order Line

There are two layers:

- `quantity_per_order_line` in `settings/main_settings.py` is the fallback profile.
- `category_quantity_profiles` in `settings/market_settings.py` overrides quantity behavior by category.

Example:

```python
category_quantity_profiles = {
    "Pet Supplies": {1: 0.50, 2: 0.25, 3: 0.14, 4: 0.07, 5: 0.04},
}
```

## Discounts

Discounts are controlled in `settings/market_settings.py`.

`discount_probability_by_category` controls how often a category receives a discount.

```python
discount_probability_by_category = {
    "Clothing": 0.32,
}
```

`discount_rate_ranges` controls discount depth.

```python
discount_rate_ranges = {
    "low": (0.03, 0.10),
    "regular": (0.10, 0.25),
    "deep": (0.25, 0.45),
}
```

`discount_monthly_multiplier` changes discount intensity by month.

```python
discount_monthly_multiplier = {
    11: 1.65,
    12: 1.35,
}
```

## Payments And Delivery

Payment method and payment provider are separate.

```python
payment_method_with_probabilities = {
    "BLIK": 0.42,
    "Card": 0.22,
}

payment_provider_with_probabilities = {
    "PayU": 0.30,
    "Przelewy24": 0.28,
}
```

Delivery is controlled by:

```python
delivery_method_with_probabilities = {
    "InPost parcel locker": 0.54,
}
```

All probability dictionaries are normalized automatically.
