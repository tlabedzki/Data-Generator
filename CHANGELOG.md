# Changelog of Data Generator

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

### Unreleased
Changed:
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
- Added local Codex instructions to avoid reading large files from the `export` directory.

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
