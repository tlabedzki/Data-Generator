import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

import func.data as d
import func.log as l
import settings.main_settings as s

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Variables:

# List of weekdays:
weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Payment methods definition with probabilities:
payment_method_with_probabilities = s.payment_method_with_probabilities
payment_method, payment_method_probabilities = d.get_param_list_and_normalized_probabilities(payment_method_with_probabilities)

# Delivery methods definition with probabilities:
delivery_method_with_probabilities = s.delivery_method_with_probabilities
delivery_method, delivery_method_probabilities = d.get_param_list_and_normalized_probabilities(delivery_method_with_probabilities)

# Order line numbers with probabilities:
order_line_numbers = s.order_line_number
order_line_numbers, order_line_numbers_probabilities = d.get_param_list_and_normalized_probabilities(order_line_numbers)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_dates_with_seasonality_and_randomness(num_rows, start_year, end_year, base_monthly_seasonality, base_weekday_seasonality, annual_growth_rate):
    """
    Generate a list of dates with seasonality and randomness.

    Parameters:
    num_rows (int): The number of dates to generate.
    start_year (int): The starting year for date generation.
    end_year (int): The ending year for date generation.
    base_monthly_seasonality (list): A list of base monthly seasonality factors.
    base_weekday_seasonality (list): A list of base weekday seasonality factors.
    annual_growth_rate (float): The annual growth rate to apply to the year weights.

    Returns:
    list: A list of generated dates with seasonality and randomness.
    """
    # Prepare variable:
    dates = []

    # Prepare seasonal weights for years:
    years = list(range(start_year, end_year + 1))
    year_weights = [1 + annual_growth_rate * (year - start_year) + np.random.normal(0, 0.02) for year in years]
    year_weights = np.array(year_weights) / sum(year_weights)
    year_cumulative = np.cumsum(year_weights)

    # Create dates in loop:
    for _ in range(num_rows):
        # Year selection:
        rand_year = np.random.rand()
        year = years[np.searchsorted(year_cumulative, rand_year)]

        # Monthly seasonality with random fluctuations:
        monthly_seasonality = np.array(base_monthly_seasonality) * (1 + np.random.normal(0, 0.2, len(base_monthly_seasonality)))
        monthly_seasonality = monthly_seasonality / monthly_seasonality.sum()
        monthly_cumulative = np.cumsum(monthly_seasonality)

        # Weekday seasonality with random fluctuations.
        # The following while loop was introduced because, at times, an issue with negative values occurred.
        while True:
            # Generate weekday seasonality with random fluctuations and normalize it:
            weekday_seasonality = np.array(base_weekday_seasonality) * (1 + np.random.normal(0, 0.2, len(base_weekday_seasonality)))
            weekday_seasonality = weekday_seasonality / weekday_seasonality.sum()

            # Check if all values are non-negative and exit loop if all values are valid:
            if (weekday_seasonality >= 0).all():
                break
            else:
                l.log_error("Negative values detected in weekday_seasonality. Regenerating...")

        # Month selection based on monthly seasonality:
        rand_month = np.random.rand()
        month = np.searchsorted(monthly_cumulative, rand_month) + 1

        # Day draw:
        start_date = datetime(year, month, 1)
        end_date = start_date + timedelta(days=(pd.Timestamp(start_date).days_in_month - 1))
        random_date = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days + 1))
        random_date_weekday = weekdays[random_date.weekday()]

        # Weekday adjustment with random shift:
        if np.random.rand() < 0.90:
            chosen_weekday = np.random.choice(range(7), p=weekday_seasonality)
            while random_date.weekday() != chosen_weekday:
                shift = np.random.randint(1, 3) * (1 if random_date.weekday() < chosen_weekday else -1)
                random_date += timedelta(days=shift)

        # Append drawn date to list:
        if np.random.rand() < 0.95:
            # Get the original weekday of random_date
            original_weekday = random_date.weekday()

            # Calculate random shift in days (between -30 and 30)
            shift_days = np.random.randint(-30, 30)

            # Apply the shift to random_date
            new_date = random_date + timedelta(days=shift_days)

            # Check if the new date's weekday is the same as the original
            while new_date.weekday() != original_weekday:
                # If not, recalculate the shift to maintain the same weekday
                shift_days = np.random.randint(-1, 1)
                new_date = random_date + timedelta(days=shift_days)

        # Append drawn date to list:
        dates.append(random_date)

    return dates

