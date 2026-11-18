"""
Plotly figures of the app. Data and titles come from func.charts (the same numbers as the README charts); this
module only draws them in the app style: teal for the data, one copper highlight, grey context, hairline grid.
"""
import plotly.graph_objects as go

from func import charts as ch
from func import number_format as nf
from ui import theme as t

CONFIG = {"displayModeBar": False}


def _num(size, color):
    """Font of numbers on a chart (axis ticks, value labels)."""
    return {"family": t.NUM_STACK, "size": size, "color": color}


def _layout(fig, height, **extra):
    margin = extra.pop("margin", {"l": 8, "r": 8, "t": 12, "b": 8})
    fig.update_layout(
        separators=nf.plotly_separators(),
        height=height, margin=margin, paper_bgcolor=t.PAGE, plot_bgcolor=t.PAGE,
        font={"family": t.SANS_STACK, "size": 13, "color": t.TEXT}, showlegend=False,
        hoverlabel={"bgcolor": t.PAGE, "bordercolor": t.LINE, "font": {"family": t.SANS_STACK, "color": t.INK, "size": 13}},
        barcornerradius=4, dragmode=False, **{"bargap": 0.32, **extra},
    )
    return fig


def monthly_revenue(sales):
    """Hero chart: gross revenue by month, teal line on a faint area, the peak month in copper."""
    data = ch.monthly_revenue_data(sales)
    peak = data.loc[data["is_peak"]].iloc[0]
    fig = go.Figure()
    fig.add_scatter(
        x=data["month"], y=data["revenue"], mode="lines", line={"color": t.PRIMARY, "width": 2.5, "shape": "spline",
                                                               "smoothing": 0.6},
        fill="tozeroy", fillcolor=t.AREA, hovertemplate="%{x|%B %Y}<br><b>%{y:,.0f} PLN</b><extra></extra>",
    )
    fig.add_scatter(x=[peak["month"]], y=[peak["revenue"]], mode="markers", hoverinfo="skip",
                    marker={"color": t.ACCENT, "size": 11, "line": {"color": t.PAGE, "width": 2.5}})
    fig.add_annotation(x=peak["month"], y=peak["revenue"], xanchor="right", xshift=-12, yshift=2, showarrow=False,
                       text=f"<b>{peak['month']:%b %Y}</b>  {ch.compact_number(peak['revenue'])} PLN",
                       font=_num(13, t.INK))
    fig.update_xaxes(showgrid=False, showline=False, ticks="", tickformat="%b %Y", dtick="M6",
                     tickfont=_num(13, t.MUTED), fixedrange=True)
    fig.update_yaxes(gridcolor=t.LINE, zeroline=False, showline=False, ticks="", tickformat="~s", nticks=5,
                     tickfont=_num(13, t.MUTED), ticklabelposition="inside top", fixedrange=True,
                     range=[0, float(data["revenue"].max()) * 1.14])
    return _layout(fig, 340, hovermode="x")


def _target_marks(fig, x, y, horizontal, size):
    """Thin ink marks for the configured or target weights."""
    symbol = "line-ns" if horizontal else "line-ew"
    fig.add_scatter(x=x, y=y, mode="markers", hoverinfo="skip",
                    marker={"symbol": symbol, "size": size, "line": {"color": t.INK, "width": 2}})


def weekday_profile(sales, configured_weights):
    """Order share by weekday: mist bars, the strongest day in copper, configured weights as ink marks."""
    data = ch.weekday_data(sales, configured_weights)
    colors = [t.ACCENT if top else t.MIST for top in data["is_top"]]
    fig = go.Figure()
    fig.add_bar(x=data["weekday"], y=data["share"], marker={"color": colors}, customdata=data[["day_name", "configured"]],
                hovertemplate="%{customdata[0]}<br><b>%{y:.1%}</b> of orders<br>configured %{customdata[1]:.1%}"
                              "<extra></extra>")
    _target_marks(fig, data["weekday"], data["configured"], horizontal=False, size=30)
    label_y = data[["share", "configured"]].max(axis=1)
    fig.add_scatter(x=data["weekday"], y=label_y + float(label_y.max()) * 0.025, mode="text",
                    text=[nf.percent(v, 0) for v in data["share"]],
                    textposition="top center", hoverinfo="skip",
                    textfont=_num(13, [t.INK if top else t.MUTED for top in data["is_top"]]))
    fig.update_xaxes(showgrid=False, ticks="", tickfont={"color": t.TEXT}, fixedrange=True, ticklabelstandoff=6)
    fig.update_yaxes(visible=False, range=[0, float(label_y.max()) * 1.2], fixedrange=True)
    return _layout(fig, 300)


def category_mix(sales, language="en"):
    """Revenue share by category: mist bars, the leading category in copper, target mix as ink marks."""
    data = ch.category_data(sales, language).iloc[::-1]
    colors = [t.ACCENT if top else t.MIST for top in data["is_top"]]
    fig = go.Figure()
    fig.add_bar(y=data["category"], x=data["share"], orientation="h", marker={"color": colors},
                customdata=data[["target"]],
                hovertemplate="%{y}<br><b>%{x:.1%}</b> of revenue<br>target %{customdata[0]:.1%}<extra></extra>")
    _target_marks(fig, data["target"], data["category"], horizontal=True, size=16)
    label_x = data[["share", "target"]].max(axis=1)
    fig.add_scatter(y=data["category"], x=label_x, mode="text",
                    text=[f"  {nf.percent(v, 1)}" for v in data["share"]],
                    textposition="middle right", hoverinfo="skip",
                    textfont=_num(12, [t.INK if top else t.MUTED for top in data["is_top"]]))
    fig.update_yaxes(showgrid=False, ticks="", tickfont={"color": t.INK}, fixedrange=True, automargin=True,
                     ticklabelstandoff=10)
    fig.update_xaxes(visible=False, range=[0, float(label_x.max()) * 1.3], fixedrange=True)
    return _layout(fig, max(260, 26 * len(data) + 30), bargap=0.38)


WEIGHT_MAX = 1.0  # upper limit of a draggable seasonality weight
WEIGHT_STEP = 0.01


def weights_figure(values, labels):
    """
    Draggable seasonality weights: one teal point per month or weekday with its value above it. ui/assets/drag_weights.js
    moves the points vertically; the y range stays fixed so a dragged point never rescales the chart.
    """
    values = [max(0.0, min(WEIGHT_MAX, float(v or 0))) for v in values]
    top = max(0.4, max(values) * 1.3)
    fig = go.Figure()
    fig.add_scatter(
        x=list(labels), y=values, mode="lines+markers+text", text=[nf.number(v, 2) for v in values],
        textposition="top center", cliponaxis=False, hoverinfo="skip",
        line={"color": t.MIST, "width": 1.5, "shape": "linear"},
        marker={"color": t.PRIMARY, "size": 13, "line": {"color": t.PAGE, "width": 2}},
        textfont=_num(11, t.TEXT),
    )
    fig.update_xaxes(showgrid=False, ticks="", tickfont={"color": t.TEXT, "size": 11}, tickangle=0, fixedrange=True)
    fig.update_yaxes(visible=False, range=[0, top], fixedrange=True)
    fig.update_layout(meta={"max": WEIGHT_MAX, "step": WEIGHT_STEP, "top": top, "decimal": nf.decimal_mark()})
    return _layout(fig, 170, margin={"l": 14, "r": 14, "t": 26, "b": 6}, hovermode=False)
