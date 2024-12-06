# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Date settings:

start_year = 2023
end_year = 2024

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Seasonality settings:

base_monthly_seasonality = [0.06, 0.07, 0.08, 0.09, 0.08, 0.06, 0.07, 0.08, 0.08, 0.10, 0.21, 0.15]
base_weekday_seasonality = [0.20, 0.15, 0.1, 0.1, 0.1, 0.15, 0.20]
annual_growth_rate = 0.20

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Size of data settings:

customer_data_rows = 40000
product_data_rows = 60000
order_data_rows = 100000

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Products & categories settings:

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
        "L'Oréal", "Nivea", "Maybelline", "Estée Lauder", "Lancôme", "Dior", "Chanel", "MAC", "Revlon",
        "Garnier", "Neutrogena", "Pantene", "Kylie", "Yves Rocher"
    ],
    "Toys": [
        "Lego", "Hasbro", "Mattel", "Playmobil", "Fisher-Price", "Barbie", "Hot Wheels"
    ],
    "Automotive": [
        "Bosch", "Michelin", "Goodyear", "Continental", "Castrol", "Bridgestone", "Hankook", "Pirelli", "Mobil",
        "Valeo", "Bilstein", "Brembo", "Ferodo", "Monroe"
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
    "black":    0.35,
    "red":      0.08,
    "blue":     0.08,
    "green":    0.12,
    "yellow":   0.06,
    "white":    0.10,
    "pink":     0.11,
    "brown":    0.10,
}