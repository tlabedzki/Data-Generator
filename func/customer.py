import pandas as pd
import numpy as np
from faker import Faker
from pathlib import Path

import func.data as d

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -- - - - - - - - - - #
    # Settings:

# Create faker instance for Polish language
fake = Faker('pl_PL')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Paths:

SOURCE_DATA = Path("source")
POSTAL_CODE_DATA = SOURCE_DATA / "pl_postal_code.csv"

code_df = pd.read_csv(POSTAL_CODE_DATA, sep=";")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def generate_customers(num_customers, max_postal_code_id):
    """
    Generate a DataFrame containing customer data.

    Parameters:
    num_customers (int): The number of customers to generate.
    max_postal_code_id (int): The maximum postal code ID to use for generating postal codes.

    Returns:
    pd.DataFrame: A DataFrame containing the generated customer data.
    """
    # Randomly assign genders to customers
    genders = np.random.choice(["Male", "Female"], size=num_customers, p=[0.5, 0.5])

    # Generate male and female first names
    male_first_names = [fake.first_name_male() for _ in range(num_customers)]
    female_first_names = [fake.first_name_female() for _ in range(num_customers)]

    # Assign first names based on gender
    first_names = [male_first_names[i] if genders[i] == "Male" else female_first_names[i] for i in range(num_customers)]

    # Generate last names and remove Polish accents
    last_names = [fake.last_name() for _ in range(num_customers)]
    last_names_without_polish_letters = [d.remove_polish_accents(last_name) for last_name in last_names]

    # List of popular e-mail domains
    domains = np.random.choice(['gmailx.com', 'yahoox.com', 'outlookx.com'], size=num_customers, p=[0.5, 0.3, 0.2])

    # Generate e-mails based on first and last names with random domains
    emails = [f"{first_names[i].lower()}.{last_names_without_polish_letters[i].lower()}@{domains[i]}" for i in range(num_customers)]

    # Create customer data dictionary
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

    # Return the generated customer data as a DataFrame
    return pd.DataFrame(data)

def generate_customer_data(num_customers):
    """
    Generate customer data and merge it with postal code data.

    Parameters:
    num_customers (int): The number of customers to generate.

    Returns:
    pd.DataFrame: A DataFrame containing the generated customer data merged with postal code data.
    """
    # Params:
    max_postal_code_id = 43783

    # Generate source:
    customer_data = generate_customers(num_customers, max_postal_code_id)

    # Merge source:
    customer_data = pd.merge(customer_data, code_df, how='left', left_on='postal_code_id', right_on='id').drop(columns=['id', 'postal_code_id'])

    return customer_data