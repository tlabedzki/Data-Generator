# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Date settings:

start_year = 2023
end_year = 2024

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Seasonality settings:

base_monthly_seasonality = [0.06, 0.07, 0.08, 0.09, 0.08, 0.06, 0.07, 0.08, 0.08, 0.10, 0.21, 0.15]
base_weekday_seasonality = [0.20, 0.15, 0.1, 0.1, 0.1, 0.15, 0.20]
annual_growth_rate = 0.20

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Size of data settings:

customer_data_rows = 40000
product_data_rows = 60000
order_data_rows = 100000