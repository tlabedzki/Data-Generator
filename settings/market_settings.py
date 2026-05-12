# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Market settings:

# Product categories and brands. Each category must also exist in categories_with_probabilities,
# price_ranges, and margin_ranges.
categories_brands = {
    "Electronics": [
        "Samsung", "Apple", "Sony", "LG", "Philips", "Huawei", "Lenovo", "Dell", "HP", "Panasonic",
        "Acer", "Asus", "Toshiba", "Xiaomi", "Microsoft", "Nokia", "Canon", "Epson", "Garmin", "Polar",
        "JBL", "Bose", "GoPro", "Nintendo", "Logitech", "Brother", "Hisense", "TCL", "Miele", "Beko"
    ],
    "Clothing": [
        "Nike", "Adidas", "Zara", "H&M", "Puma", "Levi's", "Tommy Hilfiger", "Calvin Klein",
        "Under Armour", "Gap", "Ralph Lauren", "Patagonia", "The North Face", "Columbia", "Reebok",
        "New Balance", "Gucci", "Prada", "Versace", "Reserved", "Mohito", "Cropp", "House",
        "Sinsay", "Mango", "Vistula", "Wojas"
    ],
    "Home & Garden": [
        "Bosch", "Tefal", "Black+Decker", "DeLonghi", "Dyson", "Rowenta", "Electrolux", "Miele",
        "Philips", "Whirlpool", "Gardena", "Braun", "Kenwood", "Gorenje", "Russell Hobbs",
        "Zanussi", "Fiskars", "IKEA", "Karcher", "Makita", "Stanley", "Vileda", "Ambition",
        "Gerda", "Brabantia"
    ],
    "Sports": [
        "Nike", "Adidas", "Puma", "Under Armour", "Asics", "Reebok", "New Balance", "Columbia",
        "Patagonia", "The North Face", "Salomon", "Mammut", "Arc'teryx", "Merrell", "Decathlon",
        "Wilson", "Head", "Yonex", "Lululemon", "Fila", "4F", "Kross", "Giant", "Trek",
        "Spokey", "Martes", "Rossignol"
    ],
    "Beauty": [
        "L'Oreal", "Nivea", "Maybelline", "Estee Lauder", "Lancome", "Dior", "Chanel", "MAC",
        "Revlon", "Garnier", "Neutrogena", "Pantene", "Kylie", "Yves Rocher", "Bielenda", "Ziaja",
        "AA", "Eveline", "Vichy", "La Roche-Posay", "CeraVe", "The Ordinary", "Inglot"
    ],
    "Toys": [
        "Lego", "Hasbro", "Mattel", "Playmobil", "Fisher-Price", "Barbie", "Hot Wheels",
        "Ravensburger", "Trefl", "Cobi", "Schleich", "Brio", "Clementoni", "Spin Master"
    ],
    "Automotive": [
        "Bosch", "Michelin", "Goodyear", "Continental", "Castrol", "Bridgestone", "Hankook",
        "Pirelli", "Mobil", "Valeo", "Bilstein", "Brembo", "Ferodo", "Monroe", "Motul", "Shell",
        "Denso", "Osram", "Febi", "Mann-Filter", "Varta"
    ],
    "Books & Media": [
        "Penguin", "HarperCollins", "Simon & Schuster", "Hachette", "Macmillan", "Helion", "PWN",
        "Znak", "Czarne", "Agora", "Rebis", "Empik", "Egmont", "Marvel", "DC", "Sony Music",
        "Universal Music"
    ],
    "Health": [
        "Apap", "Ibuprom", "Rutinoscorbin", "Doppelherz", "Swanson", "Solgar", "Naturell",
        "Olimp Labs", "Hasco-Lek", "Aflofarm", "Vicks", "Oral-B", "Colgate", "Sensodyne",
        "Accu-Chek", "Omron"
    ],
    "Pet Supplies": [
        "Royal Canin", "Purina", "Whiskas", "Pedigree", "Brit", "Josera", "Acana", "Orijen",
        "Animonda", "Trixie", "Catit", "Zolux", "Versele-Laga", "Vitakraft"
    ],
    "Baby & Kids": [
        "Pampers", "Huggies", "Dada", "Bebilon", "Nan", "Gerber", "HiPP", "Canpol", "Avent",
        "Chicco", "Kinderkraft", "Maxi-Cosi", "Cybex", "Britax Romer"
    ],
    "Office": [
        "HP", "Canon", "Epson", "Brother", "Logitech", "Microsoft", "Lenovo", "Dell", "Fellowes",
        "Leitz", "Parker", "Bic", "Pilot", "Stabilo", "Oxford", "Esselte"
    ],
    "Jewelry & Accessories": [
        "Apart", "W.Kruk", "Pandora", "Swarovski", "Tous", "Casio", "Fossil", "Guess",
        "Michael Kors", "Timex", "Seiko", "Ray-Ban", "Polaroid", "Vogue"
    ],
    "Furniture": [
        "IKEA", "Black Red White", "Agata", "Bodzio", "Forte", "Signal", "Halmar", "Kler", "VOX",
        "Meble Wojcik", "Tempur", "Hilding", "Selsey"
    ],
    "DIY Tools": [
        "Bosch", "Makita", "DeWalt", "Stanley", "Black+Decker", "Ryobi", "Einhell", "Metabo",
        "Milwaukee", "Yato", "Topex", "Fiskars", "Knipex", "Wera"
    ],
}

