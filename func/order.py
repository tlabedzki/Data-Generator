import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import settings.main_settings as s

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_dates_with_seasonality_and_randomness(num_rows, start_year, end_year, base_monthly_seasonality, base_weekday_seasonality, annual_growth_rate):
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

        # Weekday seasonality with random fluctuations:
        weekday_seasonality = np.array(base_weekday_seasonality) * (1 + np.random.normal(0, 0.2, len(base_weekday_seasonality)))
        weekday_seasonality = weekday_seasonality / weekday_seasonality.sum()

        # Month selection based on monthly seasonality:
        rand_month = np.random.rand()
        month = np.searchsorted(monthly_cumulative, rand_month) + 1

        # Day draw:
        start_date = datetime(year, month, 1)
        end_date = start_date + timedelta(days=(pd.Timestamp(start_date).days_in_month - 1))
        random_date = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days + 1))

        # Weekday adjustment with random shift:
        if np.random.rand() < 0.3:
            chosen_weekday = np.random.choice(range(7), p=weekday_seasonality)
            while random_date.weekday() != chosen_weekday:
                shift = np.random.randint(1, 3) * (1 if random_date.weekday() < chosen_weekday else -1)
                random_date += timedelta(days=shift)

        # Append drawn date to list:
        if np.random.rand() < 0.7:
            random_date += timedelta(days=np.random.randint(-30, 30))

        # Append drawn date to list:
        dates.append(random_date)

    return dates

# Funkcja generująca dane e-commerce
def generate_ecommerce_data_with_seasonality(num_rows, params):
    # Parameters definition:
    start_year = s.start_year
    end_year = s.end_year
    base_monthly_seasonality = s.base_monthly_seasonality
    base_weekday_seasonality = s.base_weekday_seasonality
    annual_growth_rate = s.annual_growth_rate

    # Generate data:
    data = {
        "order_date": generate_dates_with_seasonality_and_randomness(
            num_rows, start_year, end_year, base_monthly_seasonality, base_weekday_seasonality, annual_growth_rate
        ),
        "product_id": [np.random.randint(params.get('product_id_min'), params.get('product_id_max')) for _ in range(num_rows)],
        "quantity": [np.random.choice([1, 2, 3, 4, 5], p=[0.75, 0.15, 0.05, 0.03, 0.02]) for _ in range(num_rows)],
        "customer_id": [np.random.randint(params.get('customer_id_min'), params.get('customer_id_max')) for _ in range(num_rows)],
    }
    data['order_date'] = pd.to_datetime(data['order_date'])

    # Create DataFrame based on prepared dictionary:
    data = pd.DataFrame(data)

    # Filter data to show only selected years
    # Sometimes there are days from previous and next years, because of randomness in generation:
    data = data[(data['order_date'] >= f'{start_year}-01-01') & (data['order_date'] <= f'{end_year}-12-31')]\
        .reset_index(drop=True)

    return data

def generate_order_data(num_rows, params):
    # Generate source:
    order_data = generate_ecommerce_data_with_seasonality(num_rows, params)

    return order_data