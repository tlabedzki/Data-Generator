# Realism criteria

98 of 98 criteria pass on the default run (seed 42). `python scripts/check_realism.py` runs the same checks and exits
with 1 when any of them fails; `scripts/make_charts.py` writes this page.

## Dirty data and anomalies

- ✅ missing phone_number at medium (expected 1200): 1237
- ✅ missing city at medium (expected 600): 612
- ✅ missing age at medium (expected 600): 619
- ✅ duplicate customers at medium (expected 3% of customers): 1200
- ✅ missing values at none / issues listed: 0 / 0
- ✅ fraud order value / other orders: 13.9x (221 fraud orders)
- ✅ fraud orders shipped to another postal code (some go to a locker near home): 78%
- ✅ orders on outage day 2023-03-14 vs median day: 3%
- ✅ orders on outage day 2024-08-02 vs median day: 8%

## Customer behaviour

- ✅ cohort retention month 1 / month 12: 11.4% / 5.6%
- ✅ orders per customer: variance / mean: 5.14
- ✅ revenue share of the top 10% customers: 68%
- ✅ revenue per customer loyal / occasional: 3,790 / 701 PLN
- ✅ Electronics share of lines, age < 30 / 55+: 5.6% / 3.5%
- ✅ November share of orders vs the calendar (no flattening): 17.6% vs 17.6% (-0.0 pp)
- ✅ November weight over 10 seeds vs setting (noise has no bias): 18.5% vs 18.6% (-0.1 pp)
- ✅ order growth first to last year (setting 20%/year): 19%

## Prices, promotions, returns and shipping

- ✅ Black Friday 2023-11-24 / average November day: 3.4x
- ✅ 25 December 2023 / average December day: 0.33x
- ✅ Black Friday 2024-11-29 / average November day: 3.4x
- ✅ 25 December 2024 / average December day: 0.23x
- ✅ busiest hour of the day: 20:00 (9.6% of orders)
- ✅ units per line with / without discount: 1.96 / 1.60
- ✅ return rate Clothing / Electronics (shipped lines): 27.0% / 5.5%
- ✅ bulky orders in lockers / furniture lines to parcel lockers: 0.0% / 0.0% (was 55.6%)
- ✅ lines sold before launch or after discontinuation: 0
- ✅ line price differs from price_history on the order day (2000 lines): 0
- ✅ products with at least one list price change: 80%
- ✅ late deliveries outside / in November-December: 5.0% / 24.3%

## Basket and preferences

- ✅ lift Laptop + Wireless Mouse: 16.3 (60 orders)
- ✅ lift Smartphone + Headphones: 7.5 (112 orders)
- ✅ lift Office Desk + Office Chair: 43.4 (7 orders)
- ✅ lift Cat Food + Pet Litter (litter is bought by cat owners anyway): 2.7 (102 orders)
- ✅ same first category as the previous order / at random: 36.8% / 17.7%
- ✅ median days between repeat purchases of the same pet food: 28 (1711 repeats)
- ✅ median unit price premium / budget customers: 289 / 179 PLN
- ✅ lines from the customer's preferred category: 42%

## Marketing and traffic

- ✅ orders with a converting session: 100.0% (690,245 sessions)
- ✅ largest relative gap of conversion vs setting (channel x device): 3.1% (email 14.3%)
- ✅ mobile share of sessions: 62.2% vs 62%
- ✅ social share of orders on social campaign days / other days: 2.85x
- ✅ ROAS by channel (attributed revenue / cost): affiliate 4.9, email 19.5, paid_search 5.5, social 7.7
- ✅ marketing cost per order: 70 PLN vs 70
- ✅ carts abandoned (sessions with a cart and no order / all carts): 72%

## A/B experiments

- ✅ checkout_redesign: sample ratio test p-value (mismatch planted: False): 0.96 (B 50.0%)
- ✅ checkout_redesign: conversion lift, 95% CI (true +10%): +11.3% [+4.6%, +18.4%]
- ✅ recommendation_widget: sample ratio test p-value (mismatch planted: False): 0.93 (B 50.1%)
- ✅ recommendation_widget: units per line B - A, 95% CI (true +0.12): +0.093 [+0.024, +0.162]
- ✅ free_shipping_banner: sample ratio test p-value (mismatch planted: True): 4.4e-37 (B 46.0%)
- ✅ free_shipping_banner: conversion lift, 95% CI (true +6%): +11.7% [+3.4%, +20.7%]
- ✅ search_ranking_aa: sample ratio test p-value (mismatch planted: False): 0.97 (B 50.0%)
- ✅ search_ranking_aa: conversion lift, 95% CI (true +0%): -7.7% [-16.0%, +1.4%]

## Order status, reviews and churn

