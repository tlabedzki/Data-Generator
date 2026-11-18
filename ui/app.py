"""
Dash + Mantine app for the Data Generator: one path from top to bottom, parameters, preview, charts, download.

Run locally (from the repository root):
    python -m ui.app            # http://127.0.0.1:8050
"""
import os
import random

import dash._dash_renderer
import dash_mantine_components as dmc
from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update

from func import charts as ch
from func import export, service
from func import number_format as nf
from ui import figures, runs
from ui import theme as t

dash._dash_renderer._set_react_version("19.2.4")  # Mantine 3 needs React 19; Dash 4.5 still defaults to 18

REPO_URL = "https://github.com/tlabedzki/Data-Generator"
PREVIEW_ROWS = 100
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DATASET_LABELS = {"sales_data": "Sales lines", "order_data": "Order lines", "customer_data": "Customers",
                  "product_data": "Products"}
STAGE_LABELS = {"customer_data": "Generating customers", "product_data": "Building the product catalog",
                "order_data": "Drawing orders", "sales_data": "Joining sales lines"}


# ---------------------------------------------------------------------------------------------------------------- #
# Building blocks

def section(number, title, lead, body, section_id):
    return html.Section([
        html.Div([html.Span(f"{number:02d}", className="dg-step"), html.H2(title, className="dg-h2")],
                 className="dg-section-head"),
        dmc.Text(lead, className="dg-lead-small"),
        html.Div(body, id=f"{section_id}-body"),
    ], id=section_id, className="dg-section")


def placeholder(text):
    return html.P(text, className="dg-placeholder")


def number_input(input_id, label, value, limits, step, **props):
    props = {"thousandSeparator": nf.THOUSANDS, **props}
    return dmc.NumberInput(id=input_id, label=label, value=value, min=limits[0], max=limits[1], step=step,
                           allowDecimal=False, size="md", hideControls=True,
                           inputWrapperOrder=["label", "input", "description"], **props)


# Size presets of the Parameters section. Times measured on a laptop with the default seed;
# medium is the app default and large is the command-line default.
PRESETS = {
    "small": {"label": "Small", "customers": 1_000, "products": 1_000, "order_lines": 2_000, "time": "about 1 s"},
    "medium": {"label": "Medium", "customers": 5_000, "products": 5_000, "order_lines": 10_000, "time": "about 4 s"},
    "large": {"label": "Large", "customers": 40_000, "products": 50_000, "order_lines": 80_000, "time": "about 30 s"},
}


def preset_for(customers, products, order_lines):
    """Name of the preset with exactly these sizes, or "custom"."""
    for name, preset in PRESETS.items():
        if (customers, products, order_lines) == (preset["customers"], preset["products"], preset["order_lines"]):
            return name
    return "custom"


WEIGHT_GRAPH_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False}


def weights_block(kind, title, labels, values, cols):
    """A draggable weights chart (ui/assets/drag_weights.js) above the exact number fields for the same weights."""
    return html.Div([
        dmc.Text(title, className="dg-weights-title"),
        dcc.Graph(id=f"weights-{kind}-graph", figure=figures.weights_figure(values, labels),
                  config=WEIGHT_GRAPH_CONFIG, className="dg-weights-graph", style={"height": "170px"}),
        dcc.Store(id=f"weights-{kind}-drag"),
        dmc.SimpleGrid([dmc.NumberInput(id={"type": f"w-{kind}", "index": i}, label=label, value=value, min=0,
                                        max=figures.WEIGHT_MAX, step=0.05, decimalScale=2, fixedDecimalScale=True,
                                        decimalSeparator=nf.DECIMAL,
                                        size="sm", hideControls=True)
                        for i, (label, value) in enumerate(zip(labels, values))], cols=cols, spacing="xs"),
    ], className="dg-weights-block")


