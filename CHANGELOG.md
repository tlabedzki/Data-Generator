# Changelog of Data Generator

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
