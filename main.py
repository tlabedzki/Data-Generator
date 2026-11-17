"""
Generate synthetic e-commerce data (customers, products, orders and joined sales lines)
and save it to the `export/` directory.

All parameters live in the `settings/` package; see `docs/settings.md`.
"""
import func.generator as g


if __name__ == "__main__":
    g.generate_full_sales_data()
