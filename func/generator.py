import pandas as pd
import numpy as np
from pathlib import Path
from faker import Faker
import func.data as d
from func import assembler as a, customer as c, order as o, product as p, log as l, format as f, save as sv, localization as loc
from func import anomaly as an, behaviour as b, calendar as cal, experiments as ex, fulfilment as ff, marketing as mk, prices as pr, quality as q, rng
import settings.main_settings as s
import settings.market_settings as ms

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Paths:

# Path to directories (relative to the repository root, so the generator works from any working directory):
PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_DIR / "source"
EXPORT_DIR = PROJECT_DIR / "export"

# Source files paths:
POSTAL_CODE_DATA = SOURCE_DIR / "pl_postal_code.csv"

# Export files paths. Source tables first, then the joined sales lines, then the extra tables:
DATASET_NAMES = ["customer_data", "product_data", "order_data", "sales_data", "price_history", "shipment_data",
                 "return_data", "campaign_data", "session_data", "experiment_data", "experiment_assignment_data",
                 "anomaly_data", "quality_issue_data"]
SOURCE_DATASETS = {"customer_data", "product_data", "order_data"}
saving_paths = {name: EXPORT_DIR / f"{name}.{s.saving_format}" for name in DATASET_NAMES}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_full_sales_data():
    """
    Generate the datasets selected in settings and save them to the export directory
    in the configured format (parquet or csv).
    """
    generated_data = run_generation_pipeline()
    EXPORT_DIR.mkdir(exist_ok=True)
    sv.save_generated_outputs(generated_data, saving_paths)

# Share of total run time per stage, used to turn stage progress into overall progress:
STAGE_SHARES = {"customer_data": 0.40, "product_data": 0.15, "order_data": 0.35, "sales_data": 0.10}

def run_generation_pipeline(progress=None):
    """
    Generate datasets selected in the settings file.

    Source tables (customers, products, order lines) are generated whenever a selected table needs them. Anomalies
    and data quality issues are added to the source tables before the sales lines are joined.

    Parameters:
    progress (callable, optional): Called as progress(fraction, stage_name) while data is generated.

    Returns:
    dict: Dataset names mapped to generated DataFrames, in the order of DATASET_NAMES.
    """
    stage_progress = make_stage_progress(progress)
    set_random_state()
    l.log_info("Rozpoczynam przygotowanie danych.")

    selected_files = get_selected_files()
    needed = required_sources(selected_files)
    tables = {"customer_data": None, "product_data": None, "order_data": None}
    extra = {}

    if "customer_data" in needed:
        tables["customer_data"] = c.generate_customer_data(s.customer_data_rows)
        d.report_progress(stage_progress("customer_data"), 1, 1)

    if "product_data" in needed:
        product_data = p.generate_product_data(s.product_data_rows, stage_progress("product_data"))
        tables["product_data"] = pr.add_life_cycle(product_data, rng.stream("prices"))

    if "order_data" in needed:
        customers, products = tables["customer_data"], tables["product_data"]
        marketing = rng.stream("marketing")
        plain_calendar = cal.build_calendar(rng.stream("calendar"))
        campaigns, campaign_effects, own_effects = mk.draw_campaigns(plain_calendar, marketing)
        calendar = cal.build_calendar(rng.stream("calendar"),
                                      day_multiplier=mk.campaign_multiplier(campaign_effects, len(plain_calendar)))
        calendar = mk.add_campaign_columns(calendar, campaign_effects)
        extra["campaign_data"] = campaigns[mk.CAMPAIGN_COLUMNS]
        order_params = get_order_generation_params(products)
        behaviour = b.draw_customer_behaviour(customers, calendar, rng.stream("behaviour"),
                                              order_params["product_category_weights"])
        customers = tables["customer_data"] = b.add_behaviour_columns(customers, behaviour)
        extra["price_history"] = pr.build_price_history(products, rng.stream("prices"))
        price_book = pr.PriceBook(products, extra["price_history"], calendar)
        order_data = o.generate_order_data(s.order_data_rows, order_params, behaviour, calendar, price_book,
                                           rng.stream("orders"), stage_progress("order_data"))
        order_data, anomalies = an.inject_anomalies(order_data, customers, products)

        logistics = rng.stream("logistics")
        order_data = an.renumber_orders(ff.add_order_times(order_data, logistics))
        order_data, customers = mk.add_marketing_columns(order_data, customers, calendar, campaigns, own_effects,
                                                         marketing)
        tables["customer_data"] = customers
        extra["session_data"], session_of_order = mk.build_sessions(order_data, rng.stream("sessions"))
        order_data = mk.add_session_ids(order_data, session_of_order)
        order_data, extra["experiment_data"], extra["experiment_assignment_data"] = ex.run_experiments(
            order_data, extra["session_data"], calendar, rng.stream("experiments"))
        order_data = ff.add_unit_prices(order_data, price_book)
        order_data, bulky_orders = ff.fit_delivery_to_products(order_data, products, logistics)
        extra["shipment_data"] = ff.build_shipments(order_data, calendar, bulky_orders, logistics)
        extra["return_data"], spikes = ff.build_returns(order_data, products, customers, extra["shipment_data"],
                                                        rng.stream("returns"))
        tables["order_data"] = order_data
        extra["anomaly_data"] = an.anomaly_frame(anomalies + spikes)

    tables, extra["quality_issue_data"] = q.inject_quality_issues(tables)

    if "sales_data" in selected_files:
        extra["sales_data"] = a.build_sales_data(tables["order_data"], tables["product_data"], tables["customer_data"])

    generated_data = {}
    for name in DATASET_NAMES:
        if name not in selected_files:
            continue
        frame = tables.get(name) if name in SOURCE_DATASETS else extra.get(name)
        generated_data[name] = loc.localize_dataset(frame)
        log_characteristics(name, generated_data[name])

    d.report_progress(stage_progress("sales_data"), 1, 1)
    l.log_info('Dane zostały przygotowane.')

    return generated_data

