import pandas as pd
import numpy as np
from faker import Faker

import func.data as d
import settings.main_settings as s

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language:
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Variables:

# List of brands for each category:
categories_brands = s.categories_brands

# Price ranges for each category:
price_ranges = s.price_ranges

# Margin ranges for each category:
margin_ranges = s.margin_ranges

# Colors definition with probabilities:
colors_with_probabilities = s.colors_with_probabilities
colors, colors_probabilities = d.get_param_list_and_normalized_probabilities(colors_with_probabilities)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def get_param_list_and_normalized_probabilities(param_dict):
    """
    Extract the parameter list and normalized probabilities from a dictionary.

    Parameters:
    param_dict (dict): The input dictionary containing parameters and probabilities.

    Returns:
    list: The extracted parameter list.
    list: The normalized probabilities.
    """
    # Extract the parameter list and probabilities:
    param_list = list(param_dict.keys())
    probabilities = list(param_dict.values())

    # Normalize the probabilities:
    probabilities = probabilities / np.sum(probabilities)

    return param_list, probabilities

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
        "product_id": range(100001, 100001 + num_products),
        "net_purchase_price": [],
        "sales_margin": [],
        "currency": ["PLN"] * num_products,
        "category": [],
        "brand": [],
        "color": [np.random.choice(colors, p=colors_probabilities) for _ in range(num_products)],
    }

    # Second step - create parameters with additional dependencies, which is why they need to be created in this step
    for _ in range(num_products):
        # Category & brand selection:
        category = np.random.choice(list(categories_brands.keys()))
        brand = np.random.choice(categories_brands[category])

        # Price & margin params:
        min_price, max_price = price_ranges[category]
        min_margin, max_margin = margin_ranges[category]

        # Append source:
        data["category"].append(category)
        data["brand"].append(brand)
        data["net_purchase_price"].append(round(np.random.uniform(min_price, max_price), 2))
        data["sales_margin"].append(round(np.random.uniform(min_margin, max_margin), 4))

    # Transform to DataFrame:
    data = pd.DataFrame(data)

    # Add purchase_price_gross:
    data['sales_price_net'] = data['net_purchase_price'] * (1 + data['sales_margin'])
    data['sales_price_gross_unrounded'] = data['net_purchase_price'] * (1 + 0.23)
    data['sales_price_gross'] = data['sales_price_gross_unrounded'].apply(round_to_9).astype(float)

    # Drop unnecessary columns:
    data.drop(columns=['sales_price_gross_unrounded'], inplace=True)

    return pd.DataFrame(data)

def round_to_9(price):
    """
    Round the given price to the nearest integer and ensure the last digit is 9.

    Parameters:
    price (float): The input price to be rounded.

    Returns:
    int: The rounded price with the last digit as 9.
    """
    # Round to the nearest integer first:
    rounded_price = round(price)

    # Ensure the last digit is 9:
    if rounded_price % 10 != 9:
        rounded_price = (rounded_price // 10) * 10 + 9

    return rounded_price

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