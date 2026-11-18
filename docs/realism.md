# Realism criteria

52 of 52 criteria pass on the default run (seed 42). `python scripts/check_realism.py` runs the same checks and exits
with 1 when any of them fails; `scripts/make_charts.py` writes this page.

## Dirty data and anomalies

- ✅ missing phone_number at medium (expected 1200): 1237
- ✅ missing city at medium (expected 600): 612
- ✅ missing age at medium (expected 600): 619
- ✅ duplicate customers at medium (expected 3% of customers): 1200
- ✅ missing values at none / issues listed: 0 / 0
- ✅ fraud order value / other orders: 15.0x (221 fraud orders)
- ✅ fraud orders shipped to another postal code: 100%
- ✅ orders on outage day 2023-09-04 vs median day: 2%
- ✅ orders on outage day 2024-09-23 vs median day: 6%

## Customer behaviour

- ✅ cohort retention month 1 / month 12: 11.4% / 5.6%
- ✅ orders per customer: variance / mean: 5.14
- ✅ revenue share of the top 10% customers: 68%
- ✅ revenue per customer loyal / occasional: 3,896 / 771 PLN
- ✅ Electronics share of lines, age < 30 / 55+: 5.7% / 3.4%
- ✅ November share of orders vs the calendar (no flattening): 17.6% vs 17.6% (+0.0 pp)
- ✅ November weight over 10 seeds vs setting (noise has no bias): 18.5% vs 18.6% (-0.1 pp)
- ✅ order growth first to last year (setting 20%/year): 19%

## Prices, promotions, returns and shipping

- ✅ Black Friday 2023-11-24 / average November day: 3.4x
- ✅ 25 December 2023 / average December day: 0.33x
- ✅ Black Friday 2024-11-29 / average November day: 3.4x
- ✅ 25 December 2024 / average December day: 0.23x
- ✅ busiest hour of the day: 20:00 (9.6% of orders)
- ✅ units per line with / without discount: 1.96 / 1.60
- ✅ return rate Clothing / Electronics: 27.3% / 5.9%
- ✅ bulky orders in lockers / furniture lines to parcel lockers: 0.0% / 0.0% (was 55.6%)
- ✅ lines sold before launch or after discontinuation: 0
- ✅ line price differs from price_history on the order day (2000 lines): 0
- ✅ products with at least one list price change: 80%
- ✅ late deliveries outside / in November-December: 4.9% / 24.3%

## Basket and preferences

- ✅ lift Laptop + Wireless Mouse: 16.3 (60 orders)
- ✅ lift Smartphone + Headphones: 7.5 (112 orders)
- ✅ lift Office Desk + Office Chair: 43.4 (7 orders)
- ✅ lift Cat Food + Pet Litter (litter is bought by cat owners anyway): 2.7 (102 orders)
- ✅ same first category as the previous order / at random: 36.9% / 17.6%
- ✅ median days between repeat purchases of the same pet food: 28 (1711 repeats)
- ✅ median unit price premium / budget customers: 289 / 179 PLN
- ✅ lines from the customer's preferred category: 42%

## Marketing and traffic

- ✅ orders with a converting session: 100.0% (689,335 sessions)
- ✅ largest relative gap of conversion vs setting (channel x device): 3.7% (email 14.2%)
- ✅ mobile share of sessions: 62.2% vs 62%
- ✅ social share of orders on social campaign days / other days: 2.91x
- ✅ ROAS by channel (attributed revenue / cost): affiliate 5.2, email 21.1, paid_search 5.9, social 8.2
- ✅ marketing cost per order: 70 PLN vs 70
- ✅ carts abandoned (sessions with a cart and no order / all carts): 71%

## A/B experiments

- ✅ checkout_redesign: sample ratio test p-value (mismatch planted: False): 0.92 (B 50.0%)
- ✅ checkout_redesign: conversion lift, 95% CI (true +10%): +4.9% [-1.4%, +11.6%]
- ✅ recommendation_widget: sample ratio test p-value (mismatch planted: False): 0.9 (B 50.1%)
- ✅ recommendation_widget: units per line B - A, 95% CI (true +0.12): +0.079 [+0.010, +0.148]
- ✅ free_shipping_banner: sample ratio test p-value (mismatch planted: True): 4.2e-37 (B 46.0%)
- ✅ free_shipping_banner: conversion lift, 95% CI (true +6%): +3.5% [-4.3%, +11.9%]
- ✅ search_ranking_aa: sample ratio test p-value (mismatch planted: False): 0.97 (B 50.0%)
- ✅ search_ranking_aa: conversion lift, 95% CI (true +0%): +2.5% [-6.8%, +12.7%]
