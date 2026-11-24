# Changelog of Data Generator

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

### [Unreleased] - proposed 1.7.1 (after 1.7.0)
Fixed:
- Net prices now equal the gross price without 23% VAT in every row: `sales_price_net` in `product_data` and `price_history`, `unit_price_net` in `order_data`, `price_net` in `competitor_prices` and the net columns of `sales_data`. Until 1.7.0 the net price was the target price before the list price was rounded to end in 9, so gross / net ran from 1.18 to 4.33 instead of 1.23 (for example 129 PLN gross with 97.18 PLN net, now 104.88 PLN).
- `sales_margin` is the margin the list price really leaves, 1 - `net_purchase_price` / `sales_price_net`; the drawn margin only sets the price before rounding.
- The market price of competitors comes from the corrected net prices, so `competitor_prices` changes a little: 636,646 rows instead of 636,742 in the default run, with other prices and `true_market_price_gross`.

Changed:
- Seed 42 gives the same list prices with VAT, orders, quantities, shipments, returns, payments and shop costs as 1.7.0; only the net prices, `sales_margin` and the competitor prices differ. 3 tests in `tests/test_vat.py`, one of them showing that a single wrong net price is caught.

### 1.7.0 - 2026-11-24
Added:
- The shop's own selling costs, in PLN without VAT, from the rates in `settings/commerce_settings.py` (section Shop costs, described in `docs/settings.md`). The rates are the truth: every cost follows from them except the units written off after a return, so costs spread over products add up to the cost columns to the grosz.
- `payment_data`, the 16th table: one payment per order (also cancelled and failed ones) with `payment_amount` (lines after discount plus the delivery fee), `fee_rate` by payment method (BLIK 1.2%, card 1.6%, deferred payment 3.5%), `fixed_fee` by operator and `payment_fee`. Cash on delivery has no operator fee, a declined card costs 0.30 PLN, and the operator keeps its fee when an order is refunded.
- `product_data.parcel_size` (small, medium, large or bulky, by category and product type) and, in `shipment_data`, the parcel size of the shipment and `carrier_cost`: what the carrier charges the shop by delivery method and parcel size, plus 1% + 2 PLN for cash on delivery. A free delivery still costs the shop (11.33 PLN on average in the default run).
- In `return_data`: `return_shipping_cost` (the return label, paid by the shop except for changed_mind), `handling_cost`, `written_off_quantity` (units that cannot be sold again, drawn by return reason: defective 85%, changed_mind 5%) and `write_off_cost` at the purchase price.
- `order_data.affiliate_commission`: commission of the affiliate network by category (3% to 10%) on the units of an affiliate order that the customer kept; 0 for other channels and for cancelled or failed orders.
- 6 realism criteria in a new pack I (shop costs) of `scripts/check_realism.py`, 81 in all; 8 tests in `tests/test_costs.py`, one of them showing that changing the cost settings changes only the cost columns. A row in What you can analyse and a sentence on the shop's costs under the sample.

Changed:
- Nothing in the earlier columns: the new columns sit at the end of `product_data`, `order_data`, `shipment_data`, `return_data` and `sales_data`, and the written-off units draw from their own random stream. Seed 42 gives the other 10 tables exactly as in 1.6.0, byte for byte, and every 1.6.0 column of the five changed tables with the same values in the same place.

### 1.6.0 - 2026-11-24
Added:
- A fifth competitor in `competitor_prices`: Fulmina, a flash sale shop (`competitor_strategy` flash_sale). Its regular price sits at level 1.02 and it sells 40% of products. On top of that it runs 8 random sales a year, 2 to 5 days each, plus one from Black Friday to Cyber Monday; each offer joins an ordinary sale with chance 0.3 (0.6 on Black Friday) at 15, 20, 25 or 30% off its price on the day before, and the regular price comes back the day after. In the default run 2.6% of Fulmina's offer-days are on sale and its average level with sales is 1.015.
- Column `is_promotion` in `competitor_prices`: True for a Fulmina sale price, False for every other row. `true_price_level` is the regular level, sale prices aside.
- 5 realism criteria in pack H (five shops, sale discount, sale length, days on sale and Black Friday, no sales at other shops), 75 in all; 4 tests in `tests/test_competitors.py`, one of them fails when there are not five shops or when names or strategies repeat.

