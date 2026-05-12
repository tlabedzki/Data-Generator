import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

import func.data as d
import settings.main_settings as s
import settings.market_settings as ms

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Variables:

# List of weekdays:
weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Payment methods definition with probabilities:
payment_method_with_probabilities = ms.payment_method_with_probabilities
payment_method, payment_method_probabilities = d.get_param_list_and_normalized_probabilities(payment_method_with_probabilities)

# Payment providers definition with probabilities:
payment_provider_with_probabilities = ms.payment_provider_with_probabilities
payment_provider, payment_provider_probabilities = d.get_param_list_and_normalized_probabilities(payment_provider_with_probabilities)

# Delivery methods definition with probabilities:
delivery_method_with_probabilities = ms.delivery_method_with_probabilities
delivery_method, delivery_method_probabilities = d.get_param_list_and_normalized_probabilities(delivery_method_with_probabilities)

# Order line numbers with probabilities:
order_line_numbers = s.order_line_number
order_line_numbers, order_line_numbers_probabilities = d.get_param_list_and_normalized_probabilities(order_line_numbers)

# Quantity per order line with probabilities:
quantity_per_order_line = s.quantity_per_order_line
quantity_per_order_line, quantity_per_order_line_probabilities = d.get_param_list_and_normalized_probabilities(quantity_per_order_line)

# Discount type probabilities:
discount_types, discount_type_probabilities = d.get_param_list_and_normalized_probabilities(ms.discount_type_probabilities)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_dates_with_seasonality_and_randomness(start_year, end_year, base_monthly_seasonality, base_weekday_seasonality, annual_growth_rate):
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

    date_was_drawn = False
    # Create dates in loop:
    while date_was_drawn == False:
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
                pass

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
        if random_date < datetime(start_year, 1, 1) or random_date > datetime(end_year, 12, 31):
            continue
        else:
            dates.append(random_date)
            date_was_drawn = True

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
    created_rows = 0
    product_categories, base_product_category_probabilities = get_product_category_selection(params)

    while created_rows < num_rows:
        # Randomly determine the number of lines for this order
        order_line_number = np.random.choice(order_line_numbers, p=order_line_numbers_probabilities)

        # Generate shared attributes for the order
        order_date = generate_dates_with_seasonality_and_randomness(start_year, end_year, base_monthly_seasonality, base_weekday_seasonality, annual_growth_rate)[0]
        customer_id = np.random.randint(params.get('customer_id_min'), params.get('customer_id_max'))
        payment_method_choice = np.random.choice(payment_method, p=payment_method_probabilities)
        payment_provider_choice = np.random.choice(payment_provider, p=payment_provider_probabilities)
        delivery_method_choice = np.random.choice(delivery_method, p=delivery_method_probabilities)

        product_category_probabilities = get_seasonal_category_probabilities(
            product_categories,
            base_product_category_probabilities,
            order_date,
        )

        # Generate lines for the current order:
        for _ in range(order_line_number):
            product_id, category = choose_product_id(params, order_date, product_categories, product_category_probabilities)
            order_groups.append({
                "order_date": order_date,
                "product_id": product_id,
                "quantity": choose_quantity(category),
                "customer_id": customer_id,
                "payment_method": payment_method_choice,
                "payment_provider": payment_provider_choice,
                "delivery_method": delivery_method_choice,
                "discount_rate": choose_discount_rate(category, order_date),
            })

        # Increment order_id for the next order
        created_rows = len(order_groups)

    # Convert to DataFrame:
    data = pd.DataFrame(order_groups)

    # Convert order_date to datetime:
    data['order_date'] = pd.to_datetime(data['order_date'])

    # Sort data by order_date to ensure chronological order:
    data.sort_values(by="order_date", inplace=True)

    # Create unique identifier for each order (group by shared attributes)
    data['order_id'] = (
        data.groupby(['order_date', 'customer_id', 'payment_method', 'payment_provider', 'delivery_method'])
        .ngroup() + 100001
    )

    # Sort data after adding order_id:
    data.sort_values('order_id', inplace=True)

    return data

def get_product_category_selection(params):
    """
    Return category selection values when category-aware product selection is available.

    Parameters:
    params (dict): Order generation parameters.

    Returns:
    tuple: Category names and probabilities, or (None, None) when unavailable.
    """
    product_category_weights = params.get('product_category_weights')

    if not product_category_weights:
        return None, None

    return d.get_param_list_and_normalized_probabilities(product_category_weights)

def get_seasonal_category_probabilities(product_categories, base_probabilities, order_date):
    """
    Apply category monthly seasonality to base category probabilities.

    Parameters:
    product_categories (list): Category names.
    base_probabilities (list): Base category probabilities.
    order_date (datetime): Order date.

    Returns:
    np.array: Seasonally adjusted category probabilities.
    """
    if product_categories is None:
        return None

    month = order_date.month
    seasonality = np.array([
        ms.category_monthly_seasonality.get(category, {}).get(month, 1.0)
        for category in product_categories
    ])
    probabilities = np.array(base_probabilities) * seasonality

    return probabilities / probabilities.sum()

def choose_product_id(params, order_date=None, product_categories=None, product_category_probabilities=None):
    """
    Choose a product ID for an order line.

    Parameters:
    params (dict): Order generation parameters.
    product_categories (list, optional): Categories available for product selection.
    product_category_probabilities (list, optional): Category selection probabilities.

    Returns:
    tuple: Selected product ID and category.
    """
    product_ids_by_category = params.get('product_ids_by_category')
    product_weights_by_category = params.get('product_weights_by_category')

    if product_ids_by_category and product_categories is not None:
        category = np.random.choice(product_categories, p=product_category_probabilities)
        product_ids = product_ids_by_category[category]
        product_weights = product_weights_by_category[category]
        product_probabilities = product_weights / product_weights.sum()
        return np.random.choice(product_ids, p=product_probabilities), category

    return np.random.randint(params.get('product_id_min'), params.get('product_id_max')), None

def choose_quantity(category):
    """
    Choose order line quantity, using a category-specific profile when available.

    Parameters:
    category (str): Product category.

    Returns:
    int: Quantity.
    """
    if category in ms.category_quantity_profiles:
        quantity_values, quantity_probabilities = d.get_param_list_and_normalized_probabilities(ms.category_quantity_profiles[category])
        return np.random.choice(quantity_values, p=quantity_probabilities)

    return np.random.choice(quantity_per_order_line, p=quantity_per_order_line_probabilities)

def choose_discount_rate(category, order_date):
    """
    Choose a discount rate for an order line.

    Parameters:
    category (str): Product category.
    order_date (datetime): Order date.

    Returns:
    float: Discount rate.
    """
    base_probability = ms.discount_probability_by_category.get(category, 0)
    monthly_multiplier = ms.discount_monthly_multiplier.get(order_date.month, 1.0)
    discount_probability = min(base_probability * monthly_multiplier, 0.95)

    if np.random.rand() >= discount_probability:
        return 0.0

    discount_type = np.random.choice(discount_types, p=discount_type_probabilities)
    min_discount, max_discount = ms.discount_rate_ranges[discount_type]

    return round(np.random.uniform(min_discount, max_discount), 4)

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
