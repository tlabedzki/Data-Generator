# Generator Settings Guide

This project has two main settings files:

- `settings/main_settings.py` controls the generation process.
- `settings/market_settings.py` controls market behavior, products, categories, brands, prices, margins, payments, deliveries, discounts, and sales mix.
- `settings/category_hierarchy.py` controls second-level categories.
- `settings/product_catalog.py` controls product types, product names, type-level prices, type-level margins, series, and models.
- `settings/localization.py` controls translations used in generated output files.

## Reproducibility

Use `random_state` in `settings/main_settings.py`.

```python
random_state = 42
```

Set a number to make generated data repeatable. Set `None` to generate different data on every run.

## Generated Data Language

Use `data_language` in `settings/main_settings.py`.

```python
data_language = "pl"
```

Available values:

- `"pl"` saves display values in Polish.
- `"en"` saves display values in English.

The translation dictionaries are in `settings/localization.py`. They currently cover:

- categories,
- subcategories,
- product types,
- product names,
- selected product series and product models,
- colors,
- payment methods,
- payment providers,
- delivery methods,
- gender.

Market logic still uses English technical keys internally. This keeps category weights, brand weights, margins,
discounts, seasonality, and order generation stable. Translation is applied only to the output datasets.

Product series and product models are translated only for generic descriptive values. Real brand, product line,
and model names such as `Galaxy`, `ThinkPad`, `Air Max`, or `Spider-Man` are intentionally preserved.

## Output Files

Use `generated_files` in `settings/main_settings.py`.

```python
generated_files = ["customer_data", "product_data", "order_data", "sales_data"]
```

Available values:

- `customer_data`
- `product_data`
- `order_data`
- `sales_data`

Examples:

```python
generated_files = ["customer_data"]
generated_files = ["customer_data", "product_data", "order_data"]
generated_files = ["sales_data"]
```

## Volumes

Use these settings in `settings/main_settings.py`:

```python
customer_data_rows = 40000
product_data_rows = 50000
order_data_rows = 80000
```

`order_data_rows` is the target number of order lines. The final number can be slightly higher because complete multi-line orders are generated.

## Category Catalog Mix

Use `categories_with_probabilities` in `settings/market_settings.py`.

This controls how often categories appear in the product catalog.

```python
categories_with_probabilities = {
    "Electronics": 0.16,
    "Clothing": 0.23,
}
```

Values are normalized automatically.

## Category Hierarchy

Use `subcategory_by_product_type` in `settings/category_hierarchy.py`.

The product hierarchy is:

```text
category -> subcategory -> product_type -> brand -> product_series -> product_model
```

Example:

```text
Electronics -> Mobile Phones -> Smartphone -> Samsung -> Galaxy -> S23
Clothing -> Lifestyle Footwear -> Sneakers -> Adidas -> Grand Court -> Cloudfoam
Books & Media -> Literature and Non-Fiction -> Book -> Znak -> Reportaz -> Paperback
```

`subcategory` should describe the assortment segment. `product_type` should describe the concrete product form.
Do not duplicate levels, for example `Books -> Book`. The validator blocks cases where `subcategory` duplicates
`category` or `product_type`.

```python
subcategory_by_product_type = {
    "Electronics": {
        "Smartphone": "Mobile Phones",
        "Laptop": "Computers",
    },
}
```

## Category Revenue Mix

Use `category_revenue_target_weights` in `settings/market_settings.py`.

This controls the intended category mix in sales revenue. The generator adjusts this by average category price so expensive categories do not dominate only because unit prices are high.

```python
category_revenue_target_weights = {
    "Electronics": 0.215,
    "Clothing": 0.325,
}
```

Values are normalized automatically.

## Category Seasonality

Use `category_monthly_seasonality` in `settings/market_settings.py`.

```python
category_monthly_seasonality = {
    "Toys": {11: 1.45, 12: 1.80},
    "Sports": {5: 1.25, 6: 1.30},
}
```

Month numbers use `1` for January and `12` for December. Values above `1.0` increase category sales probability in that month.

## Brands

Brands are configured in two layers:

1. `categories_brands` defines which brands exist in each category.
2. `brand_weight_profiles` defines brand share tiers inside each category.

Example:

```python
brand_weight_profiles = {
    "Electronics": [
        (["Samsung", "Apple", "Xiaomi"], 0.45),
        (["HP", "Dell", "Asus"], 0.30),
        (["Other Brand"], 0.25),
    ],
}
```

Each tier weight is split equally between brands in that tier.

## Brand Sales Effect

Use `brand_sales_weight_power` in `settings/market_settings.py`.

```python
brand_sales_weight_power = 0.70
```

Higher values make stronger brands sell more often. Lower values reduce the brand effect in sales.

## Product Popularity

Use `product_popularity_sigma` in `settings/market_settings.py`.

```python
product_popularity_sigma = 1.10
```

Higher values create a stronger long-tail effect where a small number of products sell much more often.

## Prices And Margins

Product prices and margins are controlled at product type level in `settings/product_catalog.py`.

Every product type has:

```python
"Smartphone": {
    "weight": 0.30,
    "price_range": (450, 4200),
    "margin_range": (0.10, 0.24),
    "brand_series_models": {
        "Samsung": {"Galaxy": ["S23", "S24"]},
    },
}
```

Product names always use this format:

```text
product_type brand product_series product_model
```

Example:

```text
Smartphone Samsung Galaxy S23
```

Every product must have a non-empty series and model.

Older category-level `price_ranges` and `margin_ranges` in `settings/market_settings.py` are retained as market-level reference ranges, but product generation uses `settings/product_catalog.py`.

`price_range` controls net purchase cost ranges in PLN.

```python
"price_range": (450, 4200)
```

`margin_range` controls gross margin on net sales price, not markup.

```python
"margin_range": (0.10, 0.24)
```

The generator calculates net sales price as:

```python
sales_price_net = net_purchase_price / (1 - sales_margin)
```

## Quantity Per Order Line

There are two layers:

- `quantity_per_order_line` in `settings/main_settings.py` is the fallback profile.
- `category_quantity_profiles` in `settings/market_settings.py` overrides quantity behavior by category.

Example:

```python
category_quantity_profiles = {
    "Pet Supplies": {1: 0.50, 2: 0.25, 3: 0.14, 4: 0.07, 5: 0.04},
}
```

## Discounts

Discounts are controlled in `settings/market_settings.py`.

`discount_probability_by_category` controls how often a category receives a discount.

```python
discount_probability_by_category = {
    "Clothing": 0.32,
}
```

`discount_rate_ranges` controls discount depth.

```python
discount_rate_ranges = {
    "low": (0.03, 0.10),
    "regular": (0.10, 0.25),
    "deep": (0.25, 0.45),
}
```

`discount_monthly_multiplier` changes discount intensity by month.

```python
discount_monthly_multiplier = {
    11: 1.65,
    12: 1.35,
}
```

## Payments And Delivery

Payment method and payment provider are separate.

```python
payment_method_with_probabilities = {
    "BLIK": 0.42,
    "Card": 0.22,
}

payment_provider_with_probabilities = {
    "PayU": 0.30,
    "Przelewy24": 0.28,
}
```

Delivery is controlled by:

```python
delivery_method_with_probabilities = {
    "InPost parcel locker": 0.54,
}
```

All probability dictionaries are normalized automatically.