- ✅ failed payments, deferred payment / BLIK (setting 10% / 1.2%): 9.3% / 1.2%
- ✅ orders cancelled or with a failed payment (settings give about 5%): 5.6%
- ✅ cancelled or failed orders with a shipment, return or review: 0
- ✅ payment status, cancel time or reason that contradicts the order status: 0
- ✅ returned orders / shipped orders refunded in full, line by line: 3661 / 3661
- ✅ out_of_stock share of cancellations, November-December / other months: 41% / 19%
- ✅ average rating on time / late / returned as defective or damaged: 4.29 / 3.42 / 1.84
- ✅ lines reviewed, late / on time (bad experiences get more reviews): 36% / 22%
- ✅ reviews dated on or before delivery, or of lines never delivered: 0
- ✅ ratings with 5 / 1 / 2 stars (J-shaped, as in real shops): 53% / 9% / 6%
- ✅ orders more than 2 days after true_churn_date (outages move orders by up to 2 days): 0 (11 moved by an outage)
- ✅ repeat orders in the period / true_purchase_rate x active years: 1.006
- ✅ churned by the end: buyers silent for the last 180 days / recent buyers: 76% / 26%

## Competitor prices

- ✅ five shops with different names and strategies: Frugalia discounter / Aequo matcher / Maison Orvelle premium / Mercatoria marketplace / Fulmina flash_sale
- ✅ regular price level to the market price on the last day, Frugalia / Aequo / Maison Orvelle / Mercatoria / Fulmina (true_price_level 0.92 / 1.00 / 1.08 / 0.97 / 1.02): 0.921 / 1.000 / 1.080 / 0.970 / 1.021
- ✅ products each shop sells (settings 55% / 70% / 40% / 80% / 40%): 55% / 70% / 40% / 80% / 40%
- ✅ our price / median competitor price between 0.8 and 1.25; below 0.95 / above 1.05: 94%; 29% / 38%
- ✅ competitor price periods with a gap or an overlap: 0
- ✅ Aequo price changes made 3-14 days after one of ours: 100%
- ✅ sale prices outside Fulmina: 0
- ✅ Fulmina sale discount to the price before, from 50 PLN (settings 15%-30%): min / mean / max: 13.5% / 22.5% / 31.5%
- ✅ Fulmina sales 2-5 days long; back to the price before: 2-5 days; 99%
- ✅ Fulmina offer-days on sale; offers on sale on Black Friday 2024; average level with sales: 2.6%; 59%; 1.015

## Shop costs

- ✅ free shipments that still cost the shop; carrier cost per shipment, free / paid by the customer: 100%; 11.33 / 15.43 PLN
- ✅ carrier cost of a bulky shipment / any other: 6.8
- ✅ returned units written off, defective / damaged / changed_mind / wrong_size (settings 85% / 75% / 5% / 3%): 85% / 76% / 6% / 3%
- ✅ payment fee / amount paid, BLIK / Card / Deferred payment (rates 1.2% / 1.6% / 3.5% plus a fixed fee): 1.24% / 1.63% / 3.53%
- ✅ affiliate commission / affiliate net revenue; commission outside the affiliate channel: 6.3%; 0
- ✅ shop costs / net revenue of shipped orders: carrier / returns / payments / commission: 1.6% / 1.7% / 2.0% / 0.6%

## Suppliers and stock

- ✅ mean lead time / true mean, 24 suppliers with 20+ orders (lowest / highest): 0.96 / 1.08
- ✅ regular purchase orders received after the promised date: 34%
- ✅ mean lead time by origin, CN / DE / PL: 33.0 / 6.8 / 3.7 days
- ✅ stockouts off: units that came by express delivery / all units received: 7.6%
- ✅ stockouts on (1,500 products): units served / units asked for: 90.9%
- ✅ stockouts on: lost share of demand, November-December / other months: 14.0% / 6.6%
- ✅ stockouts on: stock value at the end in products with no sale in the last 90 days: 26%
- ✅ stockouts on: sessions linked to an order / orders: 66,069 / 66,069

## Markdowns, clearance and the outlet

- ✅ markdowns off (default): markdown_data and outlet_data: 0 / 0 rows
- ✅ products with a slow-stock markdown (2 years) / clearance markdowns: 57% / 212
- ✅ mean slow-stock markdown against the setting: 27.8% / 27.5%
- ✅ demand in markdowns / the same days without markdowns × true_uplift: 0.96
- ✅ measured uplift by markdown depth, up to 25% / 25-45% / over 45%: 1.25 / 1.80 / 2.75
- ✅ order lines and lost lines, without / with markdowns (lines move, none are added): 100,420 / 100,420
- ✅ withdrawn stock sold in clearance / sold in clearance or to the outlet: 65%
- ✅ outlet pays / purchase value of the stock it takes: 30%
- ✅ stock value at the end in products with no sale in the last 90 days, without / with markdowns: 26% / 15%
