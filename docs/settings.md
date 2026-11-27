# Generator Settings Guide

The settings live in the `settings/` package:

- `settings/main_settings.py` controls the generation process.
- `settings/behaviour_settings.py` controls the demand calendar, customer segments, churn, demographics and habits.
- `settings/basket_settings.py` controls products bought together, customer preferences and replenishment.
- `settings/commerce_settings.py` controls special days, product life cycle, price changes, price elasticity, order
  times, shipping, returns, order status (cancellations and failed payments) and reviews.
- `settings/experiment_settings.py` controls A/B experiments.
- `settings/marketing_settings.py` controls channels, campaigns, devices and web sessions.
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
data_language = "en"
```

Available values:

- `"en"` saves display values in English (the default of the command line, the app and the realism checks).
- `"pl"` saves display values in Polish.

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
- gender,
- review comments.

Codes such as `order_status`, `payment_status`, `cancel_reason`, `return_reason` and `channel` stay in English in
both languages, so filters and joins work the same way.

Market logic still uses English technical keys internally. This keeps category weights, brand weights, margins,
discounts, seasonality, and order generation stable. Translation is applied only to the output datasets.

Product series and product models are translated only for generic descriptive values. Real brand, product line,
and model names such as `Galaxy`, `ThinkPad`, `Air Max`, or `Spider-Man` are intentionally preserved.

## Output Files

Use `generated_files` in `settings/main_settings.py`.

```python
generated_files = [
    "customer_data", "product_data", "order_data", "sales_data", "price_history", "competitor_prices", "shipment_data",
    "return_data", "payment_data", "review_data", "campaign_data", "session_data", "experiment_data",
    "experiment_assignment_data", "anomaly_data", "quality_issue_data", "supplier_data", "product_supplier_data",
    "purchase_order_data", "stock_movement_data", "lost_demand_data",
]
```

Available values:

| File | One row is | Notes |
|---|---|---|
| `customer_data` | a customer account | truth for churn models: `true_purchase_rate`, `true_churn_date` |
| `product_data` | a product | `parcel_size` for shipping costs |
| `order_data` | an order line | `order_line_id` is unique unless dirty data duplicates a line; `order_status` per order; `affiliate_commission` |
| `sales_data` | an order line joined with its product and customer | revenue columns added |
| `price_history` | a list price of a product with its validity period | the last price equals `sales_price_gross` |
| `competitor_prices` | a list price of a product at one competing shop, with its validity period | 5 fictional shops, sale prices flagged in `is_promotion`; truth: strategy, price level, market price |
| `shipment_data` | the shipment of an order | only orders that shipped; fee paid by the customer, carrier cost to the shop, dispatch, delivery, late or not |
| `return_data` | a returned order line | reason, quantity, refund; return label, handling and goods written off |
| `payment_data` | the payment of an order | every order; amount charged and the payment operator's fee |
| `review_data` | a rating of a delivered order line | 1-5 stars, date, optional comment |
| `campaign_data` | a marketing campaign | channel, dates, cost, voucher, true effect |
| `session_data` | a web session | about 12 per order; the converting one has `order_id` |
| `experiment_data` | an A/B experiment | unit, metric, window, planned split, true effect |
| `experiment_assignment_data` | a unit (session or customer) in an experiment | variant A or B |
| `anomaly_data` | a labelled anomaly (fraud ring, shop outage, return spike) | the truth for anomaly detection |
| `quality_issue_data` | one injected data quality issue | empty when `data_quality_level = "none"` |
| `supplier_data` | a supplier the shop buys from | order weekdays, promised lead time; truth: mean and spread of the actual lead time |
| `product_supplier_data` | the supplier of a product | pack size and minimum order |
| `purchase_order_data` | a purchase order line | ordered, promised and received dates; express deliveries flagged |
| `stock_movement_data` | a change in the stock of a product | opening, receipt or the day's sales, with the stock after it |
| `lost_demand_data` | an order line lost to an empty shelf | empty unless `stockouts = True` (truth) |

Source tables needed by a selected file are always generated, but only the selected files are saved.

Examples:

```python
generated_files = ["customer_data"]
generated_files = ["customer_data", "product_data", "order_data"]
generated_files = ["sales_data"]
```

## Random Streams

Every step (customers, products, orders, behaviour, prices, competitor prices, sessions, experiments, order status,
reviews, goods written off after returns, suppliers and stock, anomalies, dirty data and so on) draws from its own random stream seeded with `(random_state, stream number)` (`func/rng.py`). Changing one of them, for
example the dirty data level, does not change the random numbers of the other steps. Names, phone numbers and bank
account numbers come from Faker, seeded with `random_state` too.

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
| `fraud_category_weights` | Electronics 0.75, Jewelry 0.25 | what fraudsters buy (expensive products, no discount) |
| `fraud_drop_addresses` | `(1, 3)` | postal codes one ring ships to |
| `fraud_home_area_share` | `0.2` | ring orders sent to a parcel locker in the customer's own postal code |
| `fraud_payment_methods` | Card 0.75, BLIK 0.15, Deferred payment 0.10 | how ring orders are paid |
| `fraud_test_order_share` | `0.5` | rings whose first order is a cheap test of the account |
| `fraud_delivery_methods`, `fraud_channels` | | delivery and traffic channel of ring orders |
| `shop_outages_per_year` | `1` | days when the shop is down (January-October) |
| `outage_kept_order_share` | `0.05` | orders that still go through on the outage day |
| `outage_recovery_days` | `2` | the other orders come back within this many days |
| `other_shipping_address_share` | `0.06` | legitimate orders shipped to another postal code (gifts, work) |
| `second_address_share` | `0.7` | of those, orders sent to the customer's second address (the same one each time) |

`order_data.shipping_postal_code` is the delivery postal code. Most fraud orders ship away from the customer's own
postal code, come in a burst, are expensive and are paid by card, but none of these signs is always there, and honest
customers also ship again and again to a second address. Detection rules therefore trade precision for recall. No
ring places an order on a shop outage day.

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
over its days, so the weekday profile follows `base_weekday_seasonality` (default 12-16%, Saturday the quietest).
Special days and campaigns come on top: Black Friday adds to Fridays and weekly e-mail campaigns to Tuesdays or
Thursdays, so a day can land a point or two away from its weight.

## Customer Behaviour

Customers follow a "buy till you die" model (`func/behaviour.py`, settings in `settings/behaviour_settings.py`):

1. Every customer gets a hidden segment, saved in `customer_data.customer_segment` as the answer for checking a
   segmentation (drop it, `preferred_category` and `price_tier` before clustering).
2. `existing_customer_share` (45%) signed up before the period, spread over `existing_customer_years` (4). The rest
   sign up during the period following the demand calendar; `signup_date` is in `customer_data`.
3. New customers place their first order on the signup day (`first_order_same_day_share`, 60%) or after a short
   delay (`first_order_delay_mean_days`, 10); `no_order_share` (8%) never order.
4. After the first order a customer buys again at a personal rate until their lifetime ends (churn). Rates are
   gamma-distributed inside a segment (`purchase_rate_shape`; lower means more "whales"); lifetimes are exponential.
5. The generator rescales all rates so the total number of order lines matches `order_data_rows`, and divides the
   calendar by the active customer base of each month, so seasonality and growth stay as set while customers churn.
6. Two truth columns in `customer_data` hold the answer for churn and customer value models (BG/NBD, Pareto/NBD):
   `true_purchase_rate` is the number of repeat orders a year the customer places while active, after the
   rescaling and at an average time of the year (0 for one-time buyers); `true_churn_date` is the last day the
   customer can buy. It falls before the period for accounts that were already gone, after it for customers still
   active at the end, and on the signup day for accounts that never order. Shop outages move a few orders by up to
   two days, so an order can land just after it.

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

## Market Basket And Preferences

Settings in `settings/basket_settings.py`.

**Products bought together.** `complements` maps a product type to the types bought with it. In an order with more
than one line, every further line becomes a complement of the first line's type with the given probability:

```python
complements = {
    "Laptop": {"Wireless Mouse": 0.35, "Headphones": 0.12, "Backpack": 0.10},
    "Cat Food": {"Pet Litter": 0.45, "Pet Toy": 0.15},
}
```

**Favourite category.** Every customer has `preferred_category` (drawn with the age and gender affinities);
`category_loyalty` (30%) of their lines come from it. **Price tier.** `price_tier` is `budget`, `standard` or
`premium` (`price_tiers`: share and exponent); the chance to keep a drawn product is multiplied by
`min(1, (price / category median) ** exponent)`, so premium customers buy dearer products. Both columns are hidden
truth in `customer_data` for recommendation and segmentation exercises.

**Replenishment.** `replenishment_products` lists consumables with their cycle in days and the share of loyal and
regular customers who buy them again and again (baby products mostly for customers aged 25-44). Their repeat orders
follow the cycle (±`replenishment_jitter`) and start with the same product. The other repeat orders fill up every
day, so the totals still follow the calendar.

## Special Days

Use `special_days` in `settings/commerce_settings.py`.

```python
special_days = {
    "black_friday": {"dates": "black_friday", "demand": 4.0, "discount": 2.2, "categories": {"Electronics": 1.4}},
    "christmas":    {"dates": ("12-25", "12-26"), "demand": 0.25, "discount": 1.0, "categories": {}},
}
```

| Key | Meaning |
|---|---|
| `dates` | a named movable day (`black_friday`, `black_week`, `cyber_monday`, `easter_sunday`, `easter_monday`) or a `("MM-DD", "MM-DD")` range |
| `demand` | multiplier of the day's orders compared with an average day of its month |
| `discount` | multiplier of the chance that a line is discounted |
| `categories` | multipliers of category probabilities on these days |

The month total does not change: a strong Black Friday takes orders from the rest of November, so the monthly
seasonality stays as set. Defaults: Black Friday, Black Week, Cyber Monday, Singles' Day (11.11), Valentine's,
Mother's Day and Children's Day weeks, Mikołajki, and quiet days at Christmas, New Year and Easter.

## Product Life Cycle And Price History

`product_data` has `launch_date` and `discontinued_date` (empty = still on sale). Products are sold only between
these dates.

| Setting | Default | Meaning |
|---|---|---|
| `launched_during_period_share` | `0.30` | products launched during the period (the rest existed before) |
| `discontinued_share` | `0.15` | products withdrawn before the end of the period |
| `min_product_life_days` | `120` | a discontinued product is on sale at least this long |
| `price_changes_per_year` | `1.2` | list price changes per product and year |
| `price_increase_share` | `0.75` | share of changes that are increases |
| `price_increase_range`, `price_decrease_range` | `(0.02, 0.12)`, `(0.05, 0.20)` | size of a change |

`price_history` lists every list price with `valid_from`, `valid_to` and `change_type` (`initial`, `increase`,
`decrease`). The last price of every product equals `sales_price_gross` in `product_data`. Order lines carry the
list price valid on the order day (`unit_price_gross`, `unit_price_net`); `sales_data` computes the discounted prices
and `revenue_gross` from them.

## Competitor Prices

`competitor_prices` holds the list prices of five fictional shops that sell some of the same products. **The table
only adds data: competitor prices do not change demand, orders, sales or any other table.** It draws from its own
random stream (`competitors`), so seed 42 gives the other 14 tables exactly as without it, and it stays clean at every
`data_quality_level`. Settings in `settings/market_settings.py`, section Competitor prices.

**Market price.** The market price comes from the cost of a product, not from our price: `net_purchase_price` ×
the median `sales_price_net / net_purchase_price` of its product type (of its category when the type has fewer than
`competitor_reference_min_products = 20` products), with 23% VAT. Our margin is drawn per product, so
our price lands above the market for some products and below it for others. `true_market_price_gross` holds it.

**Shops** (`competitor_settings`). A shop's price is the market price × `price_level` × a lasting log-normal noise
per product and shop (mean 1, sd `price_sd`), × (1 + a short-term deviation with sd `change_sd`, drawn again at every
price change). Prices change back and forth around the shop's level instead of drifting away from it, so
`true_price_level` holds on any day.

| Shop | `competitor_strategy` | `price_level` | `price_sd` | `coverage` | Price changes | Ending |
|---|---|---|---|---|---|---|
| Frugalia | discounter | 0.92 | 0.04 | 55% | 1.5 a year | ,99 |
| Aequo | matcher | 1.00 | 0.02 | 70% | follows ours | ,99 |
| Maison Orvelle | premium | 1.08 | 0.05 | 40% | 0.6 a year | 9 (under 20 PLN: ,99) |
| Mercatoria | marketplace | 0.97 | 0.10 | 80% | 3 a year | ,99 |
| Fulmina | flash_sale | 1.02 | 0.05 | 40% | 1 a year, plus sales | ,99 |

The names are made up: a frugal discounter, a matcher that keeps prices *ex aequo* with ours, a premium *maison*, a
marketplace (*mercato*, a market) and a flash sale shop named after lightning (*fulmen*). `coverage` is the chance that
a shop sells a product, drawn once per product and shop, so about 0.9% of products have no competitor offer and about
9% have one. The matcher has no random changes: with `reaction_probability = 0.6` it
follows each of our list price changes in `price_history` after `reaction_delay_days = (3, 14)` days, by the same
ratio, and its price on the last day of sale sits at its level. Endings: `,99` is the nearest x.99 (149.37 → 148.99),
`9` the nearest whole price ending in 9 (153 → 149, 155 → 159).

**Flash sales.** Fulmina keeps its regular price at its level and runs short, deep sales on top of it:
`sale_events_per_year = 8` random sales a year, each `sale_days = (2, 5)` days long, plus one from Black Friday to
Cyber Monday every year. Sales never overlap: a random sale that starts less than `sale_gap_days = 14` days after
another (or near Black Friday) is dropped. In an ordinary sale each offer joins with `sale_share = 0.3`, on Black
Friday with `black_friday_share = 0.6`, and costs one of `sale_discounts = (0.15, 0.20, 0.25, 0.30)` less than its
regular price on the day before. The day after the sale the regular price returns; a regular change that falls inside
a sale starts when it ends. Sale rows have `is_promotion = True` (`change_type` decrease, then increase when the sale
ends); every other row, at every shop, has `False`. `true_price_level` is the regular level, sale prices aside: in the
default run about 2.6% of Fulmina's offer-days are on sale and its average level with sales is 1.015.

An offer lasts while the product is on sale inside the period, from `launch_date` (or the first day of the period) to
`discontinued_date`, also for products that never sell. Periods of one offer follow each other day after day;
`valid_to` is empty only for offers still on sale on the last day. `price_net` is `price_gross / 1.23` (`vat_rate`
in `settings/market_settings.py`). Realism pack H in `scripts/check_realism.py` measures the five shops, levels,
coverage, price index, matcher delays and the flash sales (discount, length, share of days, Black Friday).

## Price Elasticity And Discounts

`category_price_elasticity` (default `default_price_elasticity = 1.2`) sets how strongly demand reacts to price:

- a product's chance to be bought is multiplied by `(list price / its lowest price) ** -elasticity`, so a price
  increase lowers its sales;
- a discount raises the expected quantity of the line by `(1 - discount) ** -elasticity` (extra units are drawn
  from a Poisson distribution, so discounted lines can have more than 5 units).

## Order Time Of Day

`order_data.order_datetime` adds the time to `order_date`. Hours follow `hour_weights` (24 values, busiest between
19:00 and 22:00); fraud orders follow `fraud_hour_weights` (mostly at night).

## Shipping

`shipment_data` has one row per order.

| Setting | Meaning |
|---|---|
| `bulky_product_types` | product types too big for parcel lockers; orders with one of them go by courier (`bulky_delivery_methods`) |
| `delivery_methods` | cost (PLN gross), transit days (min, max) and promised days per delivery method |
| `free_shipping_threshold` | orders from this gross value ship for free (199 PLN) |
| `bulky_shipping_surcharge` | extra cost of a bulky shipment, also above the threshold |
| `dispatch_cutoff_hour` | orders placed before this hour on a working day leave the same day |
| `carrier_delay_share`, `peak_delay_share`, `peak_months`, `peak_extra_days` | delays: 5% of shipments, 25% in November and December |

`promised_delivery_date` counts the promised working days from the dispatch day; `is_late` is True when
`delivered_at` is later.

## Returns

`return_data` has one row per returned order line.

| Setting | Meaning |
|---|---|
| `category_return_rate`, `default_return_rate` | chance that a line is returned (Clothing 24%, Electronics 6%) |
| `segment_return_multiplier`, `discounted_return_multiplier` | deal hunters and discounted lines return more often |
| `return_delay_days`, `return_within_14_days_share` | days from delivery to the return; 85% within 14 days |
| `return_reasons` | reason mix for Clothing (mostly `wrong_size`) and the other categories |
| `return_spikes`, `return_spike_rate`, `return_spike_days` | a defective batch: one popular product is returned 55% of the time for a month, labelled in `anomaly_data` as `return_spike` |

Fraud lines are never returned. 4% of returns are `rejected` with a refund of 0. Lines of cancelled orders and
orders with a failed payment never ship, so they are never returned either.

## Order Status

Every order in `order_data` ends with one `order_status` (the same on all its lines):

| `order_status` | `payment_status` | What happened |
|---|---|---|
| `delivered` | `paid` | shipped and kept, at least in part |
| `returned` | `refunded` | every line came back in full and was refunded |
| `cancelled` | `refunded`, or `unpaid` for cash on delivery | cancelled before dispatch, with `cancel_reason` and `cancelled_at` |
| `payment_failed` | `failed` | the payment did not go through, nothing shipped |

| Setting | Meaning |
|---|---|
| `payment_failure_rate`, `default_payment_failure_rate` | share of orders whose payment fails, by method: deferred payment 10% (credit check), card 3.5%, BLIK 1.2%, cash on delivery 0 |
| `cancellation_rate` | share of the other orders cancelled before dispatch (2.5%) |
| `cod_cancellation_multiplier`, `peak_cancellation_multiplier` | cash on delivery is cancelled 3 times as often, November and December 1.5 times |
| `cancel_reasons`, `peak_out_of_stock_multiplier` | reason mix; `out_of_stock` weighs 3 times more in the peak months |

`cancelled_at` lies between `order_datetime` and the planned dispatch. Cancelled and failed orders have no shipment,
return or review. `revenue_gross` keeps the value of every order as placed, so the realised revenue is the sum over
orders whose `order_status` is `delivered` or `returned` (the README charts and the app count only those), and the
net revenue subtracts `refund_amount` of `return_data`. Fraud orders always go through.

## Reviews

`review_data` has one row per rated order line. Customers rate lines that reached them (not cancelled, not failed,
not fraud), and a bad experience lowers the rating and makes a review more likely. These settings are the answer to
check a rating analysis against.

| Setting | Meaning |
|---|---|
| `defect_return_reasons` | return reasons that make a line `defect` (`defective`, `damaged`); lines of the return spike's defective batch count too, also when kept |
| `review_rate` | chance to review a line by experience: on time 22%, late 35%, defect 55% |
| `review_score_weights` | star mix by experience; on time averages 4.3, late 3.4, defect 1.8 |
| `review_delay_mean_days` | days from delivery to the review (geometric, mean 5) |
| `review_comment_share`, `review_comments` | share of reviews with a comment and the ready sentences; low ratings after a late delivery or a defect name the cause |

A line is `late` when its shipment has `is_late`, `defect` wins over `late`, and the rest is `on_time`. The rating
does not change what the customer buys later.

## Shop Costs

What selling costs the shop beyond the purchase price, in `settings/commerce_settings.py`, section Shop costs. All
amounts are PLN without VAT. These settings are the true rates: every cost column follows from them, except the units
written off after a return, which are drawn unit by unit from their own random stream. So costs spread over products
add up to the cost columns to the grosz, and the tables of 1.6.0 stay as they were: the cost columns are added at
the end of `product_data`, `order_data`, `shipment_data`, `return_data` and `sales_data`, and `payment_data` is new.
Values "without VAT" divide the gross value after discount by `1 + vat_rate`.

| Setting | Meaning |
|---|---|
| `category_parcel_size`, `product_type_parcel_size`, `default_parcel_size` | parcel size of a product (`small`, `medium`, `large`), by category with exceptions by product type; types in `bulky_product_types` are always `bulky` |
| `parcel_size_step_up_units` | a shipment takes the size of its largest product, one size up (at most `large`) from 4 units |
| `carrier_rates`, `default_carrier_rates` | what the carrier charges the shop for one parcel, by delivery method and parcel size: for example 9.20 to 11.40 PLN for an InPost parcel locker, 69 to 95 PLN for a bulky courier parcel |
| `cod_collection_fee` | cash on delivery adds 1% of the amount collected plus 2 PLN to `carrier_cost` |
| `return_label_rates` | return label by parcel size of the product (8.50 small to 79 PLN bulky), one per returned line |
| `shop_paid_return_reasons` | reasons for which the shop pays the label: defective, damaged, wrong_item, not_as_described and wrong_size (free size exchange); for changed_mind the customer pays |
| `return_handling_cost` | 6 PLN per return plus 2 PLN per unit, 25 PLN more for a bulky product; also for rejected returns |
| `write_off_share`, `default_write_off_share` | chance that a unit of a refunded return cannot be sold again: defective 85%, damaged 75%, not_as_described 15%, wrong_item and changed_mind 5%, wrong_size 3%; rejected returns go back to the customer |
| `payment_fee_rate`, `default_payment_fee_rate` | operator's share of the amount by payment method: BLIK 1.2%, card 1.6%, fast transfer 1.1%, deferred payment 3.5%, wallet 1.8%, bank transfer 0.5% |
| `payment_fixed_fee`, `default_payment_fixed_fee` | fixed fee by operator, from 0 (PayPo) to 1.35 PLN (PayPal) |
| `methods_without_operator` | cash on delivery: no operator fee, the carrier's collection fee is in `carrier_cost` |
| `failed_payment_fee` | a declined card costs 0.30 PLN; other failed payments cost nothing |
| `affiliate_commission_rate`, `default_affiliate_commission_rate` | commission of the affiliate network by category (3% Electronics to 10% Clothing and Jewelry & Accessories, 6% otherwise) |

`payment_data` has one row per order, also cancelled and failed ones: `payment_fee = payment_amount × fee_rate +
fixed_fee`. The operator keeps its fee when an order is refunded, and a refund costs nothing. A cancelled
cash-on-delivery order was never charged, so its amount is 0.

`affiliate_commission` is paid on the units of an affiliate order that the customer kept: the network takes back the
commission on refunded units and earns nothing on cancelled or failed orders. It comes on top of the cost of
affiliate campaigns in `campaign_data`, which stays the cost of the campaigns.

The shop's own `carrier_cost` does not depend on `shipping_cost`, the fee the customer pays, so a free delivery (from
199 PLN) still costs the shop. The rates are fictional, set at the level of Polish e-commerce contracts, and refer
to no real price list.

## Suppliers And Stock

Suppliers, purchase orders and stock, in `settings/inventory_settings.py`. Each category has
`suppliers_per_category` suppliers (one when not listed), and its brands are dealt among them, so a brand comes from
one supplier within a category. A supplier ships from Poland, Germany or China (`supplier_origins`, each with a range
of mean lead times), takes orders on one to three weekdays (`order_weekday_count`) and promises its mean lead time,
rounded. The actual lead time of each order is log-normal around the mean with the supplier's spread
(`lead_time_cv`), and deliveries never arrive on Sunday. Every product has a pack size by category (`pack_sizes`,
`default_pack_sizes`) and a minimum order of 1, 2 or 4 packs (`min_order_packs`).

A buyer orders "by eye" at the end of each order day of the supplier: the average daily units sold over
`buyer_history_days`, times the promised lead time, the days until the next order day and `buyer_cover_days`, with a
log-normal spread (`buyer_quantity_sigma`). When the stock on hand and on order is below that, the buyer orders the
difference, rounded up to whole packs and at least the minimum order. A product with no stock and no sales in the
window is noticed and ordered again with the chance `empty_shelf_notice_rate` per order day. The buyer stops
ordering a product that is withdrawn before the next delivery could sell, so a withdrawn product can keep stock that
never sells. Products on sale on the first day start with an opening stock, and products launched later get a first
delivery on their launch day (Saturday when it falls on a Sunday): the buyer's guess of their sales over
`opening_cover_days` or `launch_cover_days`, at least one pack.

Stock goes down on the order day of every order line, first come first served. Two simplifications keep the other
tables as they were: returned units go to an outlet and do not come back to the stock, and cancelled or failed orders
keep their units.

| Setting | Meaning |
|---|---|
| `stockouts` | `False` (default): an express delivery fills an empty shelf the same day (`is_express` in `purchase_order_data`), so every order line is served and the 16 tables of 1.7.1 stay exactly as they were. `True`: a line that does not fit the stock is lost; it leaves `order_data` and every table built on it, and `lost_demand_data` keeps it as the truth |

With `stockouts = True` the sales are lower than the demand. An analysis that forecasts from `order_data` alone sees
fewer sales on the days a product was out of stock and has to tell "nobody wanted it" from "it was not there". The
buyer by eye reacts late to a fast rise in demand, so the most lines are lost around Black Friday and in December. A
session whose whole order was lost keeps no `order_id`, orders are numbered again, and fraud rings and shop outages
in `anomaly_data` describe what happened before the stock check (some of their lines may be lost). The stock tables
are most realistic with a catalog in which most products sell every month: in `scripts/check_realism.py` (pack J),
1,500 products and 100,000 order lines serve about 91% of the units asked for. The default run has 50,000 products,
most of which sell only a few units in two years.

## Marketing And Traffic

Settings in `settings/marketing_settings.py`.

**Campaigns** (`campaign_data`). `campaign_plans` sets one plan per paid channel: always-on paid search every month,
social bursts, weekly e-mails and affiliate campaigns. Every campaign raises demand on its days by `true_daily_lift`
(drawn from `lift`) and a decaying carry-over after it ends (`decay`, adstock). Month totals stay as set, so campaigns
move demand inside the month; special days come on top. `total_cost` splits `marketing_budget_per_order` × expected
orders between channels (`channel_budget_shares`) and campaigns (by their expected reach, ±30%). `true_daily_lift`
is the answer for media mix models.

**Order channel, device, campaign and voucher** (`order_data`). New customers have `acquisition_channel` in
`customer_data`; `first_order_from_acquisition_share` (80%) of their first orders come through it, the rest follow
`first_order_channels`. Repeat orders follow `repeat_order_channels`. On a campaign day a share
`lift / (1 + lift)` of orders comes through the campaign; other orders of its channel on its days are credited to it
too (last click). `voucher_share` of a campaign's orders carry its `voucher_code`. Devices follow `device_shares`
weighted by `device_conversion_multipliers`. Fraud orders follow `fraud_channels` and carry no campaign or voucher.

**Sessions** (`session_data`). Every order has one converting session (`order_id`, also `order_data.session_id`)
that starts a few minutes before the order. Around it there are sessions without an order from the same channel and
device on the same day, so that orders / sessions equals `channel_conversion_rates` × `device_conversion_multipliers`
(email 14%, social 4%, desktop ×1.35, mobile ×0.85). `non_converting_add_to_cart_share` (22%) of them add to the
cart and `non_converting_checkout_share` (35%) of those reach the checkout (abandoned carts);
`known_visitor_share` (45%) belong to a known customer, the rest are anonymous (`customer_id` empty).

The session table is the largest one: about 690,000 rows for the default volume (11 MB as Parquet, 45 MB as CSV).

## A/B Experiments

Use `experiments` in `settings/experiment_settings.py`. Each experiment runs in its own window of the period
(`start_share`, `duration_days`) and has the effect it should show in the data (`true_effect`, the answer to check an
analysis against):

| Key | Meaning |
|---|---|
| `unit` | `session` (every session on its own) or `customer` (all sessions of a known customer; anonymous sessions are left out) |
| `metric` | `conversion_rate` (relative change of session conversion) or `units_per_line` (absolute change of the mean quantity of order lines) |
| `planned_split_b`, `actual_split_b` | the share of units meant for B and the share they get; a difference is a sample ratio mismatch to detect |

Defaults: `checkout_redesign` (+10% conversion), `recommendation_widget` (+0.12 units per line for customers in B),
`free_shipping_banner` (+6% conversion with a sample ratio mismatch: 46% instead of 50% in B) and
`search_ranking_aa` (an A/A test with no effect).

Variants are assigned first, at random and without looking at outcomes: units are shuffled within strata (sessions by
day, channel and device; customers by the day of their first session) and `actual_split_b` of every stratum goes to
B. A and B therefore have the same traffic mix, and with the planned split the sample ratio test passes easily.

The effect comes afterwards. For conversion experiments the orders themselves do not change: a share of the converting
A sessions trade places with B sessions without an order from the same day, channel and device, so B converts
`1 + true_effect` times as often as A on average. For `units_per_line`, order lines of B customers in the window get
extra units. A measured result has the noise of a real test: its 95% confidence interval contains `true_effect` in
about 95 of 100 seeds, and a short test can miss a real effect. `checkout_redesign` runs 9 weeks, about the length
needed to detect +10% with 80% power.

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

The generator draws a margin from the range and turns it into the list price with VAT, rounded to end in 9. The net
price is that list price without VAT, and `sales_margin` is the margin the list price really leaves:

```python
target_net = net_purchase_price / (1 - drawn_margin)
sales_price_gross = round_to_9(target_net * (1 + vat_rate))
sales_price_net = round(sales_price_gross / (1 + vat_rate), 2)
sales_margin = round(1 - net_purchase_price / sales_price_net, 4)
```

Rounding to a price ending in 9 moves the margin a little from the drawn one, more for cheap products. Every net
price in the data (`sales_price_net`, `unit_price_net`, `price_net` and the net columns of `sales_data`) is its gross
price divided by `1 + vat_rate`, to the grosz.

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
