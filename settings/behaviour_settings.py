# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Calendar:

# Random fluctuation of the monthly seasonality, drawn once per month and year (standard deviation of a
# multiplicative factor around 1.0). 0.03 means a month is usually within ±6% of its weight in settings.
monthly_noise_sd = 0.03

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Customer behaviour ("buy till you die"):

# Every customer belongs to one hidden segment, saved in customer_data.customer_segment as the answer to check a
# segmentation against. A segment sets:
# - share: share of customers,
# - orders_per_year: relative purchase frequency of an active customer (the generator rescales all frequencies so
#   the total number of order lines matches order_data_rows),
# - lifetime_days: mean time from the first order until the customer stops buying (churn),
# - discount_affinity: multiplier of the chance that an order line is discounted,
# - promo_month_power: how strongly the customer follows promotional months (discount_monthly_multiplier ** power).
customer_segments = {
    "loyal":       {"share": 0.10, "orders_per_year": 6.0, "lifetime_days": 1600, "discount_affinity": 0.8,
                    "promo_month_power": 0.0},
    "regular":     {"share": 0.22, "orders_per_year": 2.5, "lifetime_days": 700, "discount_affinity": 1.0,
                    "promo_month_power": 0.0},
    "deal_hunter": {"share": 0.15, "orders_per_year": 3.0, "lifetime_days": 500, "discount_affinity": 2.6,
                    "promo_month_power": 2.0},
    "occasional":  {"share": 0.28, "orders_per_year": 0.8, "lifetime_days": 400, "discount_affinity": 1.0,
                    "promo_month_power": 0.0},
    "one_time":    {"share": 0.25, "orders_per_year": 0.0, "lifetime_days": 0, "discount_affinity": 1.0,
                    "promo_month_power": 0.0},
}

# Spread of purchase frequency inside a segment (shape of a gamma distribution; lower = more "whales").
purchase_rate_shape = 1.5

# Customers who signed up before the generated period (their earlier orders are not in the data). They make the
# active customer base at the start realistic. Their signup dates spread over existing_customer_years.
existing_customer_share = 0.45
existing_customer_years = 4

# New customers sign up during the period, following the demand calendar. Some never place an order.
no_order_share = 0.08
first_order_same_day_share = 0.60
first_order_delay_mean_days = 10

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Demographics and habits:

# Category multipliers by age group (upper age of the group: multipliers). Categories not listed keep 1.0.
age_category_affinity = {
    29: {"Electronics": 1.45, "Clothing": 1.25, "Sports": 1.20, "Beauty": 1.10, "Books & Media": 1.10,
         "Home & Garden": 0.55, "Furniture": 0.70, "Health": 0.60, "Baby & Kids": 0.60, "DIY Tools": 0.60},
    44: {"Baby & Kids": 1.70, "Toys": 1.50, "Furniture": 1.25, "Home & Garden": 1.10, "Automotive": 1.10},
    65: {"Health": 1.70, "Home & Garden": 1.50, "DIY Tools": 1.40, "Books & Media": 1.15, "Furniture": 1.10,
         "Electronics": 0.70, "Clothing": 0.80, "Sports": 0.70, "Toys": 0.80, "Baby & Kids": 0.50},
}

gender_category_affinity = {
    "Female": {"Beauty": 1.60, "Jewelry & Accessories": 1.40, "Clothing": 1.10, "Baby & Kids": 1.15,
               "Automotive": 0.50, "DIY Tools": 0.60, "Electronics": 0.85},
    "Male":   {"Automotive": 1.50, "DIY Tools": 1.40, "Electronics": 1.15, "Sports": 1.10,
               "Beauty": 0.40, "Jewelry & Accessories": 0.60},
}

# Customers keep their habits: the share of orders paid and delivered the customer's usual way.
usual_payment_share = 0.70
usual_delivery_share = 0.60

# Expensive orders (gross value above the threshold, PLN) are paid differently: more deferred payments and cards.
high_value_order_threshold = 2000
high_value_payment_multipliers = {"Deferred payment": 3.0, "Card": 1.4, "COD": 0.3, "BLIK": 0.8}
