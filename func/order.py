import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

# Funkcja generująca daty z uwzględnieniem sezonowości
def generate_dates_with_seasonality_and_growth(
    num_rows,
    start_year,
    end_year,
    base_monthly_seasonality,
    base_weekday_seasonality,
    annual_growth_rate
):
    dates = []

    # Przygotowanie wag sezonowości
    years = list(range(start_year, end_year + 1))
    year_weights = [1 + annual_growth_rate * (year - start_year) for year in years]
    year_weights = np.array(year_weights) / sum(year_weights)

    # Losowanie roku na podstawie wag
    year_cumulative = np.cumsum(year_weights)

    for _ in range(num_rows):
        # Wybór roku
        rand_year = np.random.rand()
        year = years[np.searchsorted(year_cumulative, rand_year)]

        # Losowa zmiana sezonowości dla tego roku
        monthly_seasonality = np.array(base_monthly_seasonality) * (1 + np.random.normal(0, 0.1, len(base_monthly_seasonality)))
        monthly_seasonality = monthly_seasonality / monthly_seasonality.sum()
        monthly_cumulative = np.cumsum(monthly_seasonality)

        weekday_seasonality = np.array(base_weekday_seasonality) * (1 + np.random.normal(0, 0.1, len(base_weekday_seasonality)))
        weekday_seasonality = weekday_seasonality / weekday_seasonality.sum()

        # Wybór miesiąca na podstawie sezonowości miesięcznej
        rand_month = np.random.rand()
        month = np.searchsorted(monthly_cumulative, rand_month) + 1

        # Wybór dnia w danym miesiącu
        start_date = datetime(year, month, 1)
        end_date = start_date + timedelta(days=(pd.Timestamp(start_date).days_in_month - 1))
        random_date = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days + 1))

        # Dopasowanie dnia tygodnia na podstawie sezonowości
        if np.random.rand() < 0.7:  # 70% szans na dopasowanie do sezonowości dni tygodnia
            chosen_weekday = np.random.choice(range(7), p=weekday_seasonality)
            while random_date.weekday() != chosen_weekday:
                random_date += timedelta(days=1 if random_date.weekday() < chosen_weekday else -1)

        dates.append(random_date)

    return dates

def generate_dates_with_seasonality_and_randomness(
    num_rows,
    start_year,
    end_year,
    base_monthly_seasonality,
    base_weekday_seasonality,
    annual_growth_rate
):
    dates = []

    # Przygotowanie wag dla lat
    years = list(range(start_year, end_year + 1))
    year_weights = [1 + annual_growth_rate * (year - start_year) + np.random.normal(0, 0.02) for year in years]
    year_weights = np.array(year_weights) / sum(year_weights)
    year_cumulative = np.cumsum(year_weights)

    for _ in range(num_rows):
        # Losowy wybór roku
        rand_year = np.random.rand()
        year = years[np.searchsorted(year_cumulative, rand_year)]

        # Losowe fluktuacje sezonowości miesięcznej
        monthly_seasonality = np.array(base_monthly_seasonality) * (1 + np.random.normal(0, 0.2, len(base_monthly_seasonality)))
        monthly_seasonality = monthly_seasonality / monthly_seasonality.sum()
        monthly_cumulative = np.cumsum(monthly_seasonality)

        # Losowe fluktuacje sezonowości dni tygodnia
        weekday_seasonality = np.array(base_weekday_seasonality) * (1 + np.random.normal(0, 0.2, len(base_weekday_seasonality)))
        weekday_seasonality = weekday_seasonality / weekday_seasonality.sum()

        # Wybór miesiąca na podstawie sezonowości miesięcznej
        rand_month = np.random.rand()
        month = np.searchsorted(monthly_cumulative, rand_month) + 1

        # Wybór dnia w miesiącu
        start_date = datetime(year, month, 1)
        end_date = start_date + timedelta(days=(pd.Timestamp(start_date).days_in_month - 1))
        random_date = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days + 1))

        # Dopasowanie dnia tygodnia z losowym przesunięciem
        if np.random.rand() < 0.3:
            chosen_weekday = np.random.choice(range(7), p=weekday_seasonality)
            while random_date.weekday() != chosen_weekday:
                shift = np.random.randint(1, 3) * (1 if random_date.weekday() < chosen_weekday else -1)
                random_date += timedelta(days=shift)

        # Wprowadzenie dodatkowego przesunięcia +/- kilka dni
        if np.random.rand() < 0.7:
            random_date += timedelta(days=np.random.randint(-30, 30))

        dates.append(random_date)

    return dates

# Funkcja generująca dane e-commerce
def generate_ecommerce_data_with_seasonality(num_rows, params):
    # Parametry
    start_year = 2023
    end_year = 2024
    base_monthly_seasonality = [0.06, 0.07, 0.08, 0.09, 0.08, 0.06, 0.07, 0.08, 0.08, 0.10, 0.21, 0.15]
    base_weekday_seasonality = [0.20, 0.15, 0.1, 0.1, 0.1, 0.15, 0.20]
    annual_growth_rate = 0.20

    data = {
        "order_date": generate_dates_with_seasonality_and_randomness(num_rows, start_year, end_year, base_monthly_seasonality,
                                                                 base_weekday_seasonality, annual_growth_rate),
        "product_id": [np.random.randint(params.get('product_id_min'), params.get('product_id_max')) for _ in range(num_rows)],
        "quantity": [np.random.choice([1, 2, 3, 4, 5], p=[0.75, 0.15, 0.05, 0.03, 0.02]) for _ in range(num_rows)],
        "customer_id": [np.random.randint(params.get('customer_id_min'), params.get('customer_id_max')) for _ in range(num_rows)],
    }
    data['order_date'] = pd.to_datetime(data['order_date'])

    data = pd.DataFrame(data)

    data = data[(data['order_date'] >= f'{start_year}-01-01') & (data['order_date'] <= f'{end_year}-12-31')]\
        .reset_index(drop=True)

    return data

def generate_order_data(num_rows, params):
    # Generate source:
    order_data = generate_ecommerce_data_with_seasonality(num_rows, params)

    return order_data