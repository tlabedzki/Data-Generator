# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Suppliers, purchase orders and stock (Data Generator 1.8.0):

# The shop buys every product from one supplier. A buyer orders "by eye" on the supplier's order days: the average
# daily sales of the last buyer_history_days, times the promised lead time, the days until the next order day and
# buyer_cover_days, minus the stock on hand and on order, rounded up to the pack and at least the minimum order.
# Stock goes down on the order day of every order line. Returned units go to an outlet and do not come back to the
# shop's stock; cancelled and failed orders keep their units too (a simplification, see docs/settings.md).
#
# stockouts decides what happens when the shelf is empty:
# - False (default): an express delivery brings the missing units the same day, so every order line is served and
#   the 16 tables of 1.7.1 stay exactly as they were (seed 42, byte for byte).
# - True: the customer cannot buy. The order line is removed from order_data (and from every table built on it), and
#   lost_demand_data keeps it as the truth: what was asked for, when and by whom. Sales are then lower than demand.
stockouts = False

# Number of suppliers per category (categories not listed get one). A supplier serves the brands given to it.
suppliers_per_category = {
    "Electronics": 3, "Clothing": 3, "Home & Garden": 2, "Sports": 2, "Beauty": 2, "Health": 2, "Furniture": 2,
}

# Where suppliers come from: share of suppliers and the range of their mean lead time in days (order to receipt).
supplier_origins = {
    "PL": {"share": 0.60, "lead_time_days": (2, 6)},
    "DE": {"share": 0.25, "lead_time_days": (4, 9)},
    "CN": {"share": 0.15, "lead_time_days": (25, 40)},
}

# Spread of the actual lead time around its mean (coefficient of variation), drawn once per supplier.
lead_time_cv = (0.10, 0.35)

# How many weekdays (Monday to Friday) a supplier takes orders on, with probabilities.
order_weekday_count = {1: 0.40, 2: 0.45, 3: 0.15}

# Units in one pack by category (categories not listed use default_pack_sizes), with probabilities.
default_pack_sizes = {1: 0.55, 2: 0.20, 4: 0.15, 6: 0.10}
pack_sizes = {
    "Clothing": {1: 0.30, 5: 0.40, 10: 0.30},
    "Books & Media": {1: 0.50, 5: 0.50},
    "Beauty": {1: 0.30, 6: 0.40, 12: 0.30},
    "Health": {1: 0.30, 6: 0.40, 12: 0.30},
    "Pet Supplies": {1: 0.40, 4: 0.30, 8: 0.30},
    "Furniture": {1: 1.00},
    "Electronics": {1: 0.80, 2: 0.20},
}

# Minimum order of a product, in packs, with probabilities.
min_order_packs = {1: 0.50, 2: 0.30, 4: 0.20}

# The buyer: days of sales history, extra cover in days, spread of the order quantity (log-normal sigma) and the
# chance per order day that an empty product with no recent sales is noticed and ordered again.
buyer_history_days = 28
buyer_cover_days = 10
buyer_quantity_sigma = 0.20
empty_shelf_notice_rate = 0.5

# Stock of products already on sale on the first day, and the first delivery of a product launched later: the buyer's
# guess of its sales over this many days (drawn per product), at least one pack.
opening_cover_days = (20, 45)
launch_cover_days = (15, 40)
