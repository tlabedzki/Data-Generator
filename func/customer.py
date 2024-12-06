import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
from pathlib import Path
import unicodedata

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -- - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Paths:

SOURCE_DATA = Path("source")
POSTAL_CODE_DATA = SOURCE_DATA / "postal_code.csv"

code_df = pd.read_csv(POSTAL_CODE_DATA, sep=";")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

# Funkcja generująca dane klientów
def generate_customers(num_customers, max_postal_code_id):
    genders = np.random.choice(["Male", "Female"], size=num_customers, p=[0.5, 0.5])

    male_first_names = [fake.first_name_male() for _ in range(num_customers)]
    female_first_names = [fake.first_name_female() for _ in range(num_customers)]

    # Tworzymy listę imion w zależności od płci
    first_names = [male_first_names[i] if genders[i] == "Male" else female_first_names[i] for i in range(num_customers)]
    last_names = [fake.last_name() for _ in range(num_customers)]
    last_names_without_polish_letters = [remove_polish_accents(last_name) for last_name in last_names]

    # List of popular e-mail domains:
    domains = np.random.choice(['gmail.com', 'yahoo.com', 'outlook.com'], size=num_customers, p=[0.5, 0.3, 0.2])

    # Generate e-mails based on first and last names with random domains:
    emails = [f"{first_names[i].lower()}.{last_names_without_polish_letters[i].lower()}@{domains[i]}" for i in range(num_customers)]

    # Creata data:
    data = {
        "customer_id": range(100001, 100001 + num_customers),
        "postal_code_id": np.random.randint(1, max_postal_code_id + 1, size=num_customers),
        "age": np.random.randint(18, 66, size=num_customers),
        "gender": genders,
        "first_name": first_names,
        "last_name": last_names,
        "email": emails,
        "phone_number": [fake.phone_number() for _ in range(num_customers)],
        "bank_account_number": [fake.iban() for _ in range(num_customers)],
    }
    return pd.DataFrame(data)

def remove_polish_accents(text):
    # Normalizacja tekstu i usunięcie znaków diakrytycznych
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def generate_customer_data(num_customers):
    # Params:
    max_postal_code_id = 43783

    # Generate source:
    customer_data = generate_customers(num_customers, max_postal_code_id)

    # Merge source:
    customer_data = pd.merge(customer_data, code_df, how='left', left_on='postal_code_id', right_on='id').drop(columns=['id', 'postal_code_id'])

    return customer_data