"""
Charts and headline numbers computed from generated data. Used by the Streamlit app (interactive) and by
scripts/make_charts.py (static PNG files for the README), so both always look the same.

Style: one accent colour for the single point each chart is about, warm greys for everything else, the conclusion
in the title, direct labels instead of legends, hairline grids and rounded bar ends.
"""
import altair as alt
import pandas as pd

import settings.localization as loc
import settings.market_settings as ms

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#8a8983"
GRID = "#ebeae6"
ACCENT = "#2a78d6"
ACCENT_WASH = "#2a78d61f"
MUTED_MARK = "#cfcdc6"
TARGET_MARK = "#3d3c39"
FONT = "Segoe UI, Helvetica Neue, Arial, sans-serif"

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_NAMES = dict(zip(WEEKDAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))
TOOLTIP_PERCENT = ".1%"


def _config(chart, width, height):
    return (
        chart.properties(width=width, height=height, background=SURFACE,
                         padding={"left": 4, "right": 24, "top": 8, "bottom": 4})
        .configure_view(stroke=None)
        .configure_axis(
            labelColor=TEXT_SECONDARY, titleColor=TEXT_SECONDARY, labelFont=FONT, titleFont=FONT, labelFontSize=12,
            titleFontSize=12, titleFontWeight="normal", gridColor=GRID, gridWidth=1, domain=False, ticks=False,
            labelPadding=8,
        )
        .configure_axisX(grid=False)
        .configure_title(font=FONT, fontSize=19, fontWeight=600, color=TEXT_PRIMARY, anchor="start",
                         subtitleFont=FONT, subtitleFontSize=13, subtitleColor=TEXT_SECONDARY, subtitlePadding=6,
                         offset=22)
    )


def _with_title(chart, titled, text):
    """Put the title inside the chart (static images) or leave it to the page (the app wraps long titles)."""
    if not titled:
        return chart
    title, subtitle = text
    return chart.properties(title=alt.TitleParams(text=title, subtitle=subtitle))


def _label(chart, **kwargs):
    """Text mark in the chart font; text never takes the accent colour."""
    style = {"font": FONT, "fontSize": 12, "color": TEXT_PRIMARY}
    style.update(kwargs)
    return chart.mark_text(**style)


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
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= limit:
            return f"{value / limit:.1f}{suffix}"
    return f"{value:,.0f}"


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
    data["is_top"] = data["share"] == data["share"].max()
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
# Charts

def monthly_revenue_text(sales):
    """Title (the conclusion) and subtitle lines of the monthly revenue chart."""
    data = monthly_revenue_data(sales)
    peak_month = MONTH_NAMES[sales.groupby(sales["order_date"].dt.month)["revenue_gross"].sum().idxmax() - 1]
    growth = yearly_growth(sales)
    if growth is not None:
        direction = "grow" if growth >= 0 else "shrink"
        title = f"Sales {direction} {abs(growth):.0%} a year, peaking in {peak_month}"
    else:
        title = f"Sales peak in {peak_month}"
    return title, [f"Gross revenue by month in PLN, {data['month'].min():%b %Y} to {data['month'].max():%b %Y}"]


def monthly_revenue_chart(sales, width=760, height=320, titled=True):
    """Hero chart: monthly revenue over the whole period, with the peak month marked and labelled."""
    data = monthly_revenue_data(sales)
    peak = data.loc[data["is_peak"]].iloc[0]

    x = alt.X("month:T", title=None, axis=alt.Axis(format="%b %Y", labelAngle=0, tickCount={"interval": "month", "step": 6},
                                                 labelOverlap=True, labelColor=TEXT_MUTED))
    y = alt.Y("revenue:Q", title=None, scale=alt.Scale(zero=True, nice=True),
              axis=alt.Axis(tickCount=4, labelColor=TEXT_MUTED,
                            labelExpr="datum.value == 0 ? '0' : format(datum.value, '~s')"))
    base = alt.Chart(data).encode(x=x)
    area = base.mark_area(color=ACCENT_WASH, interpolate="monotone").encode(y=y)
    line = base.mark_line(color=ACCENT, strokeWidth=2.5, interpolate="monotone", strokeCap="round").encode(y="revenue:Q")

    hover = alt.selection_point(fields=["month"], nearest=True, on="pointerover", empty=False, clear="pointerout")
    hover_rule = base.mark_rule(color=MUTED_MARK, strokeWidth=1).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("month:T", title="Month", format="%B %Y"),
                 alt.Tooltip("revenue:Q", title="Revenue (PLN)", format=",.0f")],
    ).add_params(hover)
    hover_dot = base.mark_point(filled=True, size=60, color=ACCENT, stroke=SURFACE, strokeWidth=2, opacity=1).encode(
        y="revenue:Q", opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    )

    peak_data = data.loc[data["is_peak"]].assign(label=f"{peak['month']:%b %Y}: {compact_number(peak['revenue'])} PLN")
    peak_base = alt.Chart(peak_data).encode(x="month:T", y="revenue:Q")
    peak_dot = peak_base.mark_point(filled=True, size=110, color=ACCENT, stroke=SURFACE, strokeWidth=2.5, opacity=1)
    peak_label = _label(peak_base, align="right", dx=-10, dy=-4, fontWeight=600).encode(text="label:N")

    chart = _with_title(alt.layer(area, line, hover_rule, hover_dot, peak_dot, peak_label), titled,
                        monthly_revenue_text(sales))
    return _config(chart, width, height)


