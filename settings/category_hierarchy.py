import settings.product_catalog as pc

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Category hierarchy settings:

# Product hierarchy:
# category -> subcategory -> product_type -> brand -> product_series -> product_model
#
# category and product_type are generated from settings.product_catalog.
# subcategory is assigned here to keep analytical category hierarchy separate from concrete product types.

subcategory_by_product_type = {
    "Electronics": {
        "Smartphone": "Mobile Phones",
        "Laptop": "Computers",
        "Wireless Mouse": "Computer Accessories",
        "Headphones": "Audio",
        "Printer": "Printing",
    },
    "Clothing": {
        "Sneakers": "Lifestyle Footwear",
        "T-Shirt": "Casualwear",
        "Jeans": "Denim",
        "Jacket": "Outerwear",
        "Dress": "Women's Clothing",
    },
    "Home & Garden": {
        "Vacuum Cleaner": "Home Appliances",
        "Coffee Machine": "Kitchen Appliances",
        "Garden Tool": "Garden Equipment",
        "Kitchen Pan": "Cookware",
        "Desk Lamp": "Lighting",
    },
    "Sports": {
        "Running Shoes": "Sports Footwear",
        "Fitness Mat": "Fitness Equipment",
        "Mountain Bike": "Cycling",
        "Tennis Racket": "Racket Sports",
        "Backpack": "Outdoor Accessories",
    },
    "Beauty": {
        "Face Cream": "Face Care",
        "Mascara": "Makeup",
        "Shampoo": "Hair Care",
        "Perfume": "Fragrance",
        "Lipstick": "Makeup",
    },
    "Toys": {
        "Building Blocks": "Construction Toys",
        "Board Game": "Family Games",
        "Doll": "Dolls",
        "Toy Car": "Vehicles and Tracks",
    },
    "Automotive": {
        "Engine Oil": "Fluids and Lubricants",
        "Car Tire": "Tires",
        "Brake Pads": "Brake System",
        "Car Battery": "Electrical System",
        "Wiper Blades": "Visibility",
    },
    "Books & Media": {
        "Book": "Literature and Non-Fiction",
        "Comic Book": "Comics and Manga",
        "Music Album": "Music",
        "Board Book": "Children's Books",
    },
    "Health": {
        "Vitamin Supplement": "Supplements",
        "Pain Relief": "OTC Medicines",
        "Toothpaste": "Oral Care",
        "Blood Pressure Monitor": "Medical Devices",
        "Cold Remedy": "Cold and Flu",
    },
    "Pet Supplies": {
        "Dog Food": "Dog Nutrition",
        "Cat Food": "Cat Nutrition",
        "Pet Toy": "Pet Accessories",
        "Pet Litter": "Cat Hygiene",
    },
    "Baby & Kids": {
        "Diapers": "Baby Hygiene",
        "Baby Formula": "Baby Food",
        "Baby Bottle": "Feeding",
        "Car Seat": "Child Safety",
        "Baby Stroller": "Strollers",
    },
    "Office": {
        "Notebook": "Paper Products",
        "Pen": "Writing Instruments",
        "Office Chair": "Office Furniture",
        "Monitor": "Office Electronics",
        "Paper Shredder": "Office Equipment",
    },
    "Jewelry & Accessories": {
        "Watch": "Watches",
        "Sunglasses": "Eyewear",
        "Bracelet": "Jewelry",
        "Handbag": "Bags",
    },
    "Furniture": {
        "Office Desk": "Office Furniture",
        "Sofa": "Living Room Furniture",
        "Dining Chair": "Dining Room Furniture",
        "Mattress": "Bedroom",
        "Wardrobe": "Storage",
    },
    "DIY Tools": {
        "Cordless Drill": "Power Tools",
        "Screwdriver Set": "Hand Tools",
        "Angle Grinder": "Power Tools",
        "Tool Box": "Workshop Storage",
        "Saw": "Cutting Tools",
    },
}


def validate_category_hierarchy(product_catalog, subcategory_map):
    """
    Validate category hierarchy coverage and prevent duplicate category levels.

    Parameters:
    product_catalog (dict): Product catalog definition.
    subcategory_map (dict): Category to product type to subcategory mapping.
    """
    for category, product_types in product_catalog.items():
        if category not in subcategory_map:
            raise ValueError(f"Missing subcategory mapping for category: {category}")

        missing_product_types = set(product_types) - set(subcategory_map[category])
        if missing_product_types:
            raise ValueError(f"Missing subcategory mapping for {category}: {sorted(missing_product_types)}")

        extra_product_types = set(subcategory_map[category]) - set(product_types)
        if extra_product_types:
            raise ValueError(f"Unknown product type in subcategory mapping for {category}: {sorted(extra_product_types)}")

        for product_type, subcategory in subcategory_map[category].items():
            if not subcategory:
                raise ValueError(f"Empty subcategory for {category}/{product_type}")
            if subcategory == category:
                raise ValueError(f"Subcategory duplicates category for {category}/{product_type}: {subcategory}")
            if subcategory == product_type:
                raise ValueError(f"Subcategory duplicates product type for {category}/{product_type}: {subcategory}")


validate_category_hierarchy(pc.product_catalog, subcategory_by_product_type)