def generate_ecommerce_data_with_seasonality(num_rows, params):
    """
    Generate e-commerce data with seasonality and group orders with shared attributes.

    Parameters:
    num_rows (int): The total number of lines (rows) of data to generate.
    params (dict): A dictionary containing the parameters for data generation, including:
        - 'product_id_min' (int): The minimum product ID.
        - 'product_id_max' (int): The maximum product ID.
        - 'customer_id_min' (int): The minimum customer ID.
        - 'customer_id_max' (int): The maximum customer ID.

    Returns:
    pd.DataFrame: A DataFrame containing the generated e-commerce data with seasonality.
    """
    # Parameters definition:
    start_year = s.start_year
    end_year = s.end_year
    base_monthly_seasonality = s.base_monthly_seasonality
    base_weekday_seasonality = s.base_weekday_seasonality
    annual_growth_rate = s.annual_growth_rate

    # Initialize list to store order data
    order_groups = []

    # Estimate number of orders (assuming average 3 lines per order)
    num_orders = int(num_rows / 3)

    # Initialize order_id
    order_id = 200001
    created_rows = 0

    while created_rows < num_rows:
        # Randomly determine the number of lines for this order
        order_line_number = np.random.choice(order_line_numbers, p=order_line_numbers_probabilities)

        # Generate shared attributes for the order
        order_date = generate_dates_with_seasonality_and_randomness(
            1, start_year, end_year, base_monthly_seasonality, base_weekday_seasonality, annual_growth_rate
        )[0]
        customer_id = np.random.randint(params.get('customer_id_min'), params.get('customer_id_max'))
        payment_method_choice = np.random.choice(payment_method, p=payment_method_probabilities)
        delivery_method_choice = np.random.choice(delivery_method, p=delivery_method_probabilities)

        # Generate lines for the current order
        for _ in range(order_line_number):
            order_groups.append({
                "order_id": order_id,  # Assign the current order_id
                "order_date": order_date,
                "product_id": np.random.randint(params.get('product_id_min'), params.get('product_id_max')),
                "quantity": np.random.choice([1, 2, 3, 4, 5], p=[0.75, 0.15, 0.05, 0.03, 0.02]),
                "customer_id": customer_id,
                "payment_method": payment_method_choice,
                "delivery_method": delivery_method_choice,
            })

        # Increment order_id for the next order
        order_id += 1
        created_rows = len(order_groups)

    # Convert to DataFrame
    data = pd.DataFrame(order_groups)

    # Convert order_date to datetime
    data['order_date'] = pd.to_datetime(data['order_date'])

    # Filter data to show only selected years
    # Sometimes there are days from previous and next years, because of randomness in generation:
    data = data[(data['order_date'] >= f'{start_year}-01-01') & (data['order_date'] <= f'{end_year}-12-31')].reset_index(drop=True)

    return data

def generate_order_data(num_rows, params):
    """
    Generate order data with seasonality.

    Parameters:
    num_rows (int): The number of rows of data to generate.
    params (dict): A dictionary containing the parameters for data generation, including:
        - 'product_id_min' (int): The minimum product ID.
        - 'product_id_max' (int): The maximum product ID.
        - 'customer_id_min' (int): The minimum customer ID.
        - 'customer_id_max' (int): The maximum customer ID.

    Returns:
    pd.DataFrame: A DataFrame containing the generated order data with seasonality.
    """
    # Generate source:
    order_data = generate_ecommerce_data_with_seasonality(num_rows, params)

    return order_data