def parameter_fields():
    """All parameter inputs."""
    defaults = service.GenerationParams()
    limits = service.LIMITS
    years = (limits["start_year"][0], limits["end_year"][1])
    growth = (int(limits["annual_growth_rate"][0] * 100), int(limits["annual_growth_rate"][1] * 100))
    return {
        "customers": number_input("customers", "Customers", defaults.customers, limits["customers"], 1_000),
        "products": number_input("products", "Products", defaults.products, limits["products"], 1_000),
        "order_lines": number_input("order-lines", "Order lines", defaults.order_lines, limits["order_lines"], 5_000,
                                    description="1 to 5 lines per order"),
        "start_year": number_input("start-year", "From year", defaults.start_year, years, 1, thousandSeparator=""),
        "end_year": number_input("end-year", "To year", defaults.end_year, years, 1, thousandSeparator="",
                                 description=f"up to {limits['years_span']} years"),
        "growth": number_input("growth", "Annual growth", int(defaults.annual_growth_rate * 100), growth, 5,
                               suffix=" %"),
        "language": dmc.Stack([
            dmc.Text("Language of values", className="dg-label"),
            dmc.SegmentedControl(id="language", value=defaults.language, size="md", fullWidth=True,
                                 data=[{"value": k, "label": v} for k, v in service.LANGUAGES.items()])], gap=4),
        "seed": number_input("seed", "Seed", defaults.seed, limits["seed"], 1, thousandSeparator="",
                             description="same seed, same data"),
        "new_seed": dmc.Stack(dmc.Switch(id="new-seed", label="New random seed on every run", size="md",
                                         color="petrol"), justify="center", h="100%", pt=18),
        "weights": [
            dmc.Group([
                dmc.Text("Drag a point up or down, or type the number below it. Weights are relative: they are "
                         "normalized and get some random noise, like real demand.", className="dg-caption"),
                dmc.Button("Restore defaults", id="weights-reset", variant="subtle", color="petrol", size="compact-sm",
                           className="dg-weights-reset"),
            ], justify="space-between", align="flex-start", wrap="wrap", gap="xs", mb="sm"),
            weights_block("month", "Months", MONTHS, defaults.monthly_seasonality, {"base": 4, "sm": 6, "md": 12}),
            weights_block("day", "Weekdays", WEEKDAYS, defaults.weekday_seasonality, {"base": 4, "sm": 7}),
        ],
    }


def generate_row():
    return [
        dmc.Group([
            dmc.Button("Generate data", id="generate", size="lg", radius="sm", color="petrol", className="dg-generate"),
            html.Div([dmc.Progress(id="progress", value=0, size=3, color="petrol", radius="xl", className="dg-progress"),
                      dmc.Text(id="progress-text", className="dg-caption", mt=6)], id="progress-wrap",
                     className="dg-progress-wrap", style={"visibility": "hidden"}),
        ], gap="xl", align="center", mt="xl", wrap="wrap"),
        html.Div(id="errors"),
    ]


def preset_card(name):
    if name == "custom":
        body = [html.Span("Custom", className="dg-preset-name"), html.Span("your own sizes", className="dg-preset-time")]
    else:
        preset = PRESETS[name]
        body = [html.Span(preset["label"], className="dg-preset-name"),
                html.Span(preset["time"], className="dg-preset-time"),
                html.Span(f"{nf.number(preset['customers'])} customers · {nf.number(preset['order_lines'])} lines",
                          className="dg-preset-detail")]
    return html.Button(body, id={"type": "preset", "name": name}, n_clicks=0, disabled=name == "custom",
                       className="dg-preset is-active" if name == "medium" else "dg-preset")


def group(title, children):
    return html.Div([html.H3(title, className="dg-group-title"),
                     dmc.SimpleGrid(children, cols={"base": 1, "sm": 3}, spacing="xl", verticalSpacing="lg")],
                    className="dg-group")


