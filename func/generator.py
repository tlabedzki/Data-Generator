import pandas as pd
from pathlib import Path
from func import customer as c, order as o, product as p, log as l, format as f
import settings.main_settings as s

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Paths:

# Path to directories:
SOURCE_DIR = Path("source")
EXPORT_DIR = Path("export")

# Path to files:
POSTAL_CODE_DATA = SOURCE_DIR / "pl_postal_code.csv"
SALES_DATA = EXPORT_DIR / "sales_data.csv"
sales_data_dir = EXPORT_DIR / "sales_data.csv"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_full_sales_data():
    """
    Generate full sales data by merging customer, product, and order data,
    then export the merged data to a CSV file.

    This function performs the following steps:
    1. Logs the start of data preparation.
    2. Generates customer data.
    3. Retrieves the minimum and maximum customer IDs.
    4. Generates product data.
    5. Retrieves the minimum and maximum product IDs.
    6. Generates order data using customer and product ID ranges.
    7. Merges order data with product and customer data.
    8. Adds a calculated column for gross revenue.
    9. Sorts the merged data by order date.
    10. Logs the completion of data preparation.
    11. Exports the sorted data to a CSV file.
    12. Logs the success of the file save operation.
    """
    l.log_info("Let's prepare some data!")

    # Generate customer source:
    customer_data = c.generate_customer_data(s.customer_data_rows)

    # Get customer min and max id:
    customer_id_min, customer_id_max = customer_data['customer_id'].min(), customer_data['customer_id'].max()

    # Generate product source:
    product_data = p.generate_product_data(s.product_data_rows)

    # Get product min and max id:
    product_id_min, product_id_max = product_data['product_id'].min(), product_data['product_id'].max()

    # Generate order source:
    params = {
        'customer_id_min': customer_id_min,
        'customer_id_max': customer_id_max,
        'product_id_min': product_id_min,
        'product_id_max': product_id_max
    }
    del customer_id_min, customer_id_max, product_id_min, product_id_max
    order_data = o.generate_order_data(s.order_data_rows, params)
    del params

    # Merge order_data with customer_data and product_data:
    merged_data = pd.merge(order_data, product_data, on='product_id', how='left')
    merged_data = pd.merge(merged_data, customer_data, on='customer_id', how='left')

    # Add calculated columns:
    merged_data['revenue_gross'] = merged_data['quantity'] * merged_data['sales_price_gross']

    # Sort data:
    sorted_data = merged_data.sort_values(['order_date', 'order_id'], ascending=[True, True])
    l.log_info('Data has been prepared.')

    # Get characteristic of created data:
    d_order_number = f.format_number(sorted_data['order_id'].nunique())
    d_order_line_qty = f.format_number(len(sorted_data))
    d_unique_products_sold = f.format_number(sorted_data['product_id'].nunique())
    d_unique_customers = f.format_number(sorted_data['customer_id'].nunique())
    d_revenue_gross_pln = f.format_number(sorted_data['revenue_gross'].sum() / 1000000)

    # Print some characteristic of created data to what exactly we have created:
    field_width = 25
    l.log_info(' -> Characteristic of created data:')
    l.log_info(f'{"Number of orders:":<{field_width}} {d_order_number}')
    l.log_info(f'{"Number of order lines:":<{field_width}} {d_order_line_qty}')
    l.log_info(f'{"Unique products sold:":<{field_width}} {d_unique_products_sold}')
    l.log_info(f'{"Unique customers:":<{field_width}} {d_unique_customers}')
    l.log_info(f'{"Total revenue gross PLN:":<{field_width}} {d_revenue_gross_pln} M')
    del d_order_number, d_order_line_qty, d_unique_products_sold, d_unique_customers, d_revenue_gross_pln

    # Export data:
    sorted_data.to_csv(sales_data_dir, sep=';', index=False)
    l.log_success('File has been saved as CSV file.')

def get_pl_postal_code_data():
    """
    Read and return Polish postal code data from a CSV file.

    Returns:
    pd.DataFrame: A DataFrame containing the Polish postal code data.
    """
    pl_postal_code_data = pd.read_csv(POSTAL_CODE_DATA, sep=";")

    return pl_postal_code_data