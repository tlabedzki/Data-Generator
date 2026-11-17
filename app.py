"""
Streamlit app for the Data Generator: set parameters, generate data, explore it and download the files.

Run locally:
    streamlit run app.py --server.address 127.0.0.1
"""
import random
import time

import pandas as pd
import streamlit as st

from func import charts as ch
from func import export
from func import service

PREVIEW_ROWS = 1_000
DATASET_LABELS = {
    "sales_data": "Sales lines",
    "order_data": "Order lines",
    "customer_data": "Customers",
    "product_data": "Products",
}
STAGE_LABELS = {
    "customer_data": "Generating customers",
    "product_data": "Building the product catalog",
    "order_data": "Drawing orders",
    "sales_data": "Joining sales lines",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
REPO_URL = "https://github.com/tlabedzki/Data-Generator"


# ---------------------------------------------------------------------------------------------------------------- #
# Parameters

def parameter_form():
    """Render the sidebar form. Returns (params, submitted) where params may be None if invalid."""
    defaults = service.GenerationParams()
    limits = service.LIMITS

    with st.sidebar.form("parameters"):
        st.header("Parameters")

        st.subheader("Size")
        customers = st.number_input("Customers", *limits["customers"], defaults.customers, step=1_000)
        products = st.number_input("Products", *limits["products"], defaults.products, step=1_000)
        order_lines = st.number_input(
            "Order lines", *limits["order_lines"], defaults.order_lines, step=5_000,
            help="Target number of order lines. One order has 1 to 5 lines. "
                 "100,000 lines take about half a minute.",
        )

        st.subheader("Period and growth")
        start_year, end_year = st.slider(
            "Years", limits["start_year"][0], limits["end_year"][1], (defaults.start_year, defaults.end_year),
            help=f"Up to {limits['years_span']} years.",
        )
        growth_percent = st.slider(
            "Annual growth of order volume", int(limits["annual_growth_rate"][0] * 100),
            int(limits["annual_growth_rate"][1] * 100), int(defaults.annual_growth_rate * 100), step=5, format="%d%%",
        )

        with st.expander("Seasonality weights"):
            st.caption("Relative weights. They are normalized and get some random noise, like real demand.")
            monthly = st.data_editor(
                pd.DataFrame([defaults.monthly_seasonality], columns=MONTHS), hide_index=True, key="monthly",
                column_config={month: st.column_config.NumberColumn(month, min_value=0.0, format="%.2f")
                               for month in MONTHS},
            )
            weekday = st.data_editor(
                pd.DataFrame([defaults.weekday_seasonality], columns=WEEKDAYS), hide_index=True, key="weekday",
                column_config={day: st.column_config.NumberColumn(day, min_value=0.0, format="%.2f")
                               for day in WEEKDAYS},
            )

        st.subheader("Output")
        language = st.selectbox("Language of values", list(service.LANGUAGES), format_func=service.LANGUAGES.get)
        random_seed = st.checkbox("New random seed on every run", value=False)
        seed = st.number_input("Seed", *limits["seed"], defaults.seed, step=1,
                               help="The same seed and parameters always give the same data.")

        submitted = st.form_submit_button("Generate data", type="primary", width="stretch")

    if random_seed and submitted:
        seed = random.SystemRandom().randrange(0, 1_000_000)

    params = service.GenerationParams(
        customers=int(customers),
        products=int(products),
        order_lines=int(order_lines),
        start_year=int(start_year),
        end_year=int(end_year),
        annual_growth_rate=growth_percent / 100,
        monthly_seasonality=tuple(float(value) for value in monthly.iloc[0].fillna(0)),
        weekday_seasonality=tuple(float(value) for value in weekday.iloc[0].fillna(0)),
        seed=int(seed),
        language=language,
    )
    return params, submitted


# ---------------------------------------------------------------------------------------------------------------- #
# Generation

def run_generation(params):
    bar = st.progress(0.0, text="Starting")

    def on_progress(fraction, stage_name):
        bar.progress(fraction, text=f"{STAGE_LABELS.get(stage_name, 'Working')}… {fraction:.0%}")

    started = time.perf_counter()
    datasets = service.generate(params, progress=on_progress)
    bar.empty()
    st.session_state["result"] = {
        "params": params,
        "datasets": datasets,
        "seconds": time.perf_counter() - started,
        "exports": {},
    }


def exports_for(result, file_format):
    """Serialize each table and the ZIP once per result and format."""
    cache = result["exports"]
    if file_format not in cache:
        tables = {name: export.dataframe_to_bytes(data, file_format) for name, data in result["datasets"].items()}
        zipped = export.files_to_zip({export.file_name(name, file_format): content for name, content in tables.items()})
        cache[file_format] = {"tables": tables, "zip": zipped}
    return cache[file_format]


# ---------------------------------------------------------------------------------------------------------------- #
# Result views

def compact_pln(value):
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= limit:
            return f"{value / limit:,.1f}{suffix} PLN"
    return f"{value:,.0f} PLN"


def show_headline(result):
    numbers = ch.headline_numbers(result["datasets"])
    columns = st.columns(5)
    columns[0].metric("Orders", f"{numbers['orders']:,}", help=f"{numbers['order_lines']:,} order lines")
    columns[1].metric("Gross revenue", compact_pln(numbers["revenue"]), help=f"{numbers['revenue']:,.2f} PLN")
    columns[2].metric("Average order", f"{numbers['average_order_value']:,.0f} PLN")
    columns[3].metric("Customers", f"{numbers['customers']:,}")
    columns[4].metric("Lines with a discount", f"{numbers['discounted_line_share']:.0%}")
    params = result["params"]
    st.caption(
        f"{numbers['first_date']:%d %b %Y} to {numbers['last_date']:%d %b %Y} · {numbers['products']:,} products · "
        f"seed {params.seed} · generated in {result['seconds']:.1f} s"
    )


def chart_block(text, chart):
    """Title and subtitle as page text (they wrap on narrow screens), then the chart without its own title."""
    title, subtitle = text
    st.markdown(f"#### {title}")
    st.caption(" ".join(subtitle))
    st.altair_chart(chart, width="stretch")


def show_charts(result):
    sales = result["datasets"]["sales_data"]
    params = result["params"]
    chart_block(ch.monthly_revenue_text(sales), ch.monthly_revenue_chart(sales, width="container", titled=False))
    left, right = st.columns(2, gap="large")
    with left:
        chart_block(ch.weekday_text(sales, params.weekday_seasonality),
                    ch.weekday_chart(sales, params.weekday_seasonality, width="container", titled=False))
    with right:
        chart_block(ch.category_text(sales, params.language),
                    ch.category_chart(sales, params.language, width="container", titled=False))


def show_tables(result):
    datasets = result["datasets"]
    name = st.segmented_control(
        "Table", list(DATASET_LABELS), format_func=DATASET_LABELS.get, default="sales_data", key="table_choice",
    ) or "sales_data"
    data = datasets[name]
    column_config = {"order_date": st.column_config.DateColumn("order_date", format="YYYY-MM-DD")}
    st.dataframe(data.head(PREVIEW_ROWS), hide_index=True, width="stretch", height=420, column_config=column_config)
    st.caption(f"First {min(PREVIEW_ROWS, len(data)):,} of {len(data):,} rows and {data.shape[1]} columns. "
               "Download the files for the full table.")


def show_downloads(result):
    file_format = st.radio(
        "Format", list(export.FORMATS), format_func=lambda key: export.FORMATS[key]["label"], horizontal=True,
        help="CSV: semicolon-separated UTF-8 with a dot as the decimal separator. "
             "Parquet keeps column types and is smaller.",
    )
    files = exports_for(result, file_format)
    mime = export.FORMATS[file_format]["mime"]

    st.download_button(
        f"Download all tables (ZIP, {size_label(files['zip'])})", files["zip"],
        file_name=f"data-generator-seed-{result['params'].seed}-{file_format}.zip", mime="application/zip",
        type="primary", on_click="ignore", width="stretch",
    )
    columns = st.columns(2)
    for index, name in enumerate(DATASET_LABELS):
        content = files["tables"][name]
        columns[index % 2].download_button(
            f"{DATASET_LABELS[name]} · {export.file_name(name, file_format)} ({size_label(content)})", content,
            file_name=export.file_name(name, file_format), mime=mime, on_click="ignore", width="stretch",
        )


def size_label(content):
    size = len(content)
    return f"{size / 1e6:.1f} MB" if size >= 1e6 else f"{size / 1e3:.0f} KB"


# ---------------------------------------------------------------------------------------------------------------- #
# Page

def main():
    st.set_page_config(page_title="Data Generator", layout="wide")
    st.title("Data Generator")
    st.write(
        "Realistic, 100% fictional e-commerce data: customers, products, orders and sales lines with seasonality, "
        "growth and discounts. Set the parameters on the left and click **Generate data**."
    )

    params, submitted = parameter_form()
    problems = params.errors()
    for problem in problems:
        st.error(problem)

    if not problems and (submitted or "result" not in st.session_state):
        run_generation(params)
    if "result" not in st.session_state:
        return

    result = st.session_state["result"]
    show_headline(result)
    charts_tab, tables_tab, download_tab = st.tabs(["Charts", "Tables", "Download"])
    with charts_tab:
        show_charts(result)
    with tables_tab:
        show_tables(result)
    with download_tab:
        show_downloads(result)

    st.divider()
    st.caption(
        f"All people, products and sales are generated. Postal codes: ZnajdzKod.pl na podstawie PRG (GUGiK) i TERYT "
        f"(GUS), stan 16.09.2026. Source code: [{REPO_URL.removeprefix('https://')}]({REPO_URL})"
    )


if __name__ == "__main__":
    main()
