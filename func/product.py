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

def catalog_leaves():
    """
    Every (category, product type, brand, series, model) of the catalog with its probability: category share ×
    product type weight × brand weight, split equally between the brand's series and each series' models.

    Returns:
    pd.DataFrame: One row per catalog leaf.
    """
    rows = []
    category_p = dict(zip(categories, categories_probabilities))
    for category, product_types in product_catalog.items():
        if category_p.get(category, 0) <= 0:
            continue
        type_names, type_p = d.get_param_list_and_normalized_probabilities(
            {name: definition["weight"] for name, definition in product_types.items()})
        for product_type, p_type in zip(type_names, type_p):
            definition = product_types[product_type]
            brands = definition["brand_series_models"]
            brand_names, brand_p = d.get_param_list_and_normalized_probabilities(
                {brand: category_brand_weights[category].get(brand, 1) for brand in brands})
            for brand, p_brand in zip(brand_names, brand_p):
                series = brands[brand]
                for series_name, models in series.items():
                    for model in models:
                        rows.append((category, product_type, brand, series_name, model,
                                     category_p[category] * p_type * p_brand / len(series) / len(models),
                                     *definition["price_range"], *definition["margin_range"]))
    return pd.DataFrame(rows, columns=["category", "product_type", "brand", "product_series", "product_model",
                                       "probability", "price_low", "price_high", "margin_low", "margin_high"])


def generate_products(num_products, progress=None):
    """
    Generate a DataFrame containing product data (vectorized: one draw of catalog leaves for all products).

    Parameters:
    num_products (int): The number of products to generate.

    Returns:
    pd.DataFrame: A DataFrame containing the generated product data.
    """
    leaves = catalog_leaves()
    probability = leaves["probability"].to_numpy()
    chosen = leaves.iloc[np.random.choice(len(leaves), size=num_products, p=probability / probability.sum())]
    chosen = chosen.reset_index(drop=True)
    d.report_progress(progress, 1, 2, steps=2)

    price = chosen["price_low"] + np.random.random(num_products) * (chosen["price_high"] - chosen["price_low"])
    margin = chosen["margin_low"] + np.random.random(num_products) * (chosen["margin_high"] - chosen["margin_low"])
    data = pd.DataFrame({
        "product_id": np.arange(200001, 200001 + num_products),
        "net_purchase_price": price.round(2),
        "sales_margin": margin.round(4),
        "currency": "PLN",
        "category": chosen["category"],
        "subcategory": [get_subcategory(c, t) for c, t in zip(chosen["category"], chosen["product_type"])],
        "product_type": chosen["product_type"],
        "brand": chosen["brand"],
        "product_series": chosen["product_series"],
        "product_model": chosen["product_model"],
        "product_name": (chosen["product_type"] + " " + chosen["brand"] + " " + chosen["product_series"] + " "
                         + chosen["product_model"]),
        "product_popularity": np.round(np.random.lognormal(mean=0, sigma=ms.product_popularity_sigma,
                                                           size=num_products), 6),
        "color": np.random.choice(colors, size=num_products, p=colors_probabilities),
    })

    # Add sales prices. sales_margin is a gross margin, so price = cost / (1 - margin).
    data['sales_price_net'] = data['net_purchase_price'] / (1 - data['sales_margin'])
    data['sales_price_gross'] = (data['sales_price_net'] * (1 + ms.vat_rate)).apply(d.round_to_9).astype(float)
    d.report_progress(progress, 2, 2, steps=2)

    return data

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

def generate_product_data(num_products, progress=None):
    """
    Generate product data.

    Parameters:
    num_products (int): The number of products to generate.

    Returns:
    pd.DataFrame: A DataFrame containing the generated product data.
    """
    # Generate source:
    product_data = generate_products(num_products, progress)

    return product_data
