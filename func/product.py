import pandas as pd
import numpy as np
from faker import Faker

import func.data as d
import settings.market_settings as ms
import settings.product_catalog as pc
import settings.category_hierarchy as ch

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language:
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Variables:

# List of brands for each category:
category_brand_weights = ms.category_brand_weights
product_catalog = pc.product_catalog
subcategory_by_product_type = ch.subcategory_by_product_type

# Categories definition with probabilities:
categories_with_probabilities = ms.categories_with_probabilities
categories, categories_probabilities = d.get_param_list_and_normalized_probabilities(categories_with_probabilities)

# Colors definition with probabilities:
colors_with_probabilities = ms.colors_with_probabilities
colors, colors_probabilities = d.get_param_list_and_normalized_probabilities(colors_with_probabilities)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_products(num_products):
    """
    Generate a DataFrame containing product data.

    Parameters:
    num_products (int): The number of products to generate.

    Returns:
    pd.DataFrame: A DataFrame containing the generated product data.
    """
    # First step - create a dictionary with product source:
    data = {
        "product_id": range(200001, 200001 + num_products),
        "net_purchase_price": [],
        "sales_margin": [],
        "currency": ["PLN"] * num_products,
        "category": [],
        "subcategory": [],
        "product_type": [],
        "brand": [],
        "product_series": [],
        "product_model": [],
        "product_name": [],
        "product_popularity": [],
        "color": [np.random.choice(colors, p=colors_probabilities) for _ in range(num_products)],
    }

    # Second step - create parameters with additional dependencies, which is why they need to be created in this step
    for _ in range(num_products):
        # Category & brand selection:
        category = np.random.choice(categories, p=categories_probabilities)
        product_type, product_definition = choose_product_type(category)
        subcategory = get_subcategory(category, product_type)
        brand, product_series, product_model = choose_brand_series_model(category, product_definition)
        product_name = build_product_name(product_type, brand, product_series, product_model)

        # Price & margin params:
        min_price, max_price = product_definition["price_range"]
        min_margin, max_margin = product_definition["margin_range"]

        # Append source:
        data["category"].append(category)
        data["subcategory"].append(subcategory)
        data["product_type"].append(product_type)
        data["brand"].append(brand)
        data["product_series"].append(product_series)
        data["product_model"].append(product_model)
        data["product_name"].append(product_name)
        data["product_popularity"].append(generate_product_popularity())
        data["net_purchase_price"].append(round(np.random.uniform(min_price, max_price), 2))
        data["sales_margin"].append(round(np.random.uniform(min_margin, max_margin), 4))

    # Transform to DataFrame:
    data = pd.DataFrame(data)

    # Add sales prices. sales_margin is a gross margin, so price = cost / (1 - margin).
    data['sales_price_net'] = data['net_purchase_price'] / (1 - data['sales_margin'])
    data['sales_price_gross_unrounded'] = data['sales_price_net'] * (1 + ms.vat_rate)
    data['sales_price_gross'] = data['sales_price_gross_unrounded'].apply(d.round_to_9).astype(float)

    # Drop unnecessary columns:
    data.drop(columns=['sales_price_gross_unrounded'], inplace=True)

    return pd.DataFrame(data)

def choose_product_type(category):
    """
    Choose a product type inside a category.

    Parameters:
    category (str): Product category.

    Returns:
    tuple: Selected product type and its catalog definition.
    """
    product_type_weights = {
        product_type: definition["weight"]
        for product_type, definition in product_catalog[category].items()
    }
    product_types, product_type_probabilities = d.get_param_list_and_normalized_probabilities(product_type_weights)
    product_type = np.random.choice(product_types, p=product_type_probabilities)

    return product_type, product_catalog[category][product_type]

def get_subcategory(category, product_type):
    """
    Return subcategory assigned to a category and product type.

    Parameters:
    category (str): Product category.
    product_type (str): Product type.

    Returns:
    str: Product subcategory.
    """
    return subcategory_by_product_type[category][product_type]


def choose_brand_series_model(category, product_definition):
    """
    Choose a brand, series, and model from a product type definition.

    Parameters:
    category (str): Product category.
    product_definition (dict): Product type definition.

    Returns:
    tuple: Selected brand, series, and model.
    """
    available_brands = product_definition["brand_series_models"]
    brand_weights = {
        brand: category_brand_weights[category].get(brand, 1)
        for brand in available_brands
    }
    brands, brand_probabilities = d.get_param_list_and_normalized_probabilities(brand_weights)
    brand = np.random.choice(brands, p=brand_probabilities)
    series_values = list(available_brands[brand].keys())
    product_series = np.random.choice(series_values)
    product_model = np.random.choice(available_brands[brand][product_series])

    return brand, product_series, product_model

def build_product_name(product_type, brand, product_series, product_model):
    """
    Build a product name in the required format.

    Parameters:
    product_type (str): Product type.
    brand (str): Product brand.
    product_series (str): Product series.
    product_model (str): Product model.

    Returns:
    str: Product name.
    """
    return f"{product_type} {brand} {product_series} {product_model}"

def generate_product_popularity():
    """
    Generate a long-tail product popularity score.

    Returns:
    float: Product popularity score.
    """
    return round(np.random.lognormal(mean=0, sigma=ms.product_popularity_sigma), 6)

def generate_product_data(num_products):
    """
    Generate product data.

    Parameters:
    num_products (int): The number of products to generate.

    Returns:
    pd.DataFrame: A DataFrame containing the generated product data.
    """
    # Generate source:
    product_data = generate_products(num_products)

    return product_data