def parameters():
    """Size presets, then Size and Period groups, then everything else under a collapsed Advanced section."""
    f = parameter_fields()
    advanced = dmc.Accordion(dmc.AccordionItem([
        dmc.AccordionControl("Advanced"),
        dmc.AccordionPanel([
            dmc.SimpleGrid([f["language"], f["seed"], f["new_seed"]], cols={"base": 1, "sm": 3}, spacing="xl",
                           verticalSpacing="lg"),
            html.H4("Seasonality weights", className="dg-subgroup-title"),
            *f["weights"],
        ]),
    ], value="advanced"), variant="default", className="dg-accordion", chevronPosition="left")
    return [
        html.Div([preset_card(name) for name in (*PRESETS, "custom")], className="dg-presets"),
        group("Size", [f["customers"], f["products"], f["order_lines"]]),
        group("Period", [f["start_year"], f["end_year"], f["growth"]]),
        html.Div(advanced, className="dg-weights"),
        *generate_row(),
    ]


def page():
    return dmc.MantineProvider(theme=t.MANTINE_THEME, children=html.Div([
        dcc.Store(id="run-id"),
        dcc.Store(id="result-id"),
        dcc.Interval(id="poll", interval=300, disabled=True),
        dcc.Download(id="download"),
        html.Header(html.Div([
            html.Span(["Data Generator", html.Span(".", className="dg-dot")], className="dg-wordmark"),
            html.A("Source on GitHub", href=REPO_URL, target="_blank", className="dg-link"),
        ], className="dg-wrap dg-topline")),
        html.Main(html.Div([
            html.Div([
                html.P("Synthetic e-commerce data", className="dg-eyebrow"),
                html.H1(["A shop that never existed, ", html.Br(), "with ", html.Em("data"), " that looks real."],
                        className="dg-h1"),
                html.P("Customers, products, orders and sales lines with seasonality, growth and discounts. "
                       "100% fictional, reproducible with a seed, ready as CSV or Parquet.", className="dg-lead"),
            ], className="dg-hero"),
            section(1, "Parameters", "Pick a size, set the period, then generate. Advanced holds language, seed and seasonality.",
                    parameters(), "parameters"),
            section(2, "Preview", "Key numbers and the first rows of each table.",
                    placeholder("Generate data to see the preview."), "preview"),
            section(3, "Charts", "What the generated sales look like. Hover for exact values.",
                    placeholder("Charts appear after the first run."), "charts"),
            section(4, "Download", "All four tables at once or one by one.",
                    placeholder("Files are ready after the first run."), "download-section"),
            html.Footer([
                html.P("All people, products and sales are generated. Postal codes: ZnajdzKod.pl na podstawie PRG "
                       "(GUGiK) i TERYT (GUS), stan 16.09.2026."),
                html.A(REPO_URL.removeprefix("https://"), href=REPO_URL, target="_blank", className="dg-link"),
            ], className="dg-footer"),
        ], className="dg-wrap")),
    ], className="dg-page"))


# ---------------------------------------------------------------------------------------------------------------- #
# Result views

def compact_pln(value):
    return f"{nf.compact(value)} PLN"


def stat(label, value, note=None):
    return html.Div([html.Div(value, className="dg-stat-value"), html.Div(label, className="dg-stat-label"),
                     html.Div(note or "", className="dg-stat-note")], className="dg-stat")


def preview_view(run):
    numbers = ch.headline_numbers(run.datasets)
    stats = html.Div([
        stat("orders", nf.number(numbers["orders"], 0), f"{nf.number(numbers['order_lines'], 0)} lines"),
        stat("gross revenue", compact_pln(numbers["revenue"])),
        stat("average order", f"{nf.number(numbers['average_order_value'], 0)} PLN"),
        stat("customers", nf.number(numbers["customers"], 0)),
        stat("discounted lines", nf.percent(numbers["discounted_line_share"], 0)),
    ], className="dg-stats")
    meta = (f"{numbers['first_date']:%d %b %Y} to {numbers['last_date']:%d %b %Y} · "
            f"{nf.number(numbers['products'], 0)} products · seed {run.params.seed} · "
            f"generated in {nf.number(run.seconds, 1)} s")
    return [
        stats,
        dmc.Text(meta, className="dg-caption", mt="sm"),
        dmc.SegmentedControl(id="table-choice", value="sales_data", mt=36, size="sm", className="dg-tabs",
                             data=[{"value": k, "label": v} for k, v in DATASET_LABELS.items()]),
        html.Div(id="table"),
    ]


