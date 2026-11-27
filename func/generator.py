"""
The generation pipeline: customers, products and order lines first, then the tables built on them (prices,
competitor prices, sessions, experiments, suppliers and stock, order status, shipments, returns, reviews, shop costs
and payments, anomalies, data quality issues) and the joined sales lines.

Every step draws from its own random stream (func/rng.py), so the same seed always gives the same files.
"""
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

import settings.main_settings as s
import settings.market_settings as ms
from func import (
    anomaly,
    assembler,
    behaviour,
    calendar,
    competitors,
    costs,
    customer,
    data,
    experiments,
    fulfilment,
    inventory,
    localization,
    log,
    marketing,
    order,
    prices,
    product,
    quality,
    reviews,
    rng,
    save,
    summary,
)

ProgressCallback = Callable[[float, str], None]

# Paths relative to the repository root, so the generator works from any working directory:
PROJECT_DIR = Path(__file__).resolve().parents[1]
EXPORT_DIR = PROJECT_DIR / "export"

# Output tables: source tables first, then the joined sales lines, then the extra tables.
DATASET_NAMES = ["customer_data", "product_data", "order_data", "sales_data", "price_history", "competitor_prices",
                 "shipment_data", "return_data", "payment_data", "review_data", "campaign_data", "session_data",
                 "experiment_data", "experiment_assignment_data", "anomaly_data", "quality_issue_data",
                 "supplier_data", "product_supplier_data", "purchase_order_data", "stock_movement_data",
                 "lost_demand_data"]
SOURCE_DATASETS = {"customer_data", "product_data", "order_data"}

# Share of total run time per stage, used to turn stage progress into overall progress:
STAGE_SHARES = {"customer_data": 0.40, "product_data": 0.15, "order_data": 0.35, "sales_data": 0.10}


def saving_paths(directory: Path = EXPORT_DIR) -> dict[str, Path]:
    """Output file path of every table in the configured format."""
    return {name: directory / f"{name}.{s.saving_format}" for name in DATASET_NAMES}


def generate_full_sales_data() -> None:
    """Generate the tables selected in settings and save them to export/ in the configured format."""
    generated_data = run_generation_pipeline()
    EXPORT_DIR.mkdir(exist_ok=True)
    save.save_generated_outputs(generated_data, saving_paths())


