import pandas as pd
import numpy as np
from faker import Faker

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language:
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Variables:

# List of brands for each category:
categories_brands = {
    "Electronics": [
        "Samsung", "Apple", "Sony", "LG", "Philips", "Huawei", "Lenovo", "Dell", "HP", "Panasonic",
        "Acer", "Asus", "Toshiba", "Xiaomi", "Microsoft", "Nokia", "Canon", "Epson", "Garmin", "Polar"
    ],
    "Clothing": [
        "Nike", "Adidas", "Zara", "H&M", "Puma", "Levi's", "Tommy Hilfiger", "Calvin Klein", "Under Armour",
        "Gap", "Ralph Lauren", "Patagonia", "The North Face", "Columbia", "Reebok", "New Balance", "Gucci", "Prada", "Versace"
    ],
    "Home & Garden": [
        "Bosch", "Tefal", "Black+Decker", "DeLonghi", "Dyson", "Rowenta", "Electrolux", "Miele", "Philips",
        "Whirlpool", "Gardena", "Braun", "Kenwood", "Gorenje", "Russell Hobbs", "Zanussi", "Fiskars"
    ],
    "Sports": [
        "Nike", "Adidas", "Puma", "Under Armour", "Asics", "Reebok", "New Balance", "Columbia", "Patagonia", "The North Face",
        "Salomon", "Mammut", "Arc'teryx", "Merrell", "Decathlon", "Wilson", "Head", "Yonex", "Lululemon", "Fila"
    ],
    "Beauty": [
        "L'Oréal", "Nivea", "Maybelline", "Estée Lauder", "Clinique", "Lancôme", "Dior", "Chanel", "MAC", "Revlon",
        "Garnier", "Neutrogena", "Pantene", "Kylie", "Yves Rocher"
    ],
    "Toys": [
        "Lego", "Hasbro", "Mattel", "Playmobil", "Fisher-Price", "Barbie", "Hot Wheels"
    ],
    "Automotive": [
        "Bosch", "Michelin", "Goodyear", "Continental", "Castrol", "Bridgestone", "Hankook", "Pirelli", "Shell", "Mobil",
        "NGK", "Valeo", "Denso", "Delphi", "ZF", "KYB", "Bilstein", "Brembo", "Ferodo", "Monroe"
    ],
}

# Price ranges for each category:
price_ranges = {
    "Electronics":      (500, 8000),
    "Clothing":         (20, 300),
    "Home & Garden":    (30, 5000),
    "Sports":           (30, 3000),
    "Beauty":           (10, 500),
    "Toys":             (30, 250),
    "Automotive":       (100, 3000),
}

# Margin ranges for each category:
margin_ranges = {
    "Electronics":      (0.00, 0.10),
    "Clothing":         (0.15, 0.60),
    "Home & Garden":    (0.10, 0.50),
    "Sports":           (0.15, 0.65),
    "Beauty":           (0.10, 0.50),
    "Toys":             (0.15, 0.35),
    "Automotive":       (0.15, 0.35),
}

# Colors definition with probabilities:
colors_with_probabilities = {
    "Black":    0.35,
    "Red":      0.08,
    "Blue":     0.08,
    "Green":    0.12,
    "Yellow":   0.06,
    "White":    0.10,
    "Pink":     0.11,
    "Brown":    0.10,
}

# List of colors & list of probabilities:
colors = list(colors_with_probabilities.keys())
probabilities = list(colors_with_probabilities.values())

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_products(num_products):
    # First step - create a dictionary with product source:
    data = {
        "product_id": range(100001, 100001 + num_products),
        "net_purchase_price": [],
        "sales_margin": [],
        "currency": ["PLN"] * num_products,
        "category": [],
        "brand": [],
        "color": [np.random.choice(colors, p=probabilities) for _ in range(num_products)],
    }

    # Second step - generate source where are additional dependencies:
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
    # Round to the nearest integer first:
    rounded_price = round(price)

    # Ensure the last digit is 9:
    if rounded_price % 10 != 9:
        rounded_price = (rounded_price // 10) * 10 + 9

    return rounded_price

def generate_product_data(num_products):
    # Generate source:
    product_data = generate_products(num_products)

    return product_data