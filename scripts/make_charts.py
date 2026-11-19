"""
Render the README charts and numbers from a fresh run of the generator with the default settings (seed 42).

Usage (from the repository root):
    python scripts/make_charts.py

The charts are the app's own Plotly figures (ui/figures.py) with the app's fonts and titles, so the README shows
exactly what the app draws. Numbers use English notation (5.1M, 55,123) like the README text; the app itself writes
them in Polish notation. Each chart becomes a small HTML page that headless Chrome or Edge saves as PNG to docs/img/,
in the app's light colors on a solid white background, so it looks the same in GitHub's light and dark themes.
The numbers and tables in README.md come from scripts/readme_numbers.py and replace the text between its
`<!-- generated:... -->` markers.
Set CHROME to the browser executable if it is not found automatically.
"""
import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import data_dictionary  # noqa: E402  (scripts/ is on sys.path when this file runs)
import readme_numbers  # noqa: E402

import func.charts as ch  # noqa: E402
import func.number_format as nf  # noqa: E402
import settings.main_settings as s  # noqa: E402
from func import customer, service  # noqa: E402
from ui import figures  # noqa: E402

IMG_DIR = PROJECT_DIR / "docs" / "img"
ASSETS = PROJECT_DIR / "ui" / "assets"
WIDTH = 800
SCALE = 2
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "chromium-browser",
]


def default_params():
    """Default command-line settings with English display values."""
    return service.GenerationParams(
        customers=s.customer_data_rows,
        products=s.product_data_rows,
        order_lines=s.order_data_rows,
        seed=42,
        language="en",
    )


def find_browser():
    candidates = [os.environ.get("CHROME")] + BROWSERS
    for candidate in filter(None, candidates):
        path = candidate if Path(candidate).is_file() else shutil.which(candidate)
        if path:
            return path
    sys.exit("Chrome, Chromium or Edge not found. Set CHROME to the browser executable.")


def chart_page(text, figure):
    """HTML page with the chart title, subtitle and figure in the app style and fonts."""
    title, subtitle = text
    fonts = (ASSETS / "fonts.css").read_text(encoding="utf-8")
    fonts = fonts.replace("url('fonts/", f"url('{(ASSETS / 'fonts').as_uri()}/")
    style = (ASSETS / "style.css").read_text(encoding="utf-8")
    figure.update_layout(width=WIDTH - 48)
    body = figure.to_html(full_html=False, include_plotlyjs=True, config={"staticPlot": True})
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts}\n{style}\n"
            f"body {{ margin: 0; }} .dg-chart {{ padding: 28px 24px 16px; width: {WIDTH - 48}px; }}"
            "</style></head>"
            f"<body><figure class='dg-chart'><figcaption><div class='dg-chart-title'>{html.escape(title)}</div>"
            f"<div class='dg-chart-sub'>{html.escape(' '.join(subtitle))}</div></figcaption>"
            f"<div class='dg-graph'>{body}</div></figure></body></html>")


def save_png(browser, page, height, file_name):
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "chart.html"
        source.write_text(page, encoding="utf-8")
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}",
                        f"--window-size={WIDTH},{height}", f"--force-device-scale-factor={SCALE}",
                        "--virtual-time-budget=5000", f"--screenshot={IMG_DIR / file_name}", source.as_uri()],
                       check=True, capture_output=True)


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    params = default_params()
    datasets = service.generate(params)
    sales = datasets["sales_data"]
    weights = params.weekday_seasonality
    with nf.notation("en"):
        charts = [
            ("monthly-revenue", ch.monthly_revenue_text(sales), figures.monthly_revenue(sales)),
            ("weekday-profile", ch.weekday_text(sales, weights), figures.weekday_profile(sales, weights)),
            ("category-mix", ch.category_text(sales), figures.category_mix(sales)),
        ]
    for name, text, figure in charts:
        height = int(figure.layout.height) + 130
        save_png(browser, chart_page(text, figure), height, f"{name}.png")
        print(f"{name}.png: {text[0]} | {' '.join(text[1])}")
    print(f"Charts saved to {IMG_DIR}")
    rows = readme_numbers.realism_checks(datasets)
    with nf.notation("en"):
        blocks = {"sample": readme_numbers.sample_block(datasets),
                  "metrics": readme_numbers.metrics_block(datasets),
                  "results": readme_numbers.results_block(datasets, weights, rows),
                  "cli": readme_numbers.cli_block(datasets),
                  "data": readme_numbers.data_block(datasets, customer.code_df)}
    readme_numbers.update_readme(PROJECT_DIR / "README.md", blocks)
    data_dictionary.write(PROJECT_DIR / "docs" / "columns.md", data_dictionary.columns_markdown(datasets))
    data_dictionary.write(PROJECT_DIR / "docs" / "realism.md",
                          data_dictionary.realism_markdown(rows, readme_numbers.PACK_NAMES))
    print("README.md numbers, docs/columns.md and docs/realism.md updated")


if __name__ == "__main__":
    main()