def run_generation_pipeline(progress: ProgressCallback | None = None) -> dict[str, pd.DataFrame]:
    """
    Generate the tables selected in settings.main_settings.generated_files.

    Source tables (customers, products, order lines) are generated whenever a selected table needs them. Anomalies
    and data quality issues are added to the source tables before the sales lines are joined.

    Parameters:
    progress (callable, optional): Called as progress(fraction, stage_name) while data is generated.

    Returns:
    dict: Table names mapped to DataFrames, in the order of DATASET_NAMES.
    """
    stage_progress = make_stage_progress(progress)
    seed_faker()
    log.log_info(f"Generating data (seed {s.random_state}).")

    selected_files = get_selected_files()
    needed = required_sources(selected_files)
    tables: dict[str, pd.DataFrame | None] = {"customer_data": None, "product_data": None, "order_data": None}
    extra: dict[str, pd.DataFrame] = {}

    if "customer_data" in needed:
        tables["customer_data"] = customer.generate_customer_data(s.customer_data_rows, rng.stream("customers"))
        data.report_progress(stage_progress("customer_data"), 1, 1)

    if "product_data" in needed:
        price_stream = rng.stream("prices")
        products = product.generate_product_data(s.product_data_rows, rng.stream("products"),
                                                 stage_progress("product_data"))
        tables["product_data"] = costs.add_parcel_size(prices.add_life_cycle(products, price_stream))

    if "order_data" in needed:
        customers, products = tables["customer_data"], tables["product_data"]
        marketing_stream = rng.stream("marketing")
        # Both calendars draw from a fresh "calendar" stream, so they share the same month noise; campaigns are
        # planned on the plain one and their effect is added to the second.
        plain_calendar = calendar.build_calendar(rng.stream("calendar"))
        campaigns, campaign_effects, own_effects = marketing.draw_campaigns(plain_calendar, marketing_stream)
        day_calendar = calendar.build_calendar(
            rng.stream("calendar"),
            day_multiplier=marketing.campaign_multiplier(campaign_effects, len(plain_calendar)))
        day_calendar = marketing.add_campaign_columns(day_calendar, campaign_effects)
        extra["campaign_data"] = campaigns[marketing.CAMPAIGN_COLUMNS]
        order_params = get_order_generation_params(products)
        customer_behaviour = behaviour.draw_customer_behaviour(customers, day_calendar, rng.stream("behaviour"),
                                                               order_params["product_category_weights"])
        customers = tables["customer_data"] = behaviour.add_behaviour_columns(customers, customer_behaviour)
        extra["price_history"] = prices.build_price_history(products, price_stream)
        if "competitor_prices" in selected_files:
            extra["competitor_prices"] = competitors.build_competitor_prices(products, extra["price_history"],
                                                                             rng.stream("competitors"))
        price_book = prices.PriceBook(products, extra["price_history"], day_calendar)
        order_data, annual_rate = order.generate_order_data(s.order_data_rows, order_params, customer_behaviour,
                                                            day_calendar, price_book, rng.stream("orders"),
                                                            stage_progress("order_data"))
        order_data, anomalies = anomaly.inject_anomalies(order_data, customers, products)

        logistics = rng.stream("logistics")
        order_data = anomaly.renumber_orders(fulfilment.add_order_times(order_data, logistics))
        order_data, customers = marketing.add_marketing_columns(order_data, customers, day_calendar, campaigns,
                                                                own_effects, marketing_stream)
        customers = tables["customer_data"] = behaviour.add_churn_truth(customers, customer_behaviour, annual_rate)
        extra["session_data"], session_of_order = marketing.build_sessions(order_data, rng.stream("sessions"))
        order_data = marketing.add_session_ids(order_data, session_of_order)
        order_data, extra["experiment_data"], extra["experiment_assignment_data"] = experiments.run_experiments(
            order_data, extra["session_data"], day_calendar, rng.stream("experiments"))
        # Suppliers, purchase orders and stock draw from their own stream. With stockouts off every line is served
        # and the tables above and below stay as in 1.7.1; with stockouts on, lost lines leave order_data here.
        stock = inventory.build_inventory(order_data, products, day_calendar["date"], rng.stream("inventory"))
        extra.update({name: frame for name, frame in stock.items() if name != "served"})
        order_data, extra["session_data"], extra["lost_demand_data"] = inventory.remove_lost_lines(
            order_data, extra["session_data"], stock["served"], price_book, anomaly.renumber_orders)
        order_data = fulfilment.add_unit_prices(order_data, price_book)
        order_data, bulky_orders = fulfilment.fit_delivery_to_products(order_data, products, logistics)
        status_stream = rng.stream("order_status")
        order_data = fulfilment.draw_order_status(order_data, status_stream)
        planned_shipments = fulfilment.build_shipments(order_data, day_calendar, bulky_orders, logistics)
        extra["return_data"], spikes = fulfilment.build_returns(order_data, products, customers, planned_shipments,
                                                                rng.stream("returns"))
        order_data, extra["shipment_data"] = fulfilment.finish_order_status(order_data, planned_shipments,
                                                                            extra["return_data"], status_stream)
        extra["review_data"] = reviews.build_reviews(order_data, extra["shipment_data"], extra["return_data"],
                                                     spikes, rng.stream("reviews"))
        # Shop costs come last and add columns only, so the tables above stay as in earlier versions.
        order_data = costs.add_affiliate_commission(order_data, products, extra["return_data"])
        extra["payment_data"] = costs.build_payment_data(order_data, planned_shipments)
        extra["shipment_data"] = costs.add_shipment_costs(extra["shipment_data"], order_data, products,
                                                          extra["payment_data"])
        extra["return_data"] = costs.add_return_costs(extra["return_data"], products, rng.stream("costs"))
        tables["order_data"] = order_data
        extra["anomaly_data"] = anomaly.anomaly_frame(anomalies + spikes)

    tables, extra["quality_issue_data"] = quality.inject_quality_issues(tables)

    if "sales_data" in selected_files:
        extra["sales_data"] = assembler.build_sales_data(tables["order_data"], tables["product_data"],
                                                         tables["customer_data"])

    generated_data = {}
    for name in DATASET_NAMES:
        if name not in selected_files:
            continue
        frame = tables.get(name) if name in SOURCE_DATASETS else extra.get(name)
        generated_data[name] = localization.localize_dataset(frame)
        summary.log_table(name, generated_data[name])

    data.report_progress(stage_progress("sales_data"), 1, 1)
    log.log_info("Data is ready.")
    return generated_data


