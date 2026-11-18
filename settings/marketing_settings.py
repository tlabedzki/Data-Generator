# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Channels:

# Share of orders by traffic channel without campaigns, for first orders (new customers) and repeat orders.
first_order_channels = {
    "paid_search": 0.28, "organic_search": 0.22, "social": 0.18, "affiliate": 0.12, "direct": 0.12, "email": 0.08,
}
repeat_order_channels = {
    "direct": 0.30, "email": 0.22, "organic_search": 0.20, "paid_search": 0.15, "social": 0.07, "affiliate": 0.06,
}

# A new customer's first order usually comes through the channel that brought them (customer_data.acquisition_channel).
acquisition_channels = {
    "paid_search": 0.30, "organic_search": 0.22, "social": 0.22, "affiliate": 0.14, "direct": 0.08, "email": 0.04,
}
first_order_from_acquisition_share = 0.80

# Session conversion rate by channel (orders / sessions) and multipliers by device. Device shares of sessions.
channel_conversion_rates = {
    "email": 0.14, "direct": 0.12, "affiliate": 0.11, "paid_search": 0.10, "organic_search": 0.09, "social": 0.04,
}
device_shares = {"mobile": 0.62, "desktop": 0.33, "tablet": 0.05}
device_conversion_multipliers = {"desktop": 1.35, "mobile": 0.85, "tablet": 1.0}

# Funnel of sessions without an order: share that adds to cart, and of those the share reaching the checkout.
non_converting_add_to_cart_share = 0.22
non_converting_checkout_share = 0.35
# Share of sessions without an order that belong to a known customer (logged in); the rest are anonymous.
known_visitor_share = 0.45

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Campaigns (campaign_data):

# Marketing budget as gross PLN per expected order, split by channel. Campaign budgets follow the expected orders of
# their days with some random variation.
marketing_budget_per_order = 70.0
channel_budget_shares = {"paid_search": 0.45, "social": 0.30, "affiliate": 0.15, "email": 0.10}

# Campaign plans by channel:
# - every: "month" (one campaign per month), "week" (one per week) or a number of bursts per month,
# - days: (min, max) length of a burst,
# - lift: (min, max) extra demand while the campaign runs, as a share of an ordinary day,
# - decay: share of the effect that carries over to the next day after the campaign ends (adstock),
# - voucher_share: share of the campaign's orders that use its voucher code (0 = no voucher).
campaign_plans = {
    "paid_search": {"every": "month", "days": (28, 31), "lift": (0.05, 0.15), "decay": 0.3, "voucher_share": 0.0},
    "social":      {"every": 1.5, "days": (5, 12), "lift": (0.20, 0.50), "decay": 0.6, "voucher_share": 0.25},
    "email":       {"every": "week", "days": (1, 1), "lift": (0.25, 0.45), "decay": 0.5, "voucher_share": 0.40},
    "affiliate":   {"every": 0.5, "days": (14, 30), "lift": (0.08, 0.20), "decay": 0.2, "voucher_share": 0.60},
}