def required_sources(selected_files):
    """
    Return the source tables needed for the selected outputs: every table except customers and products alone
    needs the orders, and the orders need customers and products.

    Parameters:
    selected_files (list): Selected dataset names.

    Returns:
    set: Source dataset names to generate.
    """
    if set(selected_files) - {"customer_data", "product_data"}:
        return set(SOURCE_DATASETS)
    return set(selected_files)

def log_characteristics(name, data):
    """Log a short summary of one generated table."""
    loggers = {
        "customer_data": log_customer_data_characteristics,
        "product_data": log_product_data_characteristics,
        "order_data": log_order_data_characteristics,
        "sales_data": log_sales_data_characteristics,
    }
    if name in loggers:
        loggers[name](data)
    else:
        l.log_section(f'Podsumowanie: {name}')
        l.log_metric('Liczba wierszy', f.format_number(len(data)))

def make_stage_progress(progress):
    """
    Build a factory of per-stage callbacks that report overall progress.

    Parameters:
    progress (callable or None): Overall callback taking (fraction, stage_name).

    Returns:
    callable: stage_name -> callback taking the stage fraction (0-1), or None when progress is None.
    """
    stage_names = list(STAGE_SHARES)

    def for_stage(stage_name):
        if progress is None:
            return None
        start = sum(STAGE_SHARES[name] for name in stage_names[:stage_names.index(stage_name)])
        share = STAGE_SHARES[stage_name]
        return lambda fraction: progress(min(start + share * fraction, 1.0), stage_name)

    return for_stage

def get_selected_files():
    """
    Validate and return the list of datasets selected in settings.

    Returns:
    list: Selected dataset names.
    """
    selected_files = list(dict.fromkeys(s.generated_files))
    available_files = set(saving_paths.keys())
    unsupported_files = [file_name for file_name in selected_files if file_name not in available_files]

    if unsupported_files:
        raise ValueError(f"Nieobsługiwane nazwy generowanych plików: {unsupported_files}")
    if not selected_files:
        raise ValueError("Ustawienie generated_files nie może być puste.")

    return selected_files

def set_random_state():
    """
    Set deterministic random state for NumPy and Faker when configured.
    """
    if s.random_state is not None:
        np.random.seed(s.random_state)
        Faker.seed(s.random_state)
        c.fake.seed_instance(s.random_state)
        p.fake.seed_instance(s.random_state)
        l.log_info(f'Ustawiono ziarno losowości random_state={s.random_state}.')

