# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Products bought together (market basket):

# In an order with more than one line, every further line becomes a complement of the first line's product type
# with the given probability (complement type: probability). Probabilities of one type should add up to at most 1.
complements = {
    "Laptop":          {"Wireless Mouse": 0.35, "Headphones": 0.12, "Backpack": 0.10},
    "Smartphone":      {"Headphones": 0.30},
    "Monitor":         {"Wireless Mouse": 0.25, "Desk Lamp": 0.10},
    "Printer":         {"Notebook": 0.25, "Pen": 0.15},
    "Office Desk":     {"Office Chair": 0.40, "Desk Lamp": 0.20},
    "Jeans":           {"T-Shirt": 0.35, "Sneakers": 0.15},
    "Dress":           {"Handbag": 0.25, "Sunglasses": 0.10},
    "Jacket":          {"Jeans": 0.20, "T-Shirt": 0.15},
    "Running Shoes":   {"Fitness Mat": 0.20, "T-Shirt": 0.15},
    "Mountain Bike":   {"Backpack": 0.30},
    "Tennis Racket":   {"Backpack": 0.20, "Running Shoes": 0.10},
    "Face Cream":      {"Mascara": 0.15, "Lipstick": 0.15},
    "Mascara":         {"Lipstick": 0.30},
    "Dog Food":        {"Pet Toy": 0.30},
    "Cat Food":        {"Pet Litter": 0.45, "Pet Toy": 0.15},
    "Diapers":         {"Baby Formula": 0.35, "Baby Bottle": 0.15},
    "Baby Stroller":   {"Car Seat": 0.35},
    "Cordless Drill":  {"Screwdriver Set": 0.30, "Tool Box": 0.20},
    "Angle Grinder":   {"Tool Box": 0.25},
    "Engine Oil":      {"Wiper Blades": 0.20, "Brake Pads": 0.10},
    "Coffee Machine":  {"Kitchen Pan": 0.10},
    "Board Game":      {"Building Blocks": 0.15},
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Customer preferences:

# Every customer has a favourite category (drawn with the age and gender affinities), saved in
# customer_data.preferred_category. This share of the customer's order lines comes from it.
category_loyalty = 0.30

# Price tier of the customer (saved in customer_data.price_tier). Budget customers prefer cheaper products of a
# category, premium customers more expensive ones: the chance to keep a drawn product is multiplied by
# min(1, (price / category median price) ** exponent).
price_tiers = {
    "budget":   {"share": 0.35, "exponent": -1.2},
    "standard": {"share": 0.45, "exponent": 0.0},
    "premium":  {"share": 0.20, "exponent": 1.0},
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Replenishment (repeat purchases of consumables):

# Some customers buy one consumable product again and again. Their repeat orders follow the product's cycle
# (days, with ±replenishment_jitter random spread) and start with that product.
# Keys: product type: (cycle days, share of loyal and regular customers who replenish it).
replenishment_products = {
    "Dog Food":           (30, 0.040),
    "Cat Food":           (28, 0.040),
    "Pet Litter":         (21, 0.020),
    "Diapers":            (30, 0.030),
    "Baby Formula":       (21, 0.020),
    "Vitamin Supplement": (60, 0.030),
    "Shampoo":            (45, 0.020),
    "Toothpaste":         (60, 0.015),
    "Face Cream":         (60, 0.015),
}
replenishment_jitter = 0.15
replenishment_segments = ["loyal", "regular"]