# Brand weights by category. Each tuple is a brand tier:
# ([brand names], tier weight). The tier weight is split equally between brands in the tier.
# This keeps the settings readable while avoiding unrealistic equal brand shares inside a category.
brand_weight_profiles = {
    "Electronics": [
        (["Samsung", "Apple", "Xiaomi", "Lenovo", "LG", "Sony"], 0.55),
        (["HP", "Dell", "Asus", "Acer", "Huawei", "Philips", "Logitech", "Canon", "Epson"], 0.30),
        (["Panasonic", "Toshiba", "Microsoft", "Nokia", "Garmin", "Polar", "JBL", "Bose", "GoPro",
          "Nintendo", "Brother", "Hisense", "TCL", "Miele", "Beko"], 0.15),
    ],
    "Clothing": [
        (["Nike", "Adidas", "Zara", "H&M", "Reserved", "Sinsay"], 0.52),
        (["Puma", "Levi's", "Tommy Hilfiger", "Calvin Klein", "New Balance", "Mango", "Cropp",
          "House", "Mohito", "Wojas"], 0.33),
        (["Under Armour", "Gap", "Ralph Lauren", "Patagonia", "The North Face", "Columbia", "Reebok",
          "Gucci", "Prada", "Versace", "Vistula"], 0.15),
    ],
    "Home & Garden": [
        (["IKEA", "Bosch", "Tefal", "Philips", "Electrolux", "Whirlpool"], 0.50),
        (["Black+Decker", "DeLonghi", "Dyson", "Rowenta", "Miele", "Gardena", "Braun", "Kenwood",
          "Karcher", "Makita", "Stanley"], 0.35),
        (["Gorenje", "Russell Hobbs", "Zanussi", "Fiskars", "Vileda", "Ambition", "Gerda", "Brabantia"], 0.15),
    ],
    "Sports": [
        (["Nike", "Adidas", "Puma", "Decathlon", "4F", "New Balance"], 0.55),
        (["Under Armour", "Asics", "Reebok", "Columbia", "The North Face", "Salomon", "Wilson", "Head",
          "Kross", "Giant", "Trek"], 0.32),
        (["Patagonia", "Mammut", "Arc'teryx", "Merrell", "Yonex", "Lululemon", "Fila", "Spokey",
          "Martes", "Rossignol"], 0.13),
    ],
    "Beauty": [
        (["L'Oreal", "Nivea", "Maybelline", "Garnier", "Bielenda", "Ziaja", "Eveline"], 0.55),
        (["Estee Lauder", "Lancome", "Dior", "Chanel", "MAC", "Revlon", "Yves Rocher", "Vichy",
          "La Roche-Posay", "CeraVe"], 0.33),
        (["Neutrogena", "Pantene", "Kylie", "AA", "The Ordinary", "Inglot"], 0.12),
    ],
    "Toys": [
        (["Lego", "Hasbro", "Mattel", "Playmobil", "Barbie", "Hot Wheels"], 0.60),
        (["Fisher-Price", "Ravensburger", "Trefl", "Cobi", "Clementoni", "Spin Master"], 0.30),
        (["Schleich", "Brio"], 0.10),
    ],
    "Automotive": [
        (["Bosch", "Michelin", "Goodyear", "Continental", "Castrol", "Mobil"], 0.55),
        (["Bridgestone", "Hankook", "Pirelli", "Valeo", "Brembo", "Motul", "Shell", "Denso", "Osram",
          "Varta"], 0.35),
        (["Bilstein", "Ferodo", "Monroe", "Febi", "Mann-Filter"], 0.10),
    ],
    "Books & Media": [
        (["Empik", "Helion", "PWN", "Znak", "Egmont"], 0.50),
        (["Penguin", "HarperCollins", "Simon & Schuster", "Hachette", "Macmillan", "Agora", "Rebis"], 0.35),
        (["Czarne", "Marvel", "DC", "Sony Music", "Universal Music"], 0.15),
    ],
    "Health": [
        (["Apap", "Ibuprom", "Rutinoscorbin", "Oral-B", "Colgate", "Sensodyne"], 0.55),
        (["Doppelherz", "Swanson", "Solgar", "Naturell", "Olimp Labs", "Hasco-Lek", "Aflofarm"], 0.32),
        (["Vicks", "Accu-Chek", "Omron"], 0.13),
    ],
    "Pet Supplies": [
        (["Royal Canin", "Purina", "Whiskas", "Pedigree", "Brit", "Josera"], 0.60),
        (["Acana", "Orijen", "Animonda", "Trixie", "Vitakraft"], 0.30),
        (["Catit", "Zolux", "Versele-Laga"], 0.10),
    ],
    "Baby & Kids": [
        (["Pampers", "Huggies", "Dada", "Bebilon", "Nan", "Gerber", "HiPP"], 0.62),
        (["Canpol", "Avent", "Chicco", "Kinderkraft"], 0.26),
        (["Maxi-Cosi", "Cybex", "Britax Romer"], 0.12),
    ],
    "Office": [
        (["HP", "Canon", "Epson", "Brother", "Logitech", "Microsoft"], 0.55),
        (["Lenovo", "Dell", "Fellowes", "Leitz", "Parker", "Bic"], 0.32),
        (["Pilot", "Stabilo", "Oxford", "Esselte"], 0.13),
    ],
    "Jewelry & Accessories": [
        (["Apart", "W.Kruk", "Pandora", "Swarovski", "Casio"], 0.55),
        (["Tous", "Fossil", "Guess", "Michael Kors", "Ray-Ban", "Polaroid"], 0.33),
        (["Timex", "Seiko", "Vogue"], 0.12),
    ],
    "Furniture": [
        (["IKEA", "Black Red White", "Agata", "Bodzio", "Forte"], 0.55),
        (["Signal", "Halmar", "VOX", "Meble Wojcik", "Selsey"], 0.32),
        (["Kler", "Tempur", "Hilding"], 0.13),
    ],
    "DIY Tools": [
        (["Bosch", "Makita", "DeWalt", "Stanley", "Black+Decker"], 0.55),
        (["Ryobi", "Einhell", "Metabo", "Milwaukee", "Yato", "Fiskars"], 0.33),
        (["Topex", "Knipex", "Wera"], 0.12),
    ],
}