def format_cell(value):
    """Dates as ISO, decimals with a decimal comma; whole numbers (IDs, quantities) without grouping."""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        return nf.number(value, 2)
    return str(value)


def table_view(data):
    head = data.head(PREVIEW_ROWS)
    table = dmc.Table(
        data={"head": list(head.columns), "body": [[format_cell(v) for v in row]
                                              for row in head.itertuples(index=False)]},
        stickyHeader=True, highlightOnHover=True, verticalSpacing=6, horizontalSpacing="md", fz=13,
        className="dg-table",
    )
    return [
        dmc.ScrollArea(table, h=380, type="auto", offsetScrollbars=True, className="dg-table-scroll", mt="md"),
        dmc.Text(f"First {nf.number(len(head), 0)} of {nf.number(len(data), 0)} rows and "
                 f"{data.shape[1]} columns. "
                 "Download the files for the full table.", className="dg-caption", mt="sm"),
    ]


def chart_block(text, figure, extra_class=""):
    title, subtitle = text
    return html.Figure([
        html.Figcaption([html.Div(title, className="dg-chart-title"),
                         html.Div(" ".join(subtitle), className="dg-chart-sub")]),
        dcc.Graph(figure=figure, config=figures.CONFIG, className="dg-graph",
                  style={"height": f"{figure.layout.height}px"}),
    ], className=f"dg-chart {extra_class}")


def charts_view(run):
    sales = run.datasets["sales_data"]
    weights = run.params.weekday_seasonality
    language = run.params.language
    return [
        chart_block(ch.monthly_revenue_text(sales), figures.monthly_revenue(sales), "dg-chart-hero"),
        html.Div([
            chart_block(ch.weekday_text(sales, weights), figures.weekday_profile(sales, weights)),
            chart_block(ch.category_text(sales, language), figures.category_mix(sales, language)),
        ], className="dg-chart-pair"),
    ]


def size_label(content):
    size = len(content)
    return f"{nf.number(size / 1e6, 1)} MB" if size >= 1e6 else f"{nf.number(size / 1e3, 0)} KB"


def download_view():
    return [
        dmc.Group([
            dmc.Text("Format", className="dg-label"),
            dmc.SegmentedControl(id="file-format", value="csv", size="sm",
                                 data=[{"value": k, "label": v["label"]} for k, v in export.FORMATS.items()]),
        ], gap="md"),
        dmc.Text("CSV: semicolon-separated UTF-8 with a dot as the decimal separator. Parquet keeps column types and "
                 "is smaller.", className="dg-caption", mt=8),
        html.Div(id="file-list", className="dg-files"),
    ]


def file_list(run, file_format):
    files = runs.exports_for(run, file_format)
    rows = [html.Div([
        html.Div([html.Div(DATASET_LABELS[name], className="dg-file-name"),
                  html.Div(f"{export.file_name(name, file_format)} · {nf.number(len(run.datasets[name]), 0)} rows",
                           className="dg-caption")]),
        html.Div(size_label(files["tables"][name]), className="dg-file-size"),
        dmc.Button("Download", id={"type": "dl-table", "name": name}, variant="subtle", color="petrol", size="sm"),
    ], className="dg-file") for name in DATASET_LABELS]
    zip_button = dmc.Button(f"Download all tables · ZIP {size_label(files['zip'])}", id="dl-zip", size="lg",
                            color="petrol", className="dg-zip")
    return [zip_button, html.Div(rows, className="dg-file-rows")]


