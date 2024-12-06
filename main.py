import pandas as pd

from pathlib import Path

import customer as c
import product as p
import order as o


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Paths:

SOURCE_DIR = Path("source")
EXPORT_DIR = Path("export")
POSTAL_CODE_DATA = SOURCE_DIR / "postal_code.csv"
SALES_DATA = EXPORT_DIR / "sales_data.csv"

# Path to files:
code_df = pd.read_csv(POSTAL_CODE_DATA, sep=";")
sales_data_dir = EXPORT_DIR / "sales_data.csv"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Run:

# Generate customer source:
customer_data = c.generate_customer_data(35000)

# Get customer min and max id:
customer_id_min, customer_id_max = customer_data['customer_id'].min(), customer_data['customer_id'].max()

# Generate product source:
product_data = p.generate_product_data(50000)

# Get customer min and max id:
product_id_min, product_id_max = product_data['product_id'].min(), product_data['product_id'].max()

# Generate order source:
params = {
    'customer_id_min': customer_id_min,
    'customer_id_max': customer_id_max,
    'product_id_min': product_id_min,
    'product_id_max': product_id_max
}
order_data = o.generate_order_data(100000, params)

# Merge order_data with customer_data and product_data:
merged_data = pd.merge(order_data, product_data, on='product_id', how='left')
merged_data = pd.merge(merged_data, customer_data, on='customer_id', how='left')

# Add calculated columns:
merged_data['revenue_gross'] = merged_data['quantity'] * merged_data['sales_price_gross']

# Sort data:
sorted_data = merged_data.sort_values('order_date', ascending=True)

# Export data:
sorted_data.to_csv(sales_data_dir, sep=';', index=False)

print('Done.')