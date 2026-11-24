"""Products: catalog leaves (category, type, brand, series, model) drawn by weight, with prices and margins."""
import numpy as np
import pandas as pd

import func.data as d
import settings.category_hierarchy as ch
import settings.market_settings as ms
import settings.product_catalog as pc

category_brand_weights = ms.category_brand_weights
product_catalog = pc.product_catalog
subcategory_by_product_type = ch.subcategory_by_product_type
categories, categories_probabilities = d.get_param_list_and_normalized_probabilities(ms.categories_with_probabilities)
colors, colors_probabilities = d.get_param_list_and_normalized_probabilities(ms.colors_with_probabilities)


def catalog_leaves():
    """
    Every (category, product type, brand, series, model) of the catalog with its probability: category share ×
    product type weight × brand weight, split equally between the brand's series and each series' models.

    Returns:
    pd.DataFrame: One row per catalog leaf.
    """
    rows = []
    category_p = dict(zip(categories, categories_probabilities, strict=True))
    for category, product_types in product_catalog.items():
        if category_p.get(category, 0) <= 0:
            continue
        type_names, type_p = d.get_param_list_and_normalized_probabilities(
            {name: definition["weight"] for name, definition in product_types.items()})
        for product_type, p_type in zip(type_names, type_p, strict=True):
            definition = product_types[product_type]
            brands = definition["brand_series_models"]
            brand_names, brand_p = d.get_param_list_and_normalized_probabilities(
                {brand: category_brand_weights[category].get(brand, 1) for brand in brands})
            for brand, p_brand in zip(brand_names, brand_p, strict=True):
                series = brands[brand]
                for series_name, models in series.items():
                    for model in models:
                        rows.append((category, product_type, brand, series_name, model,
                                     category_p[category] * p_type * p_brand / len(series) / len(models),
                                     *definition["price_range"], *definition["margin_range"]))
    return pd.DataFrame(rows, columns=["category", "product_type", "brand", "product_series", "product_model",
                                       "probability", "price_low", "price_high", "margin_low", "margin_high"])


def generate_product_data(num_products: int, generator: np.random.Generator, progress=None) -> pd.DataFrame:
    """
    Generate a DataFrame containing product data (vectorized: one draw of catalog leaves for all products).

    Parameters:
    num_products (int): The number of products to generate.
    generator (np.random.Generator): Random stream.
    progress (callable, optional): Called with the completed fraction (0-1).

    Returns:
    pd.DataFrame: A DataFrame containing the generated product data.
    """
    leaves = catalog_leaves()
    probability = leaves["probability"].to_numpy()
    chosen = leaves.iloc[generator.choice(len(leaves), size=num_products, p=probability / probability.sum())]
    chosen = chosen.reset_index(drop=True)
    d.report_progress(progress, 1, 2, steps=2)

    price = chosen["price_low"] + generator.random(num_products) * (chosen["price_high"] - chosen["price_low"])
    margin = chosen["margin_low"] + generator.random(num_products) * (chosen["margin_high"] - chosen["margin_low"])
    data = pd.DataFrame({
        "product_id": np.arange(200001, 200001 + num_products),
        "net_purchase_price": price.round(2),
        "sales_margin": margin.round(4),
        "currency": "PLN",
        "category": chosen["category"],
        "subcategory": [get_subcategory(c, t) for c, t in zip(chosen["category"], chosen["product_type"], strict=True)],
        "product_type": chosen["product_type"],
        "brand": chosen["brand"],
        "product_series": chosen["product_series"],
        "product_model": chosen["product_model"],
        "product_name": (chosen["product_type"] + " " + chosen["brand"] + " " + chosen["product_series"] + " "
                         + chosen["product_model"]),
        "product_popularity": np.round(generator.lognormal(mean=0, sigma=ms.product_popularity_sigma,
                                                          size=num_products), 6),
        "color": generator.choice(np.array(colors), size=num_products, p=colors_probabilities),
    })

    # Add sales prices. The drawn margin gives a target price, cost / (1 - margin); the list price is that price with
    # VAT rounded to end in 9. The net price is the list price without VAT, and sales_margin the margin it really
    # leaves, so gross / net = 1 + vat_rate on every product.
    target_net = data['net_purchase_price'] / (1 - data['sales_margin'])
    data['sales_price_gross'] = (target_net * (1 + ms.vat_rate)).apply(d.round_to_9).astype(float)
    data['sales_price_net'] = net_price(data['sales_price_gross'])
    data['sales_margin'] = (1 - data['net_purchase_price'] / data['sales_price_net']).round(4)
    data = data[[column for column in data.columns if column != 'sales_price_gross'] + ['sales_price_gross']]
    d.report_progress(progress, 2, 2, steps=2)

    return data

def net_price(gross):
    """Price without VAT of a gross price, to the grosz: gross / (1 + vat_rate)."""
    return (gross / (1 + ms.vat_rate)).round(2)


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