def build_brand_weights(brand_profiles):
    """
    Build brand probability dictionaries from readable tier definitions.

    Parameters:
    brand_profiles (dict): Category names mapped to lists of brand tier tuples.

    Returns:
    dict: Category names mapped to brand weights.
    """
    brand_weights = {}

    for category, tiers in brand_profiles.items():
        category_weights = {}
        for brands, tier_weight in tiers:
            brand_weight = tier_weight / len(brands)
            for brand in brands:
                category_weights[brand] = brand_weight
        brand_weights[category] = category_weights

    return brand_weights

category_brand_weights = build_brand_weights(brand_weight_profiles)

# Category selection weights. Values are normalized automatically. The weights are shaped to approximate
# Polish e-commerce category demand, with fashion, electronics, health/beauty, and home categories leading.
categories_with_probabilities = {
    "Electronics":             0.16,
    "Clothing":                0.23,
    "Home & Garden":           0.085,
    "Sports":                  0.06,
    "Beauty":                  0.095,
    "Toys":                    0.035,
    "Automotive":              0.035,
    "Books & Media":           0.04,
    "Health":                  0.055,
    "Pet Supplies":            0.025,
    "Baby & Kids":             0.035,
    "Office":                  0.015,
    "Jewelry & Accessories":   0.015,
    "Furniture":               0.035,
    "DIY Tools":               0.025,
}