Changed:
- New names for the four shops: Frugalia (discounter, was Taniutko), Aequo (matcher, was Parytet), Maison Orvelle (premium, was Wrzos Atelier) and Mercatoria (marketplace, was Targowo). Their ids, prices and periods are the same as in 1.5.0.
- `competitor_prices` has 636,742 rows in the default run (421,393 in 1.5.0) and `competitor_price_id` is renumbered, since Fulmina's rows sit among the others by product. Seed 42 gives the other 14 tables exactly as in 1.5.0, byte for byte.

### 1.5.0 - 2026-11-24
Added:
- `competitor_prices`, the 15th table: list prices of the same products at four fictional competing shops, with validity periods like `price_history` (`valid_from`, `valid_to`, `change_type`). Taniutko (discounter, price level 0.92, sells 55% of products), Parytet (matcher, 1.00, 70%), Wrzos Atelier (premium, 1.08, 40%) and Targowo (marketplace, 0.97, 80%) each have their own noise, number of price changes and price ending. The matcher follows our list price changes 3 to 14 days later. 421,393 rows in the default run.
- The market price of a product comes from its cost (the median markup of its product type), not from our price, so our price lands above the market for some products and below it for others: in the default run 93% of products are priced between 0.8 and 1.25 times the median competitor price.
- Truth columns `competitor_strategy`, `true_price_level` and `true_market_price_gross`. The price level of every shop holds on any day, within 0.002 in the default run.
- Settings in `settings/market_settings.py` (section Competitor prices) and a Competitor Prices section in `docs/settings.md`; 5 realism criteria in a new pack H of `scripts/check_realism.py`, 70 in all; 17 tests in `tests/test_competitors.py`; a row in What you can analyse.

Changed:
- Nothing else: competitor prices draw from their own random stream and never change demand, orders or sales. Seed 42 gives the other 14 tables exactly as in 1.4.3, byte for byte.

### 1.4.3 - 2026-11-23
Changed:
- The first sentence of the README and the package description in `pyproject.toml` say the program generates data for the shop, not the shop itself: "Generates data for Lumo, a fully fictional Polish online shop: 14 linked tables, …". The code and the data are unchanged: seed 42 gives the same files as in 1.4.2, byte for byte.

### 1.4.2 - 2026-11-23
Changed:
- The generated shop has a name, Lumo: in the first sentence of the README, in the app heading ("Lumo, a shop that never existed, with data that looks real.") and in the README Data section, which says the name is made up and refers to no company or product of that name. The name is not written to the data: seed 42 gives the same files as in 1.4.1, byte for byte.

### 1.4.1 - 2026-11-19
Changed:
- README charts are one light PNG each, shown the same in GitHub's light and dark themes, as plain images instead of `<picture>`. `scripts/make_charts.py` draws only the light version, on a solid white background with a margin, and `docs/img/*-dark.png` are removed. The animated demo at the top keeps its light and dark frame.
- README: the date of the last change on its last line.

### 1.4.0 - 2026-11-19
Added:
- Order status in `order_data`: `order_status` (`delivered`, `returned`, `cancelled`, `payment_failed`), `payment_status` (`paid`, `refunded`, `failed`, `unpaid`), `cancel_reason` and `cancelled_at`. Payments fail by method (deferred payment 10%, card 3.5%, BLIK 1.2%, cash on delivery never), and about 2.5% of the other orders are cancelled before dispatch, more often with cash on delivery and in November and December, when `out_of_stock` grows. An order is `returned` when every line came back in full and was refunded. Cancelled and failed orders have no shipment, return or review. Settings in `settings/commerce_settings.py`, section Order status.
- `review_data`, the 14th table: 1 to 5 stars for delivered order lines, with a date after delivery and an optional comment from ready sentences (translated to Polish with `data_language = "pl"`). A late delivery and a defect (returned as defective or damaged, or bought in the defective batch of the return spike) lower the rating and make a review more likely; `review_rate` and `review_score_weights` hold the true effect.
- Truth columns for churn and customer value models in `customer_data`: `true_purchase_rate` (repeat orders a year while active, at an average time of the year) and `true_churn_date` (the last day the customer can buy). Repeat orders in the default run match `true_purchase_rate` × active years within 1%.
- 13 realism criteria in a new pack G (order status, reviews and churn) of `scripts/check_realism.py`, 65 in all, and 18 tests in `tests/test_orders_reviews.py`, among them negative ones: no shipment, return or review for a cancelled order, no order after `true_churn_date`, no rating gap once the rating settings are equal.
- README: what the default run already holds besides the analyses (margin, refunds, value of cancelled orders, CAC and ROAS, abandoned carts, vouchers, free delivery, product launches, accounts that never order), as generated numbers under the sample; two rows in What you can analyse (order status, ratings) and the churn truth in the customer row.