def get_order_generation_params(product_data):
    """
    Build product parameters required to generate order lines.

    Parameters:
    product_data (pd.DataFrame): Generated product data.

    Returns:
    dict: Product IDs and sales weights by category, category probabilities and gross prices by product.
    """
    params = get_product_selection_params(product_data)
    by_type = product_data.groupby("product_type")
    params["product_ids_by_type"] = {name: group["product_id"].to_numpy() for name, group in by_type}
    params["product_weights_by_type"] = {
        name: group["product_popularity"].astype(float).to_numpy() * np.power(
            group["brand"].map(ms.category_brand_weights[group["category"].iloc[0]]).fillna(1).astype(float).to_numpy(),
            ms.brand_sales_weight_power)
        for name, group in by_type}
    params["category_by_type"] = by_type["category"].first().to_dict()
    indexed = product_data.set_index("product_id")
    params["product_type_by_id"] = indexed["product_type"]
    params["category_by_id"] = indexed["category"]
    return params

def get_product_selection_params(product_data):
    """
    Build category-aware product selection parameters for order generation.

    Parameters:
    product_data (pd.DataFrame): Generated product data.

    Returns:
    dict: Product IDs by category and category probabilities adjusted by average price.
    """
    product_ids_by_category = {
        category: category_data['product_id'].to_numpy()
        for category, category_data in product_data.groupby('category')
    }
    product_weights_by_category = {}

    category_average_price = product_data.groupby('category')['sales_price_gross'].mean()
    category_weights = {}

    for category, category_data in product_data.groupby('category'):
        product_ids = product_ids_by_category[category]
        target_revenue_weight = ms.category_revenue_target_weights.get(category, 0)
        average_price = category_average_price[category]
        if target_revenue_weight > 0 and average_price > 0 and len(product_ids) > 0:
            category_weights[category] = target_revenue_weight / average_price
        product_weights_by_category[category] = get_product_sales_weights(category_data)

    return {
        'product_ids_by_category': product_ids_by_category,
        'product_weights_by_category': product_weights_by_category,
        'product_category_weights': category_weights,
    }

def get_product_sales_weights(category_data):
    """
    Build product sales weights from product popularity and brand sales power.

    Parameters:
    category_data (pd.DataFrame): Product rows for one category.

    Returns:
    np.array: Product sales weights.
    """
    weights = category_data['product_popularity'].astype(float).to_numpy()
    brand_weights = category_data['brand'].map(ms.category_brand_weights[category_data['category'].iloc[0]]).astype(float).to_numpy()
    weights = weights * np.power(brand_weights, ms.brand_sales_weight_power)

    return weights

def format_decimal(number, decimal_places=2):
    """
    Format a number with a space as the thousands separator and a comma as the decimal separator.

    Parameters:
    number (float or int): Number to format.
    decimal_places (int): Number of decimal places.

    Returns:
    str: Formatted number.
    """
    formatted_number = f"{number:,.{decimal_places}f}"
    return formatted_number.replace(",", " ").replace(".", ",")

def get_top_value_description(data, column_name):
    """
    Return the most common value in a column with its share.

    Parameters:
    data (pd.DataFrame): Dataset to analyze.
    column_name (str): Column name.

    Returns:
    str: Description of the most common value and its share.
    """
    top_value = data[column_name].value_counts(normalize=True).head(1)

    if top_value.empty:
        return "n/a"

    return f"{top_value.index[0]} ({format_decimal(top_value.iloc[0] * 100, 1)}%)"

def log_customer_data_characteristics(customer_data):
    """
    Log basic characteristics of generated customer data.

    Parameters:
    customer_data (pd.DataFrame): Generated customer dataset.
    """
    l.log_section('Podsumowanie danych klientów')
    l.log_metric('Liczba wierszy', f.format_number(len(customer_data)))
    l.log_metric('Unikalni klienci', f.format_number(customer_data['customer_id'].nunique()))
    l.log_metric('Zakres ID klientów', f"{customer_data['customer_id'].min()} - {customer_data['customer_id'].max()}")
    l.log_metric('Zakres wieku', f"{customer_data['age'].min()} - {customer_data['age'].max()}")
    l.log_metric('Średni wiek', format_decimal(customer_data['age'].mean(), 1))
    l.log_metric('Najczęstsza płeć', get_top_value_description(customer_data, 'gender'))
    l.log_metric('Unikalne miasta', f.format_number(customer_data['city'].nunique()))
    l.log_metric('Najczęstsze miasto', get_top_value_description(customer_data, 'city'))