def weekday_text(sales, configured_weights):
    """Title (the conclusion) and subtitle lines of the weekday chart."""
    data = weekday_data(sales, configured_weights)
    top = data.loc[data["is_top"]].iloc[0]
    low = data.loc[data["share"].idxmin()]
    title = f"{top['day_name']} brings {top['share']:.0%} of orders"
    return title, [f"Share of orders by weekday; {low['day_name']} is the quietest with {low['share']:.0%}.",
                   "Thin marks show the configured weights."]


def weekday_chart(sales, configured_weights, width=760, height=330, titled=True):
    """Order share by weekday; the strongest day in the accent colour, configured weights as thin ticks."""
    data = weekday_data(sales, configured_weights)

    x = alt.X("weekday:N", sort=WEEKDAYS, title=None, axis=alt.Axis(labelAngle=0, labelColor=TEXT_SECONDARY))
    y = alt.Y("share:Q", title=None, axis=None, scale=alt.Scale(domain=[0, float(data[["share", "configured"]].max().max()) * 1.18]))
    tooltip = [alt.Tooltip("day_name:N", title="Day"),
               alt.Tooltip("share:Q", title="Orders", format=TOOLTIP_PERCENT),
               alt.Tooltip("configured:Q", title="Configured weight", format=TOOLTIP_PERCENT)]
    base = alt.Chart(data).encode(x=x)
    bars = base.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, width=28).encode(
        y=y, color=alt.condition("datum.is_top", alt.value(ACCENT), alt.value(MUTED_MARK)), tooltip=tooltip,
    )
    ticks = base.mark_tick(color=TARGET_MARK, thickness=2, size=30, opacity=1).encode(y="configured:Q", tooltip=tooltip)
    labelled = base.transform_calculate(label_y="max(datum.share, datum.configured)")
    encoding = {"y": alt.Y("label_y:Q"), "text": alt.Text("share:Q", format=".0%")}
    values = _label(labelled.transform_filter("!datum.is_top"), dy=-8, baseline="bottom",
                    color=TEXT_SECONDARY).encode(**encoding)
    top_value = _label(labelled.transform_filter("datum.is_top"), dy=-8, baseline="bottom",
                       fontWeight=600, fontSize=13).encode(**encoding)

    chart = _with_title(alt.layer(bars, ticks, values, top_value), titled, weekday_text(sales, configured_weights))
    return _config(chart, width, height)


def category_text(sales, language="en"):
    """Title (the conclusion) and subtitle lines of the category chart."""
    data = category_data(sales, language)
    top = data.iloc[0]
    gap = (data["share"] - data["target"]).abs().max()
    title = f"{top['category']} earns {top['share']:.0%} of revenue"
    return title, ["Share of gross revenue by category.",
                   f"Thin marks show the target mix (largest gap {gap * 100:.1f} pp)."]


def category_chart(sales, language="en", width=760, height=None, titled=True):
    """Revenue share by category; the leading category in the accent colour, target weights as thin ticks."""
    data = category_data(sales, language)
    height = height or alt.Step(26)

    order = data["category"].tolist()
    y = alt.Y("category:N", sort=order, title=None,
              axis=alt.Axis(labelColor=TEXT_PRIMARY, labelLimit=200, labelFontSize=12))
    x = alt.X("share:Q", title=None, axis=None,
              scale=alt.Scale(domain=[0, float(data[["share", "target"]].max().max()) * 1.12]))
    tooltip = [alt.Tooltip("category:N", title="Category"),
               alt.Tooltip("share:Q", title="Revenue share", format=TOOLTIP_PERCENT),
               alt.Tooltip("target:Q", title="Target", format=TOOLTIP_PERCENT)]
    base = alt.Chart(data).encode(y=y)
    bars = base.mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, height={"band": 0.6}).encode(
        x=x, color=alt.condition("datum.is_top", alt.value(ACCENT), alt.value(MUTED_MARK)), tooltip=tooltip,
    )
    ticks = base.mark_tick(color=TARGET_MARK, thickness=2, size=16, orient="vertical", opacity=1).encode(
        x="target:Q", tooltip=tooltip,
    )
    labelled = base.transform_calculate(label_x="max(datum.share, datum.target)")
    encoding = {"x": alt.X("label_x:Q"), "text": alt.Text("share:Q", format=".1%")}
    values = _label(labelled.transform_filter("!datum.is_top"), align="left", dx=8,
                    color=TEXT_SECONDARY).encode(**encoding)
    top_value = _label(labelled.transform_filter("datum.is_top"), align="left", dx=8,
                       fontWeight=600, fontSize=13).encode(**encoding)

    chart = _with_title(alt.layer(bars, ticks, values, top_value), titled, category_text(sales, language))
    return _config(chart, width, height)