# Target gross revenue mix by category. These values are used when selecting products for orders.
# The generator adjusts them by average generated category price, so expensive categories do not dominate revenue only
# because their unit prices are higher.
category_revenue_target_weights = {
    "Electronics":             0.215,
    "Clothing":                0.325,
    "Home & Garden":           0.050,
    "Sports":                  0.065,
    "Beauty":                  0.064,
    "Toys":                    0.028,
    "Automotive":              0.023,
    "Books & Media":           0.027,
    "Health":                  0.041,
    "Pet Supplies":            0.016,
    "Baby & Kids":             0.028,
    "Office":                  0.009,
    "Jewelry & Accessories":   0.011,
    "Furniture":               0.034,
    "DIY Tools":               0.017,
}

# Category seasonality multipliers by month. Month 1 means January, month 12 means December.
# A value above 1.0 increases the chance that products from the category are sold in that month.
category_monthly_seasonality = {
    "Electronics":             {11: 1.35, 12: 1.25},
    "Clothing":                {3: 1.10, 4: 1.15, 9: 1.20, 10: 1.10, 11: 1.15},
    "Home & Garden":           {3: 1.25, 4: 1.35, 5: 1.25, 6: 1.15},
    "Sports":                  {4: 1.15, 5: 1.25, 6: 1.30, 7: 1.20, 8: 1.10},
    "Beauty":                  {2: 1.15, 5: 1.10, 11: 1.20, 12: 1.35},
    "Toys":                    {11: 1.45, 12: 1.80},
    "Automotive":              {3: 1.15, 4: 1.20, 10: 1.15, 11: 1.20},
    "Books & Media":           {8: 1.20, 9: 1.25, 12: 1.20},
    "Health":                  {1: 1.15, 2: 1.20, 10: 1.15, 11: 1.20, 12: 1.10},
    "Pet Supplies":            {},
    "Baby & Kids":             {8: 1.10, 9: 1.15, 11: 1.10},
    "Office":                  {8: 1.20, 9: 1.35},
    "Jewelry & Accessories":   {2: 1.25, 5: 1.15, 12: 1.45},
    "Furniture":               {3: 1.10, 4: 1.20, 9: 1.15, 10: 1.15},
    "DIY Tools":               {3: 1.20, 4: 1.25, 5: 1.20, 6: 1.10},
}

# Product popularity randomness. Higher sigma means a stronger long-tail effect:
# a small number of products sell much more often than the rest.
product_popularity_sigma = 1.10

# Brand popularity has a separate effect on sales product selection. This multiplier is applied to the product's
# catalog brand weight. Values above 1.0 make popular brands sell more often than their catalog share alone.
brand_sales_weight_power = 0.70

# Category-specific quantity profiles for one order line. Values are normalized automatically.
category_quantity_profiles = {
    "Electronics":             {1: 0.88, 2: 0.09, 3: 0.02, 4: 0.008, 5: 0.002},
    "Clothing":                {1: 0.68, 2: 0.20, 3: 0.08, 4: 0.03, 5: 0.01},
    "Home & Garden":           {1: 0.75, 2: 0.16, 3: 0.06, 4: 0.02, 5: 0.01},
    "Sports":                  {1: 0.78, 2: 0.15, 3: 0.05, 4: 0.015, 5: 0.005},
    "Beauty":                  {1: 0.58, 2: 0.24, 3: 0.11, 4: 0.05, 5: 0.02},
    "Toys":                    {1: 0.70, 2: 0.19, 3: 0.07, 4: 0.025, 5: 0.015},
    "Automotive":              {1: 0.76, 2: 0.16, 3: 0.05, 4: 0.02, 5: 0.01},
    "Books & Media":           {1: 0.64, 2: 0.22, 3: 0.09, 4: 0.035, 5: 0.015},
    "Health":                  {1: 0.55, 2: 0.24, 3: 0.12, 4: 0.06, 5: 0.03},
    "Pet Supplies":            {1: 0.50, 2: 0.25, 3: 0.14, 4: 0.07, 5: 0.04},
    "Baby & Kids":             {1: 0.56, 2: 0.24, 3: 0.12, 4: 0.055, 5: 0.025},
    "Office":                  {1: 0.52, 2: 0.25, 3: 0.13, 4: 0.07, 5: 0.03},
    "Jewelry & Accessories":   {1: 0.86, 2: 0.10, 3: 0.03, 4: 0.008, 5: 0.002},
    "Furniture":               {1: 0.90, 2: 0.08, 3: 0.015, 4: 0.004, 5: 0.001},
    "DIY Tools":               {1: 0.74, 2: 0.17, 3: 0.06, 4: 0.02, 5: 0.01},
}

