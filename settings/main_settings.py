# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Sales settings:

# Below you can set the years for which you would like to generate data. The setting works in a "from-to" option,
# meaning that if you set the start_year to 2010 and the end_year to 2020, the generated data will include orders
# from the beginning of 2010 to the end of 2020.
start_year = 2023
end_year = 2024

# Below you can set the seasonality for months and days of the week. Additionally, there is an option to set the
# average year-over-year growth. If sales are expected to decrease, you can enter a negative value here.
base_monthly_seasonality = [0.06, 0.07, 0.08, 0.08, 0.08, 0.06, 0.07, 0.08, 0.08, 0.10, 0.21, 0.16]
base_weekday_seasonality = [0.24, 0.17, 0.03, 0.05, 0.07, 0.15, 0.23]
annual_growth_rate = 0.20

# Below you can set the number of rows for each type of data, such as customers, products, and order lines.
# If you want to have more orders from returning customers in the data, the number of customers relative
# to the number of order lines should be smaller. It’s worth testing different scenarios in this case.
# Have fun!
customer_data_rows = 40000
product_data_rows = 60000
order_data_rows = 50000

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Product & category settings:

# Below, I have prepared the basic mapping of categories and brands. You can modify them as needed,
# while maintaining the structure below.
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

# Since each category may have its own pricing characteristics, below I have prepared a simple mapping that includes
# category names and the purchase price range from value X to value Y, from which a product's value will be
# randomly selected.
price_ranges = {
    "Electronics":      (500, 8000),
    "Clothing":         (20, 300),
    "Home & Garden":    (30, 5000),
    "Sports":           (30, 3000),
    "Beauty":           (10, 500),
    "Toys":             (30, 250),
    "Automotive":       (100, 3000),
}

# Categories also have their own margin characteristics, which can be seen especially when comparing electronics, and
# clothing. Therefore, I decided that in this case, custom modifications can also be made so that the margin
# differences vary depending on the category.
margin_ranges = {
    "Electronics":      (0.00, 0.10),
    "Clothing":         (0.15, 0.60),
    "Home & Garden":    (0.10, 0.50),
    "Sports":           (0.15, 0.65),
    "Beauty":           (0.10, 0.50),
    "Toys":             (0.15, 0.35),
    "Automotive":       (0.15, 0.35),
}

# Below, you can set the product colors along with their frequency of occurrence.
colors_with_probabilities = {
    "black":    0.40,
    "red":      0.08,
    "blue":     0.08,
    "green":    0.12,
    "yellow":   0.06,
    "white":    0.10,
    "pink":     0.11,
    "brown":    0.10,
}

# Below, you can set the product payment methods along with their frequency of occurrence.
payment_method_with_probabilities = {
    "BLIK":         0.75,
    "PayU":         0.15,
    "Bank transfer":0.05,
    "COD":          0.10,
}

# Below, you can set the delivery methods along with their frequency of occurrence.
delivery_method_with_probabilities = {
    "InPost":       0.70,
    "DHL":          0.10,
    "DPD":          0.15,
    "UPS":          0.06,
    "FedEx":        0.04,
}