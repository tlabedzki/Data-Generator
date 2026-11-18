# Data Generator

[![Tests](https://github.com/tlabedzki/Data-Generator/actions/workflows/tests.yml/badge.svg)](https://github.com/tlabedzki/Data-Generator/actions/workflows/tests.yml)
![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
[![Release](https://img.shields.io/github/v/release/tlabedzki/Data-Generator)](https://github.com/tlabedzki/Data-Generator/releases)

Generates a fully fictional Polish online shop as 13 linked tables, from orders to web sessions, returns and A/B
tests, for analytics practice.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/app-demo-dark.svg">
  <img alt="The app, illustrated: the generated shop's key numbers and revenue chart, then the parameters, Large and Generate, and November dragged up on the month weights to reshape the season" src="docs/img/app-demo.svg">
</picture>

**Stack:** Python · pandas · NumPy · Faker · Dash with Mantine · Plotly · pytest

## Why

Real shop data is private, and public sets are small, too clean or missing the answer. Data Generator gives
analysts, trainers and BI teams a shop that behaves like a real one: customers who come back or churn, Black Friday
peaks, baskets of products bought together, campaigns that move traffic and A/B tests with a known true effect.
Truth columns hold the right answer, so you can check your analysis, and a Large dataset takes about 5 seconds.

## What you can analyse

Each row starts with a question a shop asks; the last column says where the true answer sits.

| Question | Method and tables | Answer to check against |
|---|---|---|
| How fast do sales grow, and how big is the November peak? | Seasonality and forecasting on `sales_data` | `annual_growth_rate`, `base_monthly_seasonality`, `special_days` in `settings/` |
| Which customers come back, and which churn and when? | Cohort retention, RFM and customer value on `customer_data`, `sales_data` | `customer_segment` |
| Which products are bought together? | Market basket analysis (support, confidence, lift) on `sales_data` | `complements` in `settings/basket_settings.py` |
| Which channel brings the orders, and did the campaign pay for itself? | Funnel, attribution and ROAS on `session_data`, `campaign_data`, `order_data` | `true_daily_lift` per campaign |
| Is the A/B test result real? | Significance test, confidence interval, sample ratio mismatch and A/A test on `experiment_data`, `experiment_assignment_data`, `session_data` | `true_effect`, `has_sample_ratio_mismatch` |
| Do discounts sell more, and what drives returns and late deliveries? | Price elasticity, promotion uplift, return and delivery rates on `sales_data`, `price_history`, `return_data`, `shipment_data` | settings in `docs/settings.md` |
| Which orders are fraud, and when did the shop go down? | Fraud and anomaly detection on `order_data`, `anomaly_data` | `is_fraud`, `anomaly_data` |
| Can you trust the data before you analyse it? | Data cleaning (missing values, typos, formats, outliers, duplicates) on every table at `data_quality_level` low, medium or high | `quality_issue_data` (clean values) |

## What it does

- Generates 13 linked tables: customers, products, order lines, sales lines, price history, shipments, returns,
  campaigns, web sessions, experiments, experiment assignments, anomalies and data quality issues.
- Models customers over time: signup cohorts, segments, churn, preferred categories, replenishment and products
  bought together.
- Shapes demand with monthly and weekday seasonality, special days, hours of the day, price changes, discounts that
  sell more units, returns and late deliveries in the peak season.
- Adds channels, campaigns, devices, a session funnel and randomized A/B tests, plus labelled fraud, shop outages and
  optional dirty data.
- Saves CSV or Parquet with values in English or Polish; the same seed gives identical files.

<!-- generated:sample -->

| order_date | order_id | category | product_name | quantity | revenue_gross | city |
|---|---|---|---|---|---|---|
| 2023-01-01 | 100001 | Clothing | T-Shirt H&M Basic Cotton | 1 | 179.00 | Iława |
| 2023-11-11 | 118441 | Clothing | Dress Reserved Elegant Floral | 1 | 523.02 | Gdańsk |
| 2024-06-28 | 136911 | Health | Vitamin Supplement Olimp Labs Gold Vita-Min | 2 | 282.30 | Pobiedziska |

Three of the 80,326 rows of `sales_data` (53 columns: each order line joined with its customer and product) from the
default run with English values.

<!-- /generated:sample -->

## Results

Every chart and number below comes from the default run (seed 42). `python scripts/make_charts.py` regenerates the
data, redraws the charts in light and dark versions and rewrites the numbers in this README and in `docs/`;
`python scripts/make_demo_svg.py` builds the animated demo at the top from screenshots of the app.

<!-- generated:results -->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/monthly-revenue-dark.png">
  <img alt="Sales grow 23% a year, peaking in November" src="docs/img/monthly-revenue.png">
</picture>

Revenue grows 23% a year and peaks at 5.2M PLN in November 2024, the Black Friday month.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/weekday-profile-dark.png">
  <img alt="Saturday is the quietest day, with 12% of orders" src="docs/img/weekday-profile.png">
</picture>

Every weekday lands within 1.6 percentage points of its configured weight: special days such as Black Friday and the
weekly e-mail campaigns on Tuesdays or Thursdays move it, as they would in a real shop.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/category-mix-dark.png">
  <img alt="Clothing earns 33% of revenue" src="docs/img/category-mix.png">
</picture>

Category revenue lands within 3.1 percentage points of the target mix: the generator corrects for average price, so
expensive categories do not take over revenue just because their unit prices are high.

Beyond the charts, 52 of 52 realism criteria pass on the same run. The table shows ten of them;
[docs/realism.md](docs/realism.md) lists all with their values.

| What a real shop does | Default run |
|---|---|
| Orders grow year over year (setting: 20% a year) | **19%** |
| Black Friday 2024 against an average November day | **3.4x** |
| Christmas Day 2024 against an average December day | **0.23x** |
| Revenue from the top 10% of customers | **68%** |
| Cohort retention after 1 and 12 months | **11.4% / 5.6%** |
| Lift of laptop and wireless mouse in one basket (orders) | **16.3 (60 orders)** |
| Return rate, Clothing against Electronics | **27.0% / 5.7%** |
| Social orders on social campaign days against other days | **2.85x** |
| A/B test with a true +10% lift: measured lift and 95% CI | **+11.3% [+4.6%, +18.4%]** |
| Labelled fraud orders: value against other orders (orders) | **13.9x (221 fraud orders)** |

<!-- /generated:results -->

## Quickstart

You need Git and Python 3.11. Clone the repository:

```bash
git clone https://github.com/tlabedzki/Data-Generator.git
cd Data-Generator
```

Create and activate a virtual environment. Naming the version picks Python 3.11 even if another one is the default.

| Step | Windows (PowerShell) | macOS and Linux |
|---|---|---|
| Create | `py -3.11 -m venv .venv` | `python3.11 -m venv .venv` |
| Activate | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| Check | `python --version` prints `Python 3.11.x` | `python --version` prints `Python 3.11.x` |

If PowerShell says that running scripts is disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once
and activate again. Then install the packages and start the app:

```bash
pip install -r requirements.txt
python -m ui.app
```

Open http://127.0.0.1:8050 in your browser. The app starts at step 1, the parameters; press Ctrl+C in the terminal to
stop it.

### Command line

<!-- generated:cli -->

`python main.py` writes 40,000 customers, 50,000 products and 80,326 order lines (55,568 orders in 2023 and 2024) with
seed 42 and Polish values, and saves 13 tables as Parquet files in `export/`.

<!-- /generated:cli -->

It takes about 7 seconds on a laptop. Every option lives in `settings/` and [docs/settings.md](docs/settings.md)
describes it; `data_quality_level` in `settings/quality_settings.py` turns on dirty data.

### App

The app walks you through four steps: parameters, preview, charts and downloads. Pick a size (Small under a second,
Medium about 1 second, Large about 5 seconds), set the years and growth, and open **Advanced** for the seed, the dirty
data level and the month and weekday weights, which you drag. Every table downloads as CSV or Parquet, one by one or
as a ZIP.

## Data

All people, e-mails, phone numbers, bank account numbers, products, prices and sales are synthetic: generated by
`func/` with [Faker](https://faker.readthedocs.io/) (`pl_PL`) and NumPy, seed 42. E-mail addresses use the reserved
domains `example.com`, `example.org` and `example.net`. [docs/data-model.md](docs/data-model.md) shows how the 13
tables link, and [docs/columns.md](docs/columns.md) describes every column and marks the truth columns.

Brand, payment and delivery names (for example Samsung, H&M, PayU, BLIK and InPost) are used only as labels to make
the data look familiar. Products, prices, margins, popularity and market shares are fictional and say nothing about
these companies.

<!-- generated:data -->

Customer addresses take a real postal code and its main locality from `source/pl_postal_code.csv` (20,553 Polish
postal codes, 3,413 localities), drawn with a weight equal to the number of addresses. Addresses count buildings
rather than residents, so cities with large apartment blocks get fewer customers than their population would suggest:
Warszawa has 1.6% of customers.

<!-- /generated:data -->

Source: [ZnajdzKod.pl](https://znajdzkod.pl/baza-kodow-pocztowych/) na podstawie PRG (GUGiK) i TERYT (GUS),
stan 16.09.2026 (attribution in Polish, as required by the source). The site allows downloading, processing and
publishing its files with this attribution; `scripts/build_postal_codes.py` rebuilds the file from
`kody-pocztowe.csv`.

## Project structure

<details><summary>Show the tree</summary>

```
main.py       command-line entry point
ui/           web app (Dash with Mantine)
func/         generation steps, the app service, charts and exports
settings/     every parameter, described in docs/settings.md
source/       postal codes with localities and address counts
scripts/      realism criteria, README charts and numbers, demo, postal code import
docs/         settings, data model, columns, realism criteria, README images
tests/        pytest suite
```

</details>

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

178 pytest tests (about 30 seconds) check table shapes, joins, seed reproducibility, seasonality, customer behaviour,
prices and returns, marketing, experiments, dirty data, exports and the app's callbacks and figures on small samples.
`ruff check .` lints the code and CI runs both on every push; `python scripts/check_realism.py` checks the realism
criteria on the full default run.

## License

MIT, see [LICENSE](LICENSE). [Changelog](CHANGELOG.md).