Changed:
- The command line writes English values by default (`data_language = "en"`), like the app, the README and the realism checks; `data_language = "pl"` writes Polish ones. The README sample is now exactly what `python main.py` writes.
- Revenue in the charts, the app's key numbers, the README and the realism criteria counts only orders that shipped. `revenue_gross` keeps the value of every order as placed, so cancelled orders stay visible.
- Return rates in the realism criteria are measured on shipped lines. The README criteria table shows failed payments and average ratings instead of Christmas Day and social campaign days, which stay in `docs/realism.md`.
- Seed 42 gives different data than in 1.3.1: shipments, returns and revenue leave out cancelled and failed orders. The other tables and random streams stay as they were.

### 1.3.1 - 2026-11-19
Removed:
- `notebooks/worked_example.ipynb` and `scripts/make_notebook.py` that built it, with their `nbformat`, `nbclient` and `ipykernel` dev dependencies. Analyses of the generated data will live in separate projects; this repository covers the generator.

### 1.3.0 - 2026-11-18
Added:
- `notebooks/worked_example.ipynb`, saved with its outputs: three questions answered from the raw tables and then checked against the truth columns (an A/B test with a sample ratio check, cohort retention and RFM against `customer_segment`, fraud rules scored with precision and recall against `is_fraud`). `scripts/make_notebook.py` writes and runs it; two runs give the same file.
- `docs/columns.md`: every column of every table with its type, an example, its meaning and whether it holds the truth; `docs/realism.md`: all realism criteria with their values; `docs/data-model.md`: the table diagram. `scripts/make_charts.py` writes the first two from the default run.
- `pyproject.toml` with ruff, and a lint step in CI.

Changed:
- A/B tests: variants are now assigned at random before any outcome is known, by complete randomization within strata (day, channel and device for sessions; the day of the first session for customers). The effect is applied afterwards, so A and B have the same traffic mix and the sample ratio test passes clearly when no mismatch is planted (p above 0.9 on the default run; `scripts/check_realism.py` now asks for p > 0.05). Before, converting sessions went to B more often than the others, which skewed the channel and device mix of B. Measured lifts are as noisy as in a real test, and their 95% intervals hold the true effect about 95 times in 100. `checkout_redesign` runs 9 weeks, about the length needed to detect +10% with 80% power.
- Fraud rings are harder to catch: one to three drop addresses per ring, part of the parcels sent to a locker in the customer's own postal code, BLIK and deferred payments next to cards, a cheap test order at the start of half of the rings and several traffic channels. Honest customers ship again and again to a second address of their own. Simple rules now trade precision for recall instead of separating fraud perfectly.
- Default weekday weights are 12-16% (Saturday the quietest) instead of 5-23%. With this, the A/B and the fraud changes, seed 42 gives different data than in 1.2.0.
- Customers and products draw from their own random streams like every other step, instead of NumPy's global random state.
- The command line logs in English through Python's `logging`; the web app, tests and scripts stay silent. Error messages are in English.
- Code: dead code from the first version removed, modules imported by name instead of one-letter aliases, type hints on the public API (`func/service.py`, `run_generation_pipeline`, exports, experiments).
- README: shorter (about 6,700 px on github.com instead of 8,000). The table diagram, the full list of realism criteria and the column details moved to `docs/`; the postal code numbers and the largest city's share of customers are generated like the other numbers. Weekday chart: in a flat week the title names the quietest day.
- README demo: an animated SVG instead of a GIF, built by `scripts/make_demo_svg.py` from screenshots of the app (about 300 KB instead of 1.2 MB, sharp at full width, with a dark-theme frame). It opens on the result, the shop's key numbers and the revenue chart, then the month weights with November dragged up and the parameters; with reduced motion it shows the revenue chart. `scripts/make_demo_gif.py` and `docs/img/app-demo.gif` are removed.
- README: the table of analyses has its own section, What you can analyse, right after Why. Each row starts with the business question it answers, then the method and tables and the column or setting with the true answer. A new row covers seasonality and forecasting.

