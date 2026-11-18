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


PACK_NAMES = {"E": "Dirty data and anomalies", "A": "Customer behaviour", "D": "Prices, promotions, returns and shipping",
              "B": "Basket and preferences", "C": "Marketing and traffic", "F": "A/B experiments"}
HEADLINES = [  # (pack, start of the check label in scripts/check_realism.py, wording in the README)
    ("A", "order growth first to last year", "Orders grow year over year (setting: 20% a year)"),
    ("D", f"Black Friday {s.end_year}", f"Black Friday {s.end_year} against an average November day"),
    ("D", f"25 December {s.end_year}", f"Christmas Day {s.end_year} against an average December day"),
    ("A", "revenue share of the top 10% customers", "Revenue from the top 10% of customers"),
    ("A", "cohort retention month 1 / month 12", "Cohort retention after 1 and 12 months"),
    ("B", "lift Laptop + Wireless Mouse", "Lift of laptop and wireless mouse in one basket (orders)"),
    ("D", "return rate Clothing / Electronics", "Return rate, Clothing against Electronics"),
    ("C", "social share of orders on social campaign days", "Social orders on social campaign days against other days"),
    ("F", "checkout_redesign: conversion lift", "A/B test with a true +10% lift: measured lift and 95% CI"),
    ("E", "fraud order value / other orders", "Labelled fraud orders: value against other orders (orders)"),
]


def realism_checks(datasets):
    """Run every criterion of scripts/check_realism.py on the README run and return (pack, label, value, passed)."""
    import check_realism as cr  # noqa: E402  (scripts/ is on sys.path; the import silences the generator log)

    rows = []
    original = cr.check
    cr.check = lambda pack, label, value, passed: rows.append((pack, label, str(value), bool(passed)))
    try:
        for check_pack in cr.PACKS.values():
            check_pack(datasets)
    finally:
        cr.check = original
    return rows


def realism_block(rows):
    """Headline criteria as a table, then every criterion in a collapsed list."""
    passed = sum(row[3] for row in rows)
    found = {}
    for pack, label, value, _ in rows:
        found.setdefault((pack, label), value)
    lines = ["| What a real shop does | Default run |", "|---|---|"]
    for pack, prefix, wording in HEADLINES:
        value = next(v for (p, label), v in found.items() if p == pack and label.startswith(prefix))
        lines.append(f"| {wording} | **{value}** |")
    lines += ["", f"<details><summary>All {len(rows)} realism criteria ({passed} pass)</summary>", ""]
    for pack, name in PACK_NAMES.items():
        lines += [f"**{name}**", ""]
        lines += [f"- {'✅' if ok else '❌'} {label}: {value}" for p, label, value, ok in rows if p == pack]
        lines.append("")
    lines += ["`python scripts/check_realism.py` runs the same criteria and exits with 1 when any of them fails.", "",
              "</details>"]
    return "\n".join(lines), passed, len(rows)


def results_block(datasets, weights):
    sales = datasets["sales_data"]
    texts = {"monthly-revenue": ch.monthly_revenue_text(sales), "weekday-profile": ch.weekday_text(sales, weights),
             "category-mix": ch.category_text(sales)}
    parts = []
    for stem, takeaway in CHARTS:
        parts += [picture(stem, texts[stem][0]), "", wrap(takeaway(sales, weights)), ""]
    table, passed, total = realism_block(realism_checks(datasets))
    parts += [wrap(f"Beyond the charts, {passed} of {total} realism criteria pass on the same run. The table shows ten "
                   "of them; the list under it shows all."), "", table]
    return "\n".join(parts)


def cli_block(datasets):
    sales = datasets["sales_data"]
    years = sorted(sales["order_date"].dt.year.unique())
    period = f"{years[0]} and {years[-1]}" if len(years) == 2 else f"{years[0]} to {years[-1]}"
    return wrap(f"`python main.py` writes {nf.number(len(datasets['customer_data']))} customers, "
            f"{nf.number(len(datasets['product_data']))} products and {nf.number(len(sales))} order lines "
            f"({nf.number(sales['order_id'].nunique())} orders in {period}) with seed 42 and Polish values, and saves "
            f"{len(s.generated_files)} tables as {s.saving_format.capitalize()} files in `export/`.")


def update_readme(path, blocks):
    """Replace the text between each pair of generated markers in README.md."""
    text = "\n".join(Path(path).read_text(encoding="utf-8").splitlines()) + "\n"
    for name, content in blocks.items():
        pattern = re.compile(rf"(<!-- generated:{name} -->\n).*?(<!-- /generated:{name} -->)", re.S)
        if not pattern.search(text):
            raise SystemExit(f"README.md has no <!-- generated:{name} --> block")
        text = pattern.sub(lambda m: f"{m.group(1)}\n{content}\n\n{m.group(2)}", text)
    Path(path).write_text(text, encoding="utf-8", newline="\n")