def log_product_data_characteristics(product_data):
    """
    Log basic characteristics of generated product data.

    Parameters:
    product_data (pd.DataFrame): Generated product dataset.
    """
    l.log_section('Podsumowanie danych produktów')
    l.log_metric('Liczba wierszy', f.format_number(len(product_data)))
    l.log_metric('Unikalne produkty', f.format_number(product_data['product_id'].nunique()))
    l.log_metric('Zakres ID produktów', f"{product_data['product_id'].min()} - {product_data['product_id'].max()}")
    l.log_metric('Kategorie', f.format_number(product_data['category'].nunique()))
    l.log_metric('Podkategorie', f.format_number(product_data['subcategory'].nunique()))
    l.log_metric('Typy produktów', f.format_number(product_data['product_type'].nunique()))
    l.log_metric('Marki', f.format_number(product_data['brand'].nunique()))
    l.log_metric('Najczęstsza kategoria', get_top_value_description(product_data, 'category'))
    l.log_metric('Najczęstsza podkategoria', get_top_value_description(product_data, 'subcategory'))
    l.log_metric('Najczęstszy typ produktu', get_top_value_description(product_data, 'product_type'))
    l.log_metric('Średnia cena brutto', f"{format_decimal(product_data['sales_price_gross'].mean(), 2)} PLN")
    l.log_metric('Zakres cen brutto', f"{format_decimal(product_data['sales_price_gross'].min(), 2)} - {format_decimal(product_data['sales_price_gross'].max(), 2)} PLN")
    l.log_metric('Średnia marża', f"{format_decimal(product_data['sales_margin'].mean() * 100, 1)}%")

def log_order_data_characteristics(order_data):
    """
    Log basic characteristics of generated order data.

    Parameters:
    order_data (pd.DataFrame): Generated order dataset.
    """
    order_lines_per_order = order_data.groupby('order_id').size()

    l.log_section('Podsumowanie danych zamówień')
    l.log_metric('Liczba wierszy', f.format_number(len(order_data)))
    l.log_metric('Unikalne zamówienia', f.format_number(order_data['order_id'].nunique()))
    l.log_metric('Zakres dat', f"{order_data['order_date'].min().date()} - {order_data['order_date'].max().date()}")
    l.log_metric('Unikalni klienci w zamówieniach', f.format_number(order_data['customer_id'].nunique()))
    l.log_metric('Unikalne produkty w zamówieniach', f.format_number(order_data['product_id'].nunique()))
    l.log_metric('Średnia liczba linii na zamówienie', format_decimal(order_lines_per_order.mean(), 2))
    l.log_metric('Średnia liczba sztuk w linii', format_decimal(order_data['quantity'].mean(), 2))
    l.log_metric('Linie z rabatem', f"{format_decimal((order_data['discount_rate'] > 0).mean() * 100, 1)}%")
    l.log_metric('Średni rabat', f"{format_decimal(order_data['discount_rate'].mean() * 100, 1)}%")
    l.log_metric('Najczęstsza metoda płatności', get_top_value_description(order_data, 'payment_method'))
    l.log_metric('Najczęstszy operator płatności', get_top_value_description(order_data, 'payment_provider'))
    l.log_metric('Najczęstsza metoda dostawy', get_top_value_description(order_data, 'delivery_method'))