# ---------------------------------------------------------------------------------------------------------------- #
# App and callbacks

app = Dash(__name__, title="Data Generator", assets_folder=os.path.join(os.path.dirname(__file__), "assets"),
           suppress_callback_exceptions=True)
app.layout = page


@app.callback(
    Output("customers", "value", allow_duplicate=True), Output("products", "value", allow_duplicate=True),
    Output("order-lines", "value", allow_duplicate=True),
    Input({"type": "preset", "name": ALL}, "n_clicks"), prevent_initial_call=True,
)
def apply_preset(clicks):
    """A click on Small, Medium or Large fills in the three sizes."""
    if not ctx.triggered_id or not any(clicks) or ctx.triggered_id["name"] not in PRESETS:
        return no_update, no_update, no_update
    preset = PRESETS[ctx.triggered_id["name"]]
    return preset["customers"], preset["products"], preset["order_lines"]


@app.callback(
    Output({"type": "preset", "name": ALL}, "className"),
    Input("customers", "value"), Input("products", "value"), Input("order-lines", "value"),
    State({"type": "preset", "name": ALL}, "id"),
)
def mark_preset(customers, products, order_lines, ids):
    """Highlight the preset that matches the sizes; any other combination shows Custom."""
    active = preset_for(customers, products, order_lines)
    return ["dg-preset is-active" if item["name"] == active else "dg-preset" for item in ids]


def _weights_callbacks(kind, labels):
    @app.callback(Output(f"weights-{kind}-graph", "figure"), Input({"type": f"w-{kind}", "index": ALL}, "value"),
                  prevent_initial_call=True)
    def redraw(values):
        """Typed numbers move the points."""
        return figures.weights_figure(values, labels)

    @app.callback(Output({"type": f"w-{kind}", "index": ALL}, "value", allow_duplicate=True),
                  Input(f"weights-{kind}-drag", "data"), prevent_initial_call=True)
    def from_drag(values):
        """Dragged points fill in the numbers (the generator reads the number fields)."""
        if not values or len(values) != len(labels):
            return [no_update] * len(labels)
        return [round(max(0.0, min(figures.WEIGHT_MAX, float(v))), 2) for v in values]

    return redraw, from_drag


redraw_months, months_from_drag = _weights_callbacks("month", MONTHS)
redraw_weekdays, weekdays_from_drag = _weights_callbacks("day", WEEKDAYS)


@app.callback(
    Output({"type": "w-month", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "w-day", "index": ALL}, "value", allow_duplicate=True),
    Input("weights-reset", "n_clicks"), prevent_initial_call=True,
)
def reset_weights(clicks):
    if not clicks:
        return [no_update] * len(MONTHS), [no_update] * len(WEEKDAYS)
    defaults = service.GenerationParams()
    return list(defaults.monthly_seasonality), list(defaults.weekday_seasonality)


@app.callback(
    Output("run-id", "data"), Output("poll", "disabled"), Output("errors", "children"), Output("seed", "value"),
    Output("generate", "loading"),
    Input("generate", "n_clicks"),
    State("customers", "value"), State("products", "value"), State("order-lines", "value"),
    State("start-year", "value"), State("end-year", "value"), State("growth", "value"),
    State({"type": "w-month", "index": ALL}, "value"), State({"type": "w-day", "index": ALL}, "value"),
    State("language", "value"), State("seed", "value"), State("new-seed", "checked"),
    prevent_initial_call=True,
)
def start_run(clicks, customers, products, order_lines, start_year, end_year, growth, monthly, weekday, language, seed,
              new_seed):
    if not clicks:  # rendered, not clicked
        return no_update, no_update, no_update, no_update, no_update
    if new_seed:
        seed = random.SystemRandom().randrange(0, 1_000_000)
    try:
        params = service.GenerationParams(
            customers=int(customers), products=int(products), order_lines=int(order_lines),
            start_year=int(start_year), end_year=int(end_year), annual_growth_rate=float(growth) / 100,
            monthly_seasonality=tuple(float(v or 0) for v in monthly),
            weekday_seasonality=tuple(float(v or 0) for v in weekday), seed=int(seed), language=language,
        )
    except (TypeError, ValueError):
        return no_update, True, error_box(["Fill in every parameter with a number."]), no_update, False
    problems = params.errors()
    if problems:
        return no_update, True, error_box(problems), no_update, False
    return runs.start(params), False, None, seed, True