Removed:
- The exploratory notebook `generated_data_analysis.ipynb` (in Polish, without outputs) and its `itables` dependency.

Fixed:
- Two product types listed a brand twice (Philips desk lamps, Fellowes office chairs), so one of its series was silently dropped from the catalog.
- A fraud ring could place orders on a shop outage day; only its first day was kept clear of outages.

### 1.2.0 - 2026-11-18
Added:
- Nine new tables, 13 in all: `price_history`, `shipment_data`, `return_data`, `campaign_data`, `session_data`, `experiment_data`, `experiment_assignment_data`, `anomaly_data` and `quality_issue_data`. Every table is saved by default.
- Customer behaviour: signup cohorts, segments (`customer_segment`), churn, demographic habits, preferred categories, price tiers, replenishment and products bought together.
- Commerce: special days (Black Friday, Cyber Monday, 11.11, Valentine's Day, Mother's Day, St Nicholas Day, Christmas, Easter), product launch and discontinuation, price history, order time of day, discounts that sell more units, shipping with costs and late deliveries, and returns with reasons.
- Marketing and traffic: channels, campaigns with vouchers and a true daily lift, devices and about 690,000 web sessions with a funnel to the order.
- A/B experiments with a known true effect, a planted sample ratio mismatch and an A/A test.
- Dirty data levels (none, low, medium, high) with every injected issue and its clean value in `quality_issue_data`, and labelled anomalies (fraud rings with `is_fraud`, shop outages, a return spike); the app sets the level under Advanced.
- `scripts/check_realism.py`: 52 realism criteria on the default run; the README lists all of them with the measured values.
- README: a table of analyses to practise with the answer to check against, a diagram of all 13 tables, charts in a dark variant for GitHub's dark theme (`<picture>`) and a Quickstart from `git clone` to a running app.
- `scripts/readme_numbers.py`: `scripts/make_charts.py` also rewrites every number and table in the README from the same run, between `<!-- generated:... -->` markers. `scripts/make_demo_gif.py` records the demo GIF and starts and stops the app itself.
- Notebook section 18 on the advanced tables.

Changed:
- A vectorized order engine with independent random streams per step: Large takes about 5 seconds instead of 33 and `python main.py` about 7 seconds instead of 35. The same seed gives different data than in 1.1.0.
- The app downloads every table, as CSV by default (Parquet as an option).

Fixed:
- The same seed now gives identical data in every Python process: two loops drew random numbers in the order of a set of strings, which changes with `PYTHONHASHSEED`.

### 1.1.0 - 2026-11-18
Added:
- GitHub Actions workflow running the pytest suite on every push to main and on pull requests, with a Tests badge in the README.
- README rewritten to the shared portfolio layout: badges, an app demo GIF as the hero, a stack line, a three-command Quickstart, a sample of `sales_data`, shorter sections and a collapsible project tree.
- Seasonality weights for months and weekdays are set by dragging points up and down on two small charts (mouse or touch), with the value shown live next to the point; they replace the 19 number fields. Restore defaults resets both charts, and on narrow screens all weights are listed under each chart.
- Size presets in the app: Small, Medium (the default) and Large set customers, products and order lines and show the generation time measured on a laptop; any manual change shows Custom.

Changed:
- README images use English number notation (5.1M, 55,123) like the README text; the app keeps Polish notation. The weekday and category charts and the demo come from the same default run, so every number in the README matches.
- Parameters are grouped into Size and Period; the seed and seasonality weights moved to a collapsed Advanced section and the language of values sits just above Generate data, with a note on what it translates.
- The app uses one typeface, Inter (SIL OFL, bundled locally), for text, bold headings and tabular numbers, instead of Bricolage Grotesque headings and Instrument Sans text. README charts and the app screenshot are redrawn.
- Numbers on screen use Polish notation in both data languages: a no-break space between thousands and a decimal comma (1 234,56; 6,6M; 33,4%), in headline numbers, table previews, chart titles, labels, axes, tooltips and input fields. Downloaded files keep the machine format.