def log_sales_data_characteristics(sales_data):
    """
    Log basic characteristics of the generated sales dataset.

    Parameters:
    sales_data (pd.DataFrame): Generated final sales dataset.
    """

    order_revenue = sales_data.groupby('order_id')['revenue_gross'].sum()
    category_revenue = sales_data.groupby('category')['revenue_gross'].sum().sort_values(ascending=False)
    subcategory_revenue = sales_data.groupby('subcategory')['revenue_gross'].sum().sort_values(ascending=False)
    margin_mass = (sales_data['sales_price_net_after_discount'] - sales_data['net_purchase_price']) * sales_data['quantity']
    category_margin_mass = margin_mass.groupby(sales_data['category']).sum().sort_values(ascending=False)
    subcategory_margin_mass = margin_mass.groupby(sales_data['subcategory']).sum().sort_values(ascending=False)
    top_category = "n/a"
    top_subcategory = "n/a"
    top_margin_mass_category = "n/a"
    top_margin_mass_subcategory = "n/a"

    if not category_revenue.empty:
        top_category_name = category_revenue.index[0]
        top_category_share = category_revenue.iloc[0] / sales_data['revenue_gross'].sum() * 100
        top_category = f"{top_category_name} ({format_decimal(top_category_share, 1)}%)"

    if not subcategory_revenue.empty:
        top_subcategory_name = subcategory_revenue.index[0]
        top_subcategory_share = subcategory_revenue.iloc[0] / sales_data['revenue_gross'].sum() * 100
        top_subcategory = f"{top_subcategory_name} ({format_decimal(top_subcategory_share, 1)}%)"

    if not category_margin_mass.empty:
        top_margin_mass_category_name = category_margin_mass.index[0]
        top_margin_mass_share = category_margin_mass.iloc[0] / margin_mass.sum() * 100
        top_margin_mass_category = f"{top_margin_mass_category_name} ({format_decimal(top_margin_mass_share, 1)}%)"

    if not subcategory_margin_mass.empty:
        top_margin_mass_subcategory_name = subcategory_margin_mass.index[0]
        top_margin_mass_subcategory_share = subcategory_margin_mass.iloc[0] / margin_mass.sum() * 100
        top_margin_mass_subcategory = f"{top_margin_mass_subcategory_name} ({format_decimal(top_margin_mass_subcategory_share, 1)}%)"

    l.log_section('Podsumowanie danych sprzedaży')
    l.log_metric('Liczba wierszy', f.format_number(len(sales_data)))
    l.log_metric('Unikalne zamówienia', f.format_number(sales_data['order_id'].nunique()))
    l.log_metric('Zakres dat', f"{sales_data['order_date'].min().date()} - {sales_data['order_date'].max().date()}")
    l.log_metric('Unikalni klienci', f.format_number(sales_data['customer_id'].nunique()))
    l.log_metric('Unikalne sprzedane produkty', f.format_number(sales_data['product_id'].nunique()))
    l.log_metric('Łączny przychód brutto', f"{format_decimal(sales_data['revenue_gross'].sum(), 2)} PLN")
    l.log_metric('Średnia wartość zamówienia', f"{format_decimal(order_revenue.mean(), 2)} PLN")
    l.log_metric('Mediana wartości zamówienia', f"{format_decimal(order_revenue.median(), 2)} PLN")
    l.log_metric('Średnia wartość linii', f"{format_decimal(sales_data['revenue_gross'].mean(), 2)} PLN")
    l.log_metric('Średnia liczba sztuk w linii', format_decimal(sales_data['quantity'].mean(), 2))
    l.log_metric('Linie z rabatem', f"{format_decimal((sales_data['discount_rate'] > 0).mean() * 100, 1)}%")
    l.log_metric('Średni rabat', f"{format_decimal(sales_data['discount_rate'].mean() * 100, 1)}%")
    l.log_metric('Największa kategoria wg przychodu', top_category)
    l.log_metric('Największa podkategoria wg przychodu', top_subcategory)
    l.log_metric('Największa kategoria wg masy marży', top_margin_mass_category)
    l.log_metric('Największa podkategoria wg masy marży', top_margin_mass_subcategory)
    l.log_metric('Najczęstsza metoda płatności', get_top_value_description(sales_data, 'payment_method'))
    l.log_metric('Najczęstszy operator płatności', get_top_value_description(sales_data, 'payment_provider'))
    l.log_metric('Najczęstsza metoda dostawy', get_top_value_description(sales_data, 'delivery_method'))

def get_pl_postal_code_data():
    """
    Read and return Polish postal code data from a CSV file.

    Returns:
    pd.DataFrame: A DataFrame containing the Polish postal code data.
    """
    pl_postal_code_data = pd.read_csv(POSTAL_CODE_DATA, sep=";")

    return pl_postal_code_data
