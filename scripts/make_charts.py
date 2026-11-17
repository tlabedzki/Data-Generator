"""
Render the README charts from a fresh run of the generator with the default settings (seed 42).

Usage (from the repository root, after `pip install -r requirements-dev.txt`):
    python scripts/make_charts.py

The charts come from func/charts.py, the same code the Streamlit app uses. PNG files are written to docs/img/.
"""
import sys
from pathlib import Path

import vl_convert as vlc

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import func.charts as ch  # noqa: E402
import settings.main_settings as s  # noqa: E402
from func import service  # noqa: E402

IMG_DIR = PROJECT_DIR / "docs" / "img"
WIDTH = 760
SCALE = 2


def default_params():
    """Default command-line settings with English display values."""
    return service.GenerationParams(
        customers=s.customer_data_rows,
        products=s.product_data_rows,
        order_lines=s.order_data_rows,
        seed=42,
        language="en",
    )


def save_png(chart, file_name):
    png = vlc.vegalite_to_png(chart.to_json(), scale=SCALE)
    (IMG_DIR / file_name).write_bytes(png)


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    params = default_params()
    datasets = service.generate(params)
    sales = datasets["sales_data"]

    save_png(ch.monthly_revenue_chart(sales, width=WIDTH), "monthly-revenue.png")
    save_png(ch.weekday_chart(sales, params.weekday_seasonality, width=WIDTH), "weekday-profile.png")
    save_png(ch.category_chart(sales, width=WIDTH), "category-mix.png")
    for title, subtitle in (ch.monthly_revenue_text(sales), ch.weekday_text(sales, params.weekday_seasonality),
                            ch.category_text(sales)):
        print(f"{title} | {' '.join(subtitle)}")
    print(f"Charts saved to {IMG_DIR}")


if __name__ == "__main__":
    main()