def required_sources(selected_files: list[str]) -> set[str]:
    """
    Return the source tables needed for the selected outputs: every table except customers and products alone
    needs the orders, and the orders need customers and products.
    """
    if set(selected_files) - {"customer_data", "product_data"}:
        return set(SOURCE_DATASETS)
    return set(selected_files)


def make_stage_progress(progress: ProgressCallback | None) -> Callable[[str], Callable[[float], None] | None]:
    """
    Build a factory of per-stage callbacks that report overall progress.

    Parameters:
    progress (callable or None): Overall callback taking (fraction, stage_name).

    Returns:
    callable: stage_name -> callback taking the stage fraction (0-1), or None when progress is None.
    """
    stage_names = list(STAGE_SHARES)

    def for_stage(stage_name: str) -> Callable[[float], None] | None:
        if progress is None:
            return None
        start = sum(STAGE_SHARES[name] for name in stage_names[:stage_names.index(stage_name)])
        share = STAGE_SHARES[stage_name]
        return lambda fraction: progress(min(start + share * fraction, 1.0), stage_name)

    return for_stage


def get_selected_files() -> list[str]:
    """Validate and return the tables selected in settings.main_settings.generated_files."""
    selected_files = list(dict.fromkeys(s.generated_files))
    unsupported_files = [name for name in selected_files if name not in DATASET_NAMES]

    if unsupported_files:
        raise ValueError(f"Unsupported table names in generated_files: {unsupported_files}. "
                         f"Use any of {DATASET_NAMES}.")
    if not selected_files:
        raise ValueError("generated_files must not be empty.")

    return selected_files


def seed_faker() -> None:
    """Seed the Faker instance used for names, phone numbers and bank accounts (NumPy uses func/rng.py streams)."""
    if s.random_state is not None:
        customer.fake.seed_instance(s.random_state)


def get_order_generation_params(product_data: pd.DataFrame) -> dict:
    """
    Build product parameters required to generate order lines.

    Returns:
    dict: Product IDs and sales weights by category and product type, category probabilities and lookups by product.
    """
    params = get_product_selection_params(product_data)
    by_type = product_data.groupby("product_type")
    params["product_ids_by_type"] = {name: group["product_id"].to_numpy() for name, group in by_type}
    params["product_weights_by_type"] = {name: product_sales_weights(group) for name, group in by_type}
    params["category_by_type"] = by_type["category"].first().to_dict()
    indexed = product_data.set_index("product_id")
    params["product_type_by_id"] = indexed["product_type"]
    params["category_by_id"] = indexed["category"]
    return params


def get_product_selection_params(product_data: pd.DataFrame) -> dict:
    """
    Build category-aware product selection parameters for order generation.

    Category weights are the target revenue share divided by the category's average price, so expensive categories
    do not take over revenue just because their unit prices are high.

    Returns:
    dict: Product IDs and sales weights by category, and category probabilities adjusted by average price.
    """
    product_ids_by_category = {}
    product_weights_by_category = {}
    category_weights = {}
    average_price = product_data.groupby("category")["sales_price_gross"].mean()

    for category, category_data in product_data.groupby("category"):
        product_ids_by_category[category] = category_data["product_id"].to_numpy()
        product_weights_by_category[category] = product_sales_weights(category_data)
        target_revenue_weight = ms.category_revenue_target_weights.get(category, 0)
        if target_revenue_weight > 0 and average_price[category] > 0:
            category_weights[category] = target_revenue_weight / average_price[category]

    return {
        "product_ids_by_category": product_ids_by_category,
        "product_weights_by_category": product_weights_by_category,
        "product_category_weights": category_weights,
    }


def product_sales_weights(group: pd.DataFrame) -> np.ndarray:
    """Sales weight of products of one category: popularity times the brand's weight to brand_sales_weight_power."""
    brand_weights = group["brand"].map(ms.category_brand_weights[group["category"].iloc[0]]).fillna(1)
    return (group["product_popularity"].astype(float).to_numpy()
            * np.power(brand_weights.astype(float).to_numpy(), ms.brand_sales_weight_power))