### 1.0.0 - 2026-11-17
Added:
- Added a web app in Dash with Mantine (`ui/`, `python -m ui.app`): one page with numbered steps (parameters, preview, charts, download), progress bar, headline numbers, table previews, interactive charts and CSV, Parquet or ZIP downloads. Minimal white look with a teal and copper palette, Bricolage Grotesque headings, Inter numbers and Instrument Sans text (all SIL OFL, bundled locally).
- Added `func/service.py` (validated app parameters on top of the existing generator), `func/export.py` and `func/charts.py` (chart data and conclusion titles shared by the app and the README).
- Added a pytest suite (74 tests): table shapes and ranges, unique IDs and e-mails, joins, seed reproducibility, monthly and weekday seasonality, year-over-year growth, localization, settings validators, app parameters, exports, chart data and the app itself.
- Added `scripts/make_charts.py` and README charts in `docs/img/` (monthly revenue, weekday profile, category mix), rendered from the app's own Plotly figures with headless Chrome.
- Added MIT `LICENSE` and `requirements-dev.txt`.
- Added `scripts/build_postal_codes.py`, which builds `source/pl_postal_code.csv` from ZnajdzKod.pl (PRG GUGiK and TERYT GUS, as of 2026-09-16).

Changed:
- Generated e-mails use the reserved domains `example.com`, `example.org` and `example.net` and are always unique.
- Every generated order keeps its own `order_id`; before, two orders of one customer with the same date, payment and delivery were merged.
- Random customer and product draws include the last ID.
- Generation steps accept an optional progress callback; the output for a given seed is unchanged.
- Replaced the postal code file with 20,553 codes from ZnajdzKod.pl; customers get postal codes weighted by their number of addresses.
- Source and export paths are resolved from the repository root, so the generator runs from any working directory.
- Rewrote `README.md` (now UTF-8) with results, quickstart, data sources and tests.

Removed:
- Removed an unused date shift block in order date generation and the old `png/sales_plot.png`.

### 0.0.6 - 2026-05-12
Added:
- Added selectable generation modes for generating individual datasets or generating source datasets without assembling them.
- Added Polish output localization for generated data values.
- Added second-level category hierarchy with validation against duplicate hierarchy levels.
- Added product names built from product type, brand, series, and model.
- Added realistic product catalog settings with category, product type, brand, series, model, price, and margin controls.
- Added brand share profiles, category revenue mix, seasonality, product popularity, quantity profiles, and discount controls.
- Added professional Polish logging with log levels and richer dataset summaries.
- Added Jupyter notebook for generated data analysis, including `itables`, standardized chart styling, and TOP20 product tables.
- Added local assistant instructions to avoid reading large files from the `export` directory.

Changed:
- Reworked the generation pipeline into clearer stages for customers, products, orders, and assembled sales data.
- Improved market realism for category weights, margins, prices, brand popularity, discounts, payments, deliveries, and sales distribution.
- Updated documentation for settings, language handling, hierarchy, product catalog, generation modes, and analysis workflow.
- Changed logs to Polish.
- Removed grocery products from active generation settings.

Removed:
- Removed the temporary SQLite product database approach and related import scripts, templates, and documentation.

### 0.0.5 - 2024-12-09
Added:
- Added the ability to create export folder if it does not exist.

### 0.0.4 - 2024-12-07
Added:
- Added the ability to generate orders with multiple lines under a single order number, simulating the purchase of several products in one order.

### 0.0.3 - 2024-12-07
Added:
- Modifications of basic settings related to the seasonality of generated orders to increase quality.
- Additional descriptions in the settings file that clearly explain the purpose of each setting.
- Added the ability to define custom payment and delivery methods directly in the `main_settings.py` file.

### 0.0.2 - 2024-12-06
Changed:
- Updated `README.md` file with more information about the project;
- Updated `main_settings` file with more configuration options;
- Updated `requirements.txt` file with new dependencies.

### 0.0.1 - 2024-12-06
Added:
- Initial project setup;
- Customer data generation;
- Product data generation;
- Sales data generation with seasonality;
- Configuration options for data generation in `main_settings` file.