def error_box(problems):
    return dmc.Alert([html.Div(problem) for problem in problems], color="copper", variant="light", mt="lg",
                     title="Check the parameters")


@app.callback(
    Output("progress", "value"), Output("progress-text", "children"), Output("result-id", "data"),
    Output("poll", "disabled", allow_duplicate=True), Output("generate", "loading", allow_duplicate=True),
    Output("progress-wrap", "style"),
    Input("poll", "n_intervals"), State("run-id", "data"), prevent_initial_call=True,
)
def poll_run(_, run_id):
    run = runs.get(run_id)
    visible = {"visibility": "visible"}
    if run is None:
        return 0, "", no_update, True, False, no_update
    if run.error:
        return 0, f"Generation failed: {run.error}", no_update, True, False, visible
    if run.done:
        return 100, f"Done in {nf.number(run.seconds, 1)} s.", run_id, True, False, visible
    stage = STAGE_LABELS.get(run.stage, "Starting")
    return run.fraction * 100, f"{stage}… {nf.percent(run.fraction, 0)}", no_update, False, True, visible


@app.callback(
    Output("preview-body", "children"), Output("charts-body", "children"), Output("download-section-body", "children"),
    Input("result-id", "data"), prevent_initial_call=True,
)
def show_result(run_id):
    run = runs.get(run_id)
    if run is None or run.datasets is None:
        return no_update, no_update, no_update
    return preview_view(run), charts_view(run), download_view()


app.clientside_callback(
    """function (runId) {
        if (runId) { setTimeout(function () { document.getElementById('preview').scrollIntoView({behavior: 'smooth'}); }, 150); }
        return window.dash_clientside.no_update;
    }""",
    Output("preview", "className"), Input("result-id", "data"), prevent_initial_call=True,
)


@app.callback(Output("table", "children"), Input("table-choice", "value"), State("result-id", "data"))
def show_table(name, run_id):
    run = runs.get(run_id)
    if run is None or run.datasets is None:
        return no_update
    return table_view(run.datasets[name or "sales_data"])


@app.callback(Output("file-list", "children"), Input("file-format", "value"), State("result-id", "data"))
def show_files(file_format, run_id):
    run = runs.get(run_id)
    if run is None or run.datasets is None:
        return no_update
    return file_list(run, file_format)


@app.callback(
    Output("download", "data"),
    Input("dl-zip", "n_clicks"), Input({"type": "dl-table", "name": ALL}, "n_clicks"),
    State("file-format", "value"), State("result-id", "data"), prevent_initial_call=True,
)
def download(_, __, file_format, run_id):
    run = runs.get(run_id)
    if run is None or run.datasets is None or not ctx.triggered or not ctx.triggered[0]["value"]:
        return no_update
    files = runs.exports_for(run, file_format)
    if ctx.triggered_id == "dl-zip":
        return dcc.send_bytes(files["zip"], f"data-generator-seed-{run.params.seed}-{file_format}.zip")
    name = ctx.triggered_id["name"]
    return dcc.send_bytes(files["tables"][name], export.file_name(name, file_format))


def main():
    app.run(host="127.0.0.1", port=int(os.environ.get("DG_PORT", 8050)), debug=False)


if __name__ == "__main__":
    main()