# Discount model. A discount is applied per order line, after product and category selection.
discount_probability_by_category = {
    "Electronics":             0.10,
    "Clothing":                0.32,
    "Home & Garden":           0.18,
    "Sports":                  0.24,
    "Beauty":                  0.20,
    "Toys":                    0.18,
    "Automotive":              0.12,
    "Books & Media":           0.15,
    "Health":                  0.10,
    "Pet Supplies":            0.12,
    "Baby & Kids":             0.16,
    "Office":                  0.12,
    "Jewelry & Accessories":   0.18,
    "Furniture":               0.15,
    "DIY Tools":               0.14,
}

discount_rate_ranges = {
    "low":       (0.03, 0.10),
    "regular":   (0.10, 0.25),
    "deep":      (0.25, 0.45),
}

discount_type_probabilities = {
    "low":       0.45,
    "regular":   0.45,
    "deep":      0.10,
}

# Discount intensity multipliers by month. November and December include stronger promotional periods.
discount_monthly_multiplier = {
    1: 1.10,
    2: 1.00,
    3: 0.95,
    4: 0.95,
    5: 1.00,
    6: 1.05,
    7: 1.10,
    8: 1.00,
    9: 0.95,
    10: 1.00,
    11: 1.65,
    12: 1.35,
}

# Net purchase price ranges by category, in PLN.
price_ranges = {
    "Electronics":             (50, 7000),
    "Clothing":                (15, 450),
    "Home & Garden":           (15, 3500),
    "Sports":                  (20, 2800),
    "Beauty":                  (6, 300),
    "Toys":                    (12, 450),
    "Automotive":              (20, 2500),
    "Books & Media":           (8, 180),
    "Health":                  (5, 420),
    "Pet Supplies":            (8, 420),
    "Baby & Kids":             (8, 1400),
    "Office":                  (3, 1200),
    "Jewelry & Accessories":   (15, 2500),
    "Furniture":               (60, 5000),
    "DIY Tools":               (15, 3000),
}

# Gross margin ranges by category. These values represent gross margin on net sales price, not markup.
margin_ranges = {
    "Electronics":             (0.12, 0.28),
    "Clothing":                (0.42, 0.62),
    "Home & Garden":           (0.30, 0.48),
    "Sports":                  (0.32, 0.48),
    "Beauty":                  (0.52, 0.72),
    "Toys":                    (0.35, 0.55),
    "Automotive":              (0.25, 0.40),
    "Books & Media":           (0.18, 0.35),
    "Health":                  (0.48, 0.68),
    "Pet Supplies":            (0.35, 0.55),
    "Baby & Kids":             (0.35, 0.55),
    "Office":                  (0.20, 0.38),
    "Jewelry & Accessories":   (0.50, 0.70),
    "Furniture":               (0.32, 0.50),
    "DIY Tools":               (0.25, 0.42),
}

vat_rate = 0.23

colors_with_probabilities = {
    "black":        0.22,
    "white":        0.16,
    "gray":         0.12,
    "silver":       0.07,
    "blue":         0.08,
    "navy":         0.05,
    "red":          0.05,
    "green":        0.05,
    "beige":        0.04,
    "brown":        0.04,
    "pink":         0.04,
    "yellow":       0.025,
    "orange":       0.015,
    "purple":       0.015,
    "gold":         0.015,
    "multicolor":   0.025,
}

payment_method_with_probabilities = {
    "BLIK":              0.42,
    "Card":              0.22,
    "Fast transfer":     0.18,
    "Deferred payment":  0.07,
    "COD":               0.04,
    "Wallet":            0.04,
    "Bank transfer":     0.03,
}

payment_provider_with_probabilities = {
    "PayU":          0.30,
    "Przelewy24":    0.28,
    "Tpay":          0.14,
    "Autopay":       0.10,
    "Stripe":        0.08,
    "PayPal":        0.04,
    "PayPo":         0.04,
    "Other":         0.02,
}

delivery_method_with_probabilities = {
    "InPost parcel locker":   0.54,
    "InPost courier":         0.08,
    "DPD":                    0.10,
    "DHL":                    0.08,
    "Allegro One":            0.06,
    "Orlen Paczka":           0.04,
    "Poczta Polska":          0.025,
    "UPS":                    0.025,
    "FedEx":                  0.01,
    "Store pickup":           0.04,
}
