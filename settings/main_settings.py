# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Saving format settings:

# Choose the format of the file in which the data will be saved. The available options are 'csv' and 'parquet'.
saving_format = "parquet"

# Choose which files should be generated and saved.
# Available options: "customer_data", "product_data", "order_data", "sales_data".
# Examples:
# - ["customer_data"] generates only the customer file.
# - ["customer_data", "product_data", "order_data"] generates three separate files without joining them.
# - ["customer_data", "product_data", "order_data", "sales_data"] generates all source files and the joined file.
generated_files = ["customer_data", "product_data", "order_data", "sales_data"]

# Set a number for reproducible generated data, or None for fully random data on every run.
random_state = 42

# Choose generated data language. Available options: "en" and "pl".
# This affects display values saved in output files, for example categories, product types, colors,
# payment methods, delivery methods, and generated product names.
data_language = "pl"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Sales settings:

# Below you can set the years for which you would like to generate data. The setting works in a "from-to" option,
# meaning that if you set the start_year to 2010 and the end_year to 2020, the generated data will include orders
# from the beginning of 2010 to the end of 2020.
start_year = 2023
end_year = 2024

# Below you can set the seasonality for months and days of the week. Additionally, there is an option to set the
# average year-over-year growth. If sales are expected to decrease, you can enter a negative value here.
base_monthly_seasonality = [0.06, 0.07, 0.08, 0.08, 0.08, 0.06, 0.07, 0.08, 0.08, 0.10, 0.21, 0.16]
base_weekday_seasonality = [0.23, 0.17, 0.05, 0.05, 0.07, 0.15, 0.22]
annual_growth_rate = 0.20

# Below you can set the number of rows for each type of data, such as customers, products, and order lines.
# If you want to have more orders from returning customers in the data, the number of customers relative
# to the number of order lines should be smaller. It is worth testing different scenarios in this case.
customer_data_rows = 40000
product_data_rows = 50000
order_data_rows = 80000

# Below, you can control the number of lines in an order using a probability indicator for each quantity from 1 to 5.
order_line_number = {
    1: 0.69,
    2: 0.21,
    3: 0.05,
    4: 0.03,
    5: 0.01,
}

# Below, you can control the quantity sold in a single order line.
quantity_per_order_line = {
    1: 0.74,
    2: 0.16,
    3: 0.06,
    4: 0.025,
    5: 0.015,
}
