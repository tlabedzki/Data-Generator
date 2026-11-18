"""
Numbers and tables for README.md, computed from the same default run as the README charts (scripts/make_charts.py).

README.md marks each generated part with `<!-- generated:<name> -->` and `<!-- /generated:<name> -->`; update_readme()
replaces only the text between a pair, so the hand-written text around it stays as it is.
"""
import re
import textwrap
from pathlib import Path

import func.charts as ch
import func.number_format as nf
import settings.main_settings as s
import settings.market_settings as ms

SAMPLE_COLUMNS = ["order_date", "order_id", "category", "product_name", "quantity", "revenue_gross", "city"]
CHARTS = [  # file name stem, function that gives the takeaway sentence under the chart
    ("monthly-revenue", lambda sales, weights: monthly_takeaway(sales)),
    ("weekday-profile", lambda sales, weights: weekday_takeaway(sales, weights)),
    ("category-mix", lambda sales, weights: category_takeaway(sales)),
]


def wrap(text):
    """README source lines stay within 120 characters."""
    return textwrap.fill(text, width=118, break_long_words=False, break_on_hyphens=False)


def pct(value, digits=0):
    return nf.percent(value, digits)


def sample_block(datasets):
    """Three order lines of sales_data as a Markdown table, with one sentence under it."""
    sales = datasets["sales_data"]
    rows = sales.iloc[[0, len(sales) // 3, 2 * len(sales) // 3]][SAMPLE_COLUMNS]
    lines = ["| " + " | ".join(SAMPLE_COLUMNS) + " |", "|" + "---|" * len(SAMPLE_COLUMNS)]
    for _, row in rows.iterrows():
        cells = [f"{row['order_date']:%Y-%m-%d}", str(row["order_id"]), row["category"], row["product_name"],
                 str(row["quantity"]), nf.number(row["revenue_gross"], 2), row["city"]]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", wrap(f"Three of the {nf.number(len(sales))} rows of `sales_data` from the default run with English "
                       f"values. The table has {len(sales.columns)} columns: each order line joined with its customer "
                       "and product.")]
    return "\n".join(lines)


def picture(stem, alt):
    """A chart that follows GitHub's light or dark theme."""
    return (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="docs/img/{stem}-dark.png">\n'
            f'  <img alt="{alt}" src="docs/img/{stem}.png">\n</picture>')


def monthly_takeaway(sales):
    data = ch.monthly_revenue_data(sales)
    peak = data.loc[data["is_peak"]].iloc[0]
    growth = ch.yearly_growth(sales)
    trend = f"grows {pct(growth)} a year and " if growth is not None and growth >= 0 else ""
    return (f"Revenue {trend}peaks at {nf.compact(peak['revenue'])} PLN in {peak['month']:%B %Y}, "
            "the Black Friday month.")


def weekday_takeaway(sales, weights):
    data = ch.weekday_data(sales, weights)
    gap = (data["share"] - data["configured"]).abs().max()
    return (f"Every weekday lands within {nf.number(gap * 100, 1)} percentage points of its configured weight; "
            "the rest is deliberate random noise.")


def category_takeaway(sales):
    data = ch.category_data(sales)
    gap = (data["share"] - data["target"]).abs().max()
    return (f"Category revenue lands within {nf.number(gap * 100, 1)} percentage points of the target mix: the "
            "generator corrects for average price, so expensive categories do not take over revenue just because "
            "their unit prices are high.")


def checks_table(datasets):
    """Patterns that the charts do not show: what the settings ask for and what the default run delivers."""
    sales, products = datasets["sales_data"], datasets["product_data"]
    months, years = sales["order_date"].dt.month, sales["order_date"].dt.year
    monthly = [w / sum(s.base_monthly_seasonality) for w in s.base_monthly_seasonality]
    peak = max(range(12), key=lambda i: monthly[i]) + 1
    peak_name = ch.MONTH_NAMES[peak - 1]
    lines_by_year = sales.groupby(years).size()
    span = s.end_year - s.start_year
    single = s.order_line_number[1] / sum(s.order_line_number.values())
    lines_per_order = sales.groupby("order_id").size()
    discounted = sales["discount_rate"] > 0
    normal_months = ~months.isin([11, 12])
    revenue = sales.groupby("product_id")["revenue_gross"].sum()
    revenue = revenue.reindex(products["product_id"], fill_value=0).sort_values(ascending=False)
    top_share = revenue.iloc[:len(revenue) // 5].sum() / revenue.sum()
    rows = [
        (f"{peak_name} share of order lines", f"{pct(monthly[peak - 1], 1)} (`base_monthly_seasonality`)",
         pct((months == peak).mean(), 1)),
        (f"Order lines in {s.end_year} vs {s.start_year}",
         f"+{pct(s.annual_growth_rate * span)} (`annual_growth_rate`) plus noise",
         f"+{pct(lines_by_year[s.end_year] / lines_by_year[s.start_year] - 1, 1)}"),
        ("Orders with more than one line", f"{pct(1 - single)} (`order_line_number`)",
         pct((lines_per_order > 1).mean())),
        ("Discounted lines, November vs Jan–Oct",
         f"×{nf.number(ms.discount_monthly_multiplier[11], 2)} (`discount_monthly_multiplier`)",
         f"{pct(discounted[months == 11].mean())} vs {pct(discounted[normal_months].mean())}"),
        ("Revenue from the top 20% of products",
         f"long tail (`product_popularity_sigma` = {nf.number(ms.product_popularity_sigma, 2)})", pct(top_share)),
    ]
    lines = ["| Pattern | Settings | Default run |", "|---|---|---|"]
    lines += [f"| {pattern} | {setting} | **{result}** |" for pattern, setting, result in rows]
    return "\n".join(lines)


def results_block(datasets, weights):
    sales = datasets["sales_data"]
    texts = {"monthly-revenue": ch.monthly_revenue_text(sales), "weekday-profile": ch.weekday_text(sales, weights),
             "category-mix": ch.category_text(sales)}
    parts = []
    for stem, takeaway in CHARTS:
        parts += [picture(stem, texts[stem][0]), "", wrap(takeaway(sales, weights)), ""]
    parts += ["The table checks patterns that the charts do not show, against the settings that drive them.", "",
              checks_table(datasets)]
    return "\n".join(parts)


def cli_block(datasets):
    sales = datasets["sales_data"]
    years = sorted(sales["order_date"].dt.year.unique())
    period = f"{years[0]} and {years[-1]}" if len(years) == 2 else f"{years[0]} to {years[-1]}"
    return wrap(f"`python main.py` writes {nf.number(len(datasets['customer_data']))} customers, "
            f"{nf.number(len(datasets['product_data']))} products and {nf.number(len(sales))} order lines "
            f"({nf.number(sales['order_id'].nunique())} orders in {period}) as {s.saving_format.capitalize()} to "
            "`export/` in about half a minute, with seed 42 and Polish values by default.")


def update_readme(path, blocks):
    """Replace the text between each pair of generated markers in README.md."""
    text = "\n".join(Path(path).read_text(encoding="utf-8").splitlines()) + "\n"
    for name, content in blocks.items():
        pattern = re.compile(rf"(<!-- generated:{name} -->\n).*?(<!-- /generated:{name} -->)", re.S)
        if not pattern.search(text):
            raise SystemExit(f"README.md has no <!-- generated:{name} --> block")
        text = pattern.sub(lambda m: f"{m.group(1)}\n{content}\n\n{m.group(2)}", text)
    Path(path).write_text(text, encoding="utf-8", newline="\n")
