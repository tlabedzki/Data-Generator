import pandas as pd
import numpy as np
from pathlib import Path
from faker import Faker
from func import assembler as a, customer as c, order as o, product as p, log as l, format as f, save as sv, localization as loc
import settings.main_settings as s
import settings.market_settings as ms

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Paths:

# Path to directories:
SOURCE_DIR = Path("source")
EXPORT_DIR = Path("export")

# Create export directory if not exist:
if not EXPORT_DIR.exists():
    EXPORT_DIR.mkdir()

# Source files paths:
POSTAL_CODE_DATA = SOURCE_DIR / "pl_postal_code.csv"
SALES_DATA = EXPORT_DIR / "sales_data.csv"

# Export files paths:
saving_paths = {
    "customer_data": EXPORT_DIR / f"customer_data.{s.saving_format}",
    "product_data": EXPORT_DIR / f"product_data.{s.saving_format}",
    "order_data": EXPORT_DIR / f"order_data.{s.saving_format}",
    "sales_data": EXPORT_DIR / f"sales_data.{s.saving_format}",
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_full_sales_data():
    """
    Generate full sales data by merging customer, product, and order data,
    then export the merged data to a CSV file.

    This function performs the following steps:
    1. Logs the start of data preparation.
    2. Generates customer data.
    3. Retrieves the minimum and maximum customer IDs.
    4. Generates product data.
    5. Retrieves the minimum and maximum product IDs.
    6. Generates order data using customer and product ID ranges.
    7. Merges order data with product and customer data.
    8. Adds a calculated column for gross revenue.
    9. Sorts the merged data by order date.
    10. Logs the completion of data preparation.
    11. Exports the sorted data to a CSV file.
    12. Logs the success of the file save operation.
    """
    generated_data = run_generation_pipeline()
    sv.save_generated_outputs(generated_data, saving_paths)

def run_generation_pipeline():
    """
    Generate datasets selected in the settings file.

    Returns:
    dict: Dataset names mapped to generated DataFrames.
    """
    set_random_state()
    l.log_info("Rozpoczynam przygotowanie danych.")

    selected_files = get_selected_files()
    generated_data = {}

    customer_data = None
    product_data = None
    order_data = None

    if should_generate_source("customer_data", selected_files):
        customer_data = c.generate_customer_data(s.customer_data_rows)
        if "customer_data" in selected_files:
            localized_customer_data = loc.localize_dataset(customer_data)
            generated_data["customer_data"] = localized_customer_data
            log_customer_data_characteristics(localized_customer_data)

    if should_generate_source("product_data", selected_files):
        product_data = p.generate_product_data(s.product_data_rows)
        if "product_data" in selected_files:
            localized_product_data = loc.localize_dataset(product_data)
            generated_data["product_data"] = localized_product_data
            log_product_data_characteristics(localized_product_data)

    if should_generate_source("order_data", selected_files):
        order_data = o.generate_order_data(s.order_data_rows, get_order_generation_params(customer_data, product_data))
        if "order_data" in selected_files:
            localized_order_data = loc.localize_dataset(order_data)
            generated_data["order_data"] = localized_order_data
            log_order_data_characteristics(localized_order_data)

    if "sales_data" in selected_files:
        sales_data = a.build_sales_data(order_data, product_data, customer_data)
        localized_sales_data = loc.localize_dataset(sales_data)
        generated_data["sales_data"] = localized_sales_data
        log_sales_data_characteristics(localized_sales_data)

    l.log_info('Dane zostały przygotowane.')

    return generated_data

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
        o.fake.seed_instance(s.random_state)
        l.log_info(f'Ustawiono ziarno losowości random_state={s.random_state}.')

def should_generate_source(data_name, selected_files):
    """
    Check if a source dataset is required for selected outputs.

    Parameters:
    data_name (str): Source dataset name.
    selected_files (list): Selected dataset names.

    Returns:
    bool: True when the source dataset should be generated.
    """
    source_files = {"customer_data", "product_data", "order_data"}
    if data_name not in source_files:
        raise ValueError(f"Nieobsługiwana nazwa pliku źródłowego: {data_name}")

    return data_name in selected_files or "sales_data" in selected_files

def get_order_generation_params(customer_data=None, product_data=None):
    """
    Build ID ranges required to generate order data.

    Parameters:
    customer_data (pd.DataFrame, optional): Generated customer data.
    product_data (pd.DataFrame, optional): Generated product data.

    Returns:
    dict: Minimum and maximum customer and product IDs.
    """
    if customer_data is not None:
        customer_id_min = customer_data['customer_id'].min()
        customer_id_max = customer_data['customer_id'].max()
    else:
        customer_id_min = 100001
        customer_id_max = 100001 + s.customer_data_rows - 1

    if product_data is not None:
        product_id_min = product_data['product_id'].min()
        product_id_max = product_data['product_id'].max()
        product_selection_params = get_product_selection_params(product_data)
    else:
        product_id_min = 200001
        product_id_max = 200001 + s.product_data_rows - 1
        product_selection_params = {}

    params = {
        'customer_id_min': customer_id_min,
        'customer_id_max': customer_id_max,
        'product_id_min': product_id_min,
        'product_id_max': product_id_max
    }
    params.update(product_selection_params)

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
