import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Settings:

# Create faker instance for Polish language
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Functions:

# Funkcja generująca daty z większą ilością zamówień na Black Friday i przed Świętami
def generate_dates(num_rows):
    dates = []
    black_friday = datetime(2024, 11, 29)  # Data Black Friday
    holiday_start = datetime(2024, 12, 1)
    holiday_end = datetime(2024, 12, 24)

    for _ in range(num_rows):
        if np.random.rand() < 0.4:  # 40% zamówień w okresie peak sprzedaży
            if np.random.rand() < 0.5:  # Losowy wybór między Black Friday i grudniem
                dates.append(black_friday + timedelta(days=np.random.randint(-3, 4)))
            else:
                dates.append(holiday_start + timedelta(days=np.random.randint(0, (holiday_end - holiday_start).days)))
        else:  # Zamówienia w pozostałych dniach roku
            random_date = datetime(2024, 1, 1) + timedelta(days=np.random.randint(0, 365))
            dates.append(random_date)

    return dates

# Funkcja generująca dane
def generate_ecommerce_data(num_rows, params):
    data = {
        "order_date": generate_dates(num_rows),
        "product_id": [np.random.randint(params.get('product_id_min'), params.get('product_id_max')) for _ in range(num_rows)],
        "quantity": np.clip(np.random.geometric(0.7), 1, 10),
        "customer_id": [np.random.randint(params.get('customer_id_min'), params.get('customer_id_max')) for _ in range(num_rows)],
    }
    data['order_date'] = pd.to_datetime(data['order_date'])

    return pd.DataFrame(data)

def generate_order_data(num_rows, params):
    # Generate source:
    order_data = generate_ecommerce_data(num_rows, params)

    return order_data