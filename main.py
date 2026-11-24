"""
Generate synthetic e-commerce data (15 linked tables: customers, products, orders, sales lines, competitor prices,
sessions, experiments and more) and save it to the `export/` directory.

All parameters live in the `settings/` package; see `docs/settings.md`.
"""
from func import generator, log

if __name__ == "__main__":
    log.configure()
    generator.generate_full_sales_data()
