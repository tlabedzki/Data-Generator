# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Special days (promotions and holidays):

# Each special day multiplies the demand of its days (the month total stays as set in base_monthly_seasonality, so a
# strong Black Friday takes orders from the rest of November), the chance of a discount and the probability of
# selected categories. "dates" is a named movable day or a ("MM-DD", "MM-DD") range. Named days: "black_friday"
# (the Friday after the fourth Thursday of November), "black_week" (the four days before it), "cyber_monday",
# "easter_sunday", "easter_monday". The first matching entry wins when days overlap.
special_days = {
    "black_friday":     {"dates": "black_friday", "demand": 4.0, "discount": 2.2, "categories": {"Electronics": 1.4}},
    "cyber_monday":     {"dates": "cyber_monday", "demand": 2.6, "discount": 1.8, "categories": {"Electronics": 1.5}},
    "black_week":       {"dates": "black_week", "demand": 1.5, "discount": 1.5, "categories": {}},
    "singles_day":      {"dates": ("11-11", "11-11"), "demand": 2.0, "discount": 1.6, "categories": {}},
    "valentines_week":  {"dates": ("02-07", "02-13"), "demand": 1.15, "discount": 1.0,
                         "categories": {"Jewelry & Accessories": 2.2, "Beauty": 1.5}},
    "mothers_day_week": {"dates": ("05-19", "05-25"), "demand": 1.15, "discount": 1.0,
                         "categories": {"Beauty": 1.8, "Jewelry & Accessories": 1.8}},
    "childrens_day_week": {"dates": ("05-26", "05-31"), "demand": 1.15, "discount": 1.0, "categories": {"Toys": 2.5}},
    "mikolajki":        {"dates": ("12-01", "12-05"), "demand": 1.25, "discount": 1.2, "categories": {"Toys": 1.6}},
    "christmas_eve":    {"dates": ("12-24", "12-24"), "demand": 0.45, "discount": 1.0, "categories": {}},
    "christmas":        {"dates": ("12-25", "12-26"), "demand": 0.25, "discount": 1.0, "categories": {}},
    "new_years_eve":    {"dates": ("12-31", "12-31"), "demand": 0.60, "discount": 1.0, "categories": {}},
    "new_year":         {"dates": ("01-01", "01-01"), "demand": 0.40, "discount": 1.0, "categories": {}},
    "easter_sunday":    {"dates": "easter_sunday", "demand": 0.30, "discount": 1.0, "categories": {}},
    "easter_monday":    {"dates": "easter_monday", "demand": 0.50, "discount": 1.0, "categories": {}},
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Product life cycle and prices:

# Share of products launched during the period (the rest existed before) and share discontinued before its end.
# A discontinued product stays on sale for at least min_product_life_days.
launched_during_period_share = 0.30
discontinued_share = 0.15
min_product_life_days = 120

# List price changes per product and year, the share of increases and their size (fractions of the price).
# The last price of every product equals sales_price_gross in product_data; price_history keeps the earlier ones.
price_changes_per_year = 1.2
price_increase_share = 0.75
price_increase_range = (0.02, 0.12)
price_decrease_range = (0.05, 0.20)

# Price elasticity of demand by category. A product's chance to be bought falls with its list price relative to its
# lowest price in the period: (price / lowest price) ** -elasticity. A discount raises the expected quantity of an
# order line: (1 - discount) ** -elasticity.
default_price_elasticity = 1.2
category_price_elasticity = {
    "Electronics": 1.6,
    "Clothing": 1.8,
    "Health": 0.6,
    "Pet Supplies": 0.7,
    "Baby & Kids": 0.8,
    "Books & Media": 1.0,
    "Furniture": 1.4,
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Order time of day:

# Relative weights of the 24 hours (0 = midnight to 1 a.m.). Evenings are the busiest.
hour_weights = [0.6, 0.35, 0.2, 0.12, 0.1, 0.15, 0.4, 0.9, 1.6, 2.2, 2.8, 3.1,
                3.3, 3.2, 3.1, 3.2, 3.5, 3.9, 4.6, 5.4, 5.8, 5.4, 4.0, 1.9]

# Fraudulent orders are placed mostly at night.
fraud_hour_weights = [5.0, 6.0, 6.0, 5.0, 4.0, 2.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5,
                      0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.8, 1.0, 1.5, 2.5, 4.0]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Shipping (shipment_data):

# Product types too big for parcel lockers. Orders with one of them go by courier.
bulky_product_types = ["Sofa", "Wardrobe", "Mattress", "Office Desk", "Dining Chair", "Office Chair", "Mountain Bike",
                       "Baby Stroller", "Car Tire"]
locker_delivery_methods = ["InPost parcel locker", "Orlen Paczka", "Allegro One", "Poczta Polska"]
bulky_delivery_methods = {"DPD": 0.40, "DHL": 0.30, "UPS": 0.15, "FedEx": 0.05, "InPost courier": 0.10}

# Delivery cost paid by the customer (PLN gross), transit days (min, max) and promised days per method.
delivery_methods = {
    "InPost parcel locker": {"cost": 13.99, "transit_days": (1, 2), "promised_days": 2},
    "InPost courier":       {"cost": 17.99, "transit_days": (1, 3), "promised_days": 2},
    "DPD":                  {"cost": 18.99, "transit_days": (1, 3), "promised_days": 3},
    "DHL":                  {"cost": 19.99, "transit_days": (1, 3), "promised_days": 3},
    "Allegro One":          {"cost": 11.99, "transit_days": (1, 2), "promised_days": 2},
    "Orlen Paczka":         {"cost": 10.99, "transit_days": (1, 3), "promised_days": 3},
    "Poczta Polska":        {"cost": 12.99, "transit_days": (2, 5), "promised_days": 4},
    "UPS":                  {"cost": 21.99, "transit_days": (1, 3), "promised_days": 3},
    "FedEx":                {"cost": 24.99, "transit_days": (1, 2), "promised_days": 2},
    "Store pickup":         {"cost": 0.0, "transit_days": (1, 2), "promised_days": 2},
}
free_shipping_threshold = 199.0
bulky_shipping_surcharge = 49.0

# Warehouse: orders placed before the cut-off hour on a working day leave the same day; weekends and holidays wait.
# The promised delivery date counts promised_days working days from that dispatch day. A carrier delay (1 to
# peak_extra_days days) hits carrier_delay_share of shipments, and peak_delay_share in peak months, when the
# warehouse also needs an extra day for the same share of orders.
dispatch_cutoff_hour = 14
carrier_delay_share = 0.05
peak_months = [11, 12]
peak_delay_share = 0.25
peak_extra_days = 2

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Returns (return_data):

# Chance that an order line is returned, by category. Deal hunters and discounted lines return a bit more often.
default_return_rate = 0.05
category_return_rate = {
    "Clothing": 0.24,
    "Jewelry & Accessories": 0.12,
    "Sports": 0.09,
    "Furniture": 0.08,
    "Electronics": 0.06,
    "Beauty": 0.03,
    "Health": 0.02,
    "Pet Supplies": 0.02,
    "Books & Media": 0.02,
}
segment_return_multiplier = {"deal_hunter": 1.4, "loyal": 0.8}
discounted_return_multiplier = 1.2

# Days from delivery to the return (most within the 14-day withdrawal period) and return reasons.
return_delay_days = (1, 30)
return_within_14_days_share = 0.85
return_reasons = {
    "Clothing": {"wrong_size": 0.55, "not_as_described": 0.15, "changed_mind": 0.20, "damaged": 0.05,
                 "defective": 0.05},
    "default": {"changed_mind": 0.35, "not_as_described": 0.20, "damaged": 0.15, "defective": 0.25, "wrong_item": 0.05},
}

# A defective batch: once per period one popular product is returned much more often for a month (labelled in
# anomaly_data as return_spike).
return_spikes = 1
return_spike_rate = 0.55
return_spike_days = 30

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Order status (order_data):

# Every order ends as delivered, returned (every line sent back and refunded), cancelled or payment_failed. Cancelled
# and failed orders never ship, so they have no shipment, return or review, and they bring no revenue: revenue_gross
# keeps the value of the order as placed, so filter on order_status for the money the shop made. Fraud orders always
# go through (their stolen cards pay).
# Share of orders whose payment fails, by payment method: deferred payments are refused after a credit check, cards
# get declined, cash on delivery cannot fail at checkout.
default_payment_failure_rate = 0.02
payment_failure_rate = {
    "BLIK": 0.012,
    "Card": 0.035,
    "Fast transfer": 0.02,
    "Deferred payment": 0.10,
    "COD": 0.0,
    "Wallet": 0.015,
    "Bank transfer": 0.03,
}

# Share of paid orders cancelled before dispatch, more often with cash on delivery (nothing paid yet) and in the peak
# months, when products run out. Cancelled orders keep the time of the cancellation (cancelled_at, always before the
# planned dispatch) and a reason; out_of_stock weighs peak_out_of_stock_multiplier times more in peak_months.
cancellation_rate = 0.025
cod_cancellation_multiplier = 3.0
peak_cancellation_multiplier = 1.5
cancel_reasons = {"customer_request": 0.50, "out_of_stock": 0.20, "duplicate_order": 0.15, "address_problem": 0.15}
peak_out_of_stock_multiplier = 3.0

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Reviews (review_data):

# Customers rate delivered order lines from 1 to 5 stars, more often after a bad experience. The experience of a line
# is "defect" when it came back as defective or damaged or belongs to the defective batch of the return spike (the
# customers who kept it rate it low too), "late" when the shipment came after the promised date, else "on_time".
# These settings are the answer: how much a late delivery and a defect lower the rating and the chance to review.
defect_return_reasons = ["defective", "damaged"]
review_rate = {"on_time": 0.22, "late": 0.35, "defect": 0.55}
review_score_weights = {
    "on_time": {5: 0.60, 4: 0.23, 3: 0.08, 2: 0.04, 1: 0.05},
    "late":    {5: 0.30, 4: 0.25, 3: 0.17, 2: 0.12, 1: 0.16},
    "defect":  {5: 0.04, 4: 0.06, 3: 0.12, 2: 0.23, 1: 0.55},
}

# Days from delivery to the review (geometric, at least one day, with this mean) and the share of reviews with a
# comment, which is one of the ready sentences below. Low ratings after a late delivery or a defect name the cause.
review_delay_mean_days = 5
review_comment_share = {"on_time": 0.35, "late": 0.60, "defect": 0.80}
review_comments = {
    "positive": ["Great product, I recommend it.", "Exactly as described.", "Good value for the price.",
                 "Very happy with it."],
    "neutral": ["It is fine, nothing special.", "Okay for the price.",
                "Does the job, but the quality could be better."],
    "negative": ["Not worth the money.", "Disappointed with the quality.", "Not what I expected."],
    "late": ["The parcel came late.", "Delivery took much longer than promised.",
             "Good product, but the courier was late."],
    "defect": ["Arrived damaged.", "Stopped working after a few days.", "Faulty item, very disappointed."],
}
