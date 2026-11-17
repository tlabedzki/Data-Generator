"""
Render the README charts from a fresh run of the generator with the default settings (seed 42).

Usage (from the repository root):
    python scripts/make_charts.py

Charts are written to docs/img/. Display values are generated in English so the charts match the README.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import pandas as pd  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import func.generator as g  # noqa: E402
import settings.main_settings as s  # noqa: E402
import settings.market_settings as ms  # noqa: E402

IMG_DIR = PROJECT_DIR / "docs" / "img"

# Chart tokens (light surface). Categorical slots: blue, orange.
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES_1 = "#2a78d6"
SERIES_2 = "#eb6834"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, length=0, labelsize=10)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def new_figure(width=10, height=5.2):
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    style_axes(ax)
    return fig, ax


def add_titles(fig, title, subtitle):
    fig.text(0.06, 0.95, title, fontsize=15, fontweight="bold", color=TEXT_PRIMARY, ha="left", va="top")
    fig.text(0.06, 0.895, subtitle, fontsize=10.5, color=TEXT_SECONDARY, ha="left", va="top")


def millions(value, _):
    return f"{value / 1e6:.0f}M" if value else "0"


def monthly_revenue_chart(sales):
    revenue = sales.groupby([sales["order_date"].dt.year, sales["order_date"].dt.month])["revenue_gross"].sum()
    by_year = revenue.unstack(level=0)
    growth = by_year[s.end_year].sum() / by_year[s.start_year].sum() - 1

    fig, ax = new_figure()
    for year, color in ((s.start_year, SERIES_1), (s.end_year, SERIES_2)):
        values = by_year[year]
        ax.plot(range(1, 13), values, color=color, linewidth=2, marker="o", markersize=5,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=str(year))
        ax.annotate(f"{year}: {values[11] / 1e6:.1f}M", xy=(11, values[11]), xytext=(-10, 0),
                    textcoords="offset points", ha="right", va="center", fontsize=10, color=TEXT_PRIMARY)

    ax.set_xticks(range(1, 13), MONTHS)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(millions))
    ax.set_ylabel("Gross revenue (PLN)", color=TEXT_SECONDARY, fontsize=10)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left", fontsize=10, labelcolor=TEXT_PRIMARY)
    add_titles(fig, f"Revenue peaks in November and grows {growth:.0%} year over year",
               f"Generated gross revenue by month, {s.start_year}–{s.end_year}, default settings (seed 42, "
               f"annual_growth_rate = {s.annual_growth_rate:.0%} on order volume)")
    fig.subplots_adjust(top=0.82, left=0.08, right=0.97, bottom=0.08)
    fig.savefig(IMG_DIR / "monthly-revenue.png", facecolor=SURFACE)
    plt.close(fig)


def weekday_chart(sales):
    orders = sales.drop_duplicates("order_id")
    generated = orders["order_date"].dt.dayofweek.value_counts(normalize=True).sort_index()
    configured = pd.Series(s.base_weekday_seasonality) / sum(s.base_weekday_seasonality)

    fig, ax = new_figure(height=4.8)
    x = range(7)
    ax.bar(x, generated, width=0.6, color=SERIES_1, label="Generated orders")
    ax.scatter(x, configured, marker="_", s=900, linewidths=2.5, color=TEXT_PRIMARY, zorder=3,
               label="Configured weight")
    ax.set_xticks(list(x), WEEKDAYS)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1, decimals=0))
    ax.set_ylabel("Share of orders", color=TEXT_SECONDARY, fontsize=10)
    ax.set_ylim(0, max(generated.max(), configured.max()) * 1.22)
    ax.legend(frameon=False, loc="upper center", ncol=2, fontsize=10, labelcolor=TEXT_PRIMARY)
    add_titles(fig, "Orders cluster on Sunday and Monday, as configured",
               "Share of generated orders by weekday vs base_weekday_seasonality (noise is added on purpose)")
    fig.subplots_adjust(top=0.80, left=0.08, right=0.97, bottom=0.08)
    fig.savefig(IMG_DIR / "weekday-profile.png", facecolor=SURFACE)
    plt.close(fig)


def category_mix_chart(sales):
    generated = sales.groupby("category")["revenue_gross"].sum()
    generated = generated / generated.sum()
    target = pd.Series(ms.category_revenue_target_weights)
    target = target / target.sum()
    order = generated.sort_values().index

    fig, ax = new_figure(height=6.4)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=1)
    y = range(len(order))
    ax.barh(y, generated[order], height=0.6, color=SERIES_1, label="Generated revenue share")
    ax.scatter(target.reindex(order).fillna(0), y, marker="|", s=260, linewidths=2.5, color=TEXT_PRIMARY,
               zorder=3, label="Target weight")
    ax.set_yticks(list(y), order)
    ax.tick_params(axis="y", labelcolor=TEXT_PRIMARY)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1, decimals=0))
    ax.legend(frameon=False, loc="lower right", fontsize=10, labelcolor=TEXT_PRIMARY)
    add_titles(fig, "Category revenue lands close to the configured mix",
               "Generated share of gross revenue vs category_revenue_target_weights")
    fig.subplots_adjust(top=0.86, left=0.22, right=0.97, bottom=0.06)
    fig.savefig(IMG_DIR / "category-mix.png", facecolor=SURFACE)
    plt.close(fig)


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    s.random_state = 42
    s.data_language = "en"
    s.generated_files = ["sales_data"]
    sales = g.run_generation_pipeline()["sales_data"]

    monthly_revenue_chart(sales)
    weekday_chart(sales)
    category_mix_chart(sales)
    print(f"Charts saved to {IMG_DIR}")


if __name__ == "__main__":
    main()
