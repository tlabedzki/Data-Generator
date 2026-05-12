import pandas as pd


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def build_sales_data(order_data, product_data, customer_data):
    """
    Build the final sales dataset by joining orders with product and customer data.

    Parameters:
    order_data (pd.DataFrame): Generated order lines.
    product_data (pd.DataFrame): Generated product data.
    customer_data (pd.DataFrame): Generated customer data.

    Returns:
    pd.DataFrame: Enriched sales dataset sorted by order date and order ID.
    """
    sales_data = pd.merge(order_data, product_data, on='product_id', how='left')
    sales_data = pd.merge(sales_data, customer_data, on='customer_id', how='left')
    sales_data['sales_price_gross_after_discount'] = sales_data['sales_price_gross'] * (1 - sales_data['discount_rate'])
    sales_data['sales_price_net_after_discount'] = sales_data['sales_price_net'] * (1 - sales_data['discount_rate'])
    sales_data['revenue_gross'] = sales_data['quantity'] * sales_data['sales_price_gross_after_discount']

    return sales_data.sort_values(['order_date', 'order_id'], ascending=[True, True])
