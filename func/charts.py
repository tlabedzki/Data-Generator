"""
Chart data, chart titles and headline numbers computed from generated data. The app (ui/figures.py draws the charts)
and scripts/make_charts.py (the same charts as PNG files for the README) both read them from here.

Each chart title states the conclusion; the subtitle says what is measured.
"""
import pandas as pd

import func.number_format as nf
import settings.localization as loc
import settings.market_settings as ms

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_NAMES = dict(zip(WEEKDAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))


# ---------------------------------------------------------------------------------------------------------------- #
# Headline numbers

def headline_numbers(datasets):
    """Return the key numbers shown above the charts."""
    sales = datasets["sales_data"]
    order_revenue = sales.groupby("order_id")["revenue_gross"].sum()
    return {
        "orders": int(sales["order_id"].nunique()),
        "order_lines": int(len(sales)),
        "customers": int(len(datasets["customer_data"])),
        "products": int(len(datasets["product_data"])),
        "revenue": float(sales["revenue_gross"].sum()),
        "average_order_value": float(order_revenue.mean()),
        "discounted_line_share": float((sales["discount_rate"] > 0).mean()),
        "first_date": sales["order_date"].min(),
        "last_date": sales["order_date"].max(),
    }


def yearly_growth(sales):
    """Average yearly revenue growth between the first and the last year, or None for a single year."""
    yearly = sales.groupby(sales["order_date"].dt.year)["revenue_gross"].sum()
    if len(yearly) < 2 or yearly.iloc[0] <= 0:
        return None
    return (yearly.iloc[-1] / yearly.iloc[0]) ** (1 / (len(yearly) - 1)) - 1


def compact_number(value):
    return nf.compact(value)


# ---------------------------------------------------------------------------------------------------------------- #
# Chart data

def monthly_revenue_data(sales):
    monthly = sales.set_index("order_date")["revenue_gross"].resample("MS").sum()
    data = monthly.rename("revenue").rename_axis("month").reset_index()
    data["is_peak"] = data["revenue"] == data["revenue"].max()
    return data


def weekday_data(sales, configured_weights):
    orders = sales.drop_duplicates("order_id")
    generated = orders["order_date"].dt.dayofweek.value_counts(normalize=True).reindex(range(7), fill_value=0)
    configured = pd.Series(configured_weights, dtype=float)
    configured = configured / configured.sum()
    data = pd.DataFrame({
        "weekday": WEEKDAYS,
        "day_name": [WEEKDAY_NAMES[day] for day in WEEKDAYS],
        "share": generated.to_numpy(),
        "configured": configured.to_numpy(),
    })
    data["is_top"] = data.index == data["share"].idxmax()  # one highlighted day, also on a tie
    return data


def category_data(sales, language="en"):
    generated = sales.groupby("category")["revenue_gross"].sum()
    generated = generated / generated.sum()
    target = pd.Series(ms.category_revenue_target_weights, dtype=float)
    target = target / target.sum()
    if language != "en":
        target.index = target.index.map(lambda name: loc.translations[language]["category"].get(name, name))
    data = pd.DataFrame({"share": generated, "target": target}).fillna(0.0)
    data = data.rename_axis("category").reset_index().sort_values("share", ascending=False).reset_index(drop=True)
    data["is_top"] = data.index == 0
    return data


# ---------------------------------------------------------------------------------------------------------------- #
# Chart titles

def monthly_revenue_text(sales):
    """Title (the conclusion) and subtitle lines of the monthly revenue chart."""
    data = monthly_revenue_data(sales)
    peak_month = MONTH_NAMES[sales.groupby(sales["order_date"].dt.month)["revenue_gross"].sum().idxmax() - 1]
    growth = yearly_growth(sales)
    if growth is not None:
        direction = "grow" if growth >= 0 else "shrink"
        title = f"Sales {direction} {nf.percent(abs(growth), 0)} a year, peaking in {peak_month}"
    else:
        title = f"Sales peak in {peak_month}"
    return title, [f"Gross revenue by month in PLN, {data['month'].min():%b %Y} to {data['month'].max():%b %Y}"]


def weekday_text(sales, configured_weights):
    """Title (the conclusion) and subtitle lines of the weekday chart."""
    data = weekday_data(sales, configured_weights)
    top = data.loc[data["is_top"]].iloc[0]
    low = data.loc[data["share"].idxmin()]
    title = f"{top['day_name']} brings {nf.percent(top['share'], 0)} of orders"
    return title, [f"Share of orders by weekday; {low['day_name']} is the quietest with "
                   f"{nf.percent(low['share'], 0)}.",
                   "Thin marks show the configured weights."]


def category_text(sales, language="en"):
    """Title (the conclusion) and subtitle lines of the category chart."""
    data = category_data(sales, language)
    top = data.iloc[0]
    gap = (data["share"] - data["target"]).abs().max()
    title = f"{top['category']} earns {nf.percent(top['share'], 0)} of revenue"
    return title, ["Share of gross revenue by category.",
                   f"Thin marks show the target mix (largest gap {nf.number(gap * 100, 1)} pp)."]
