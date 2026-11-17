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

SOURCE_DATA = Path(__file__).resolve().parents[1] / "source"
POSTAL_CODE_DATA = SOURCE_DATA / "pl_postal_code.csv"

code_df = pd.read_csv(POSTAL_CODE_DATA, sep=";", dtype={"postal_code": str})

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

# Reserved example domains (RFC 2606), so generated addresses can never belong to a real mailbox:
EMAIL_DOMAINS_WITH_PROBABILITIES = {"example.com": 0.5, "example.org": 0.3, "example.net": 0.2}

def make_unique_emails(emails):
    """
    Make e-mail addresses unique by adding a number to repeated local parts (jan.kowalski2@example.com).

    Parameters:
    emails (list): E-mail addresses, possibly with duplicates.

    Returns:
    list: Unique e-mail addresses in the same order.
    """
    used = set(emails)
    seen = set()
    unique_emails = []

    for email in emails:
        if email not in seen:
            seen.add(email)
            unique_emails.append(email)
            continue

        local_part, domain = email.split("@", 1)
        suffix = 2
        while f"{local_part}{suffix}@{domain}" in used:
            suffix += 1
        candidate = f"{local_part}{suffix}@{domain}"
        used.add(candidate)
        seen.add(candidate)
        unique_emails.append(candidate)

    return unique_emails

def generate_customers(num_customers, postal_code_ids, postal_code_weights=None):
    """
    Generate a DataFrame containing customer data.

    Parameters:
    num_customers (int): The number of customers to generate.
    postal_code_ids (array-like): Postal code IDs to draw customer addresses from.
    postal_code_weights (array-like, optional): Draw weights for postal_code_ids (e.g. number of addresses).

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

    # Draw e-mail domains:
    domain_names, domain_probabilities = d.get_param_list_and_normalized_probabilities(EMAIL_DOMAINS_WITH_PROBABILITIES)
    domains = np.random.choice(domain_names, size=num_customers, p=domain_probabilities)

    # Generate unique e-mails based on first and last names with random domains:
    first_names_without_polish_letters = [d.remove_polish_accents(first_name) for first_name in first_names]
    emails = make_unique_emails([
        f"{first_names_without_polish_letters[i].lower()}.{last_names_without_polish_letters[i].lower()}@{domains[i]}".replace(" ", "")
        for i in range(num_customers)
    ])

    # Create customer data dictionary
    data = {
        "customer_id": range(100001, 100001 + num_customers),
        "postal_code_id": draw_postal_code_ids(num_customers, postal_code_ids, postal_code_weights),
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

def draw_postal_code_ids(num_customers, postal_code_ids, postal_code_weights=None):
    """
    Draw a postal code ID for every customer, weighted when weights are given.

    Parameters:
    num_customers (int): The number of customers.
    postal_code_ids (array-like): Postal code IDs.
    postal_code_weights (array-like, optional): Non-negative weights, one per ID.

    Returns:
    np.array: Drawn postal code IDs.
    """
    probabilities = None
    if postal_code_weights is not None:
        weights = np.asarray(postal_code_weights, dtype=float)
        probabilities = weights / weights.sum()

    return np.random.choice(np.asarray(postal_code_ids), size=num_customers, p=probabilities)

def generate_customer_data(num_customers):
    """
    Generate customer data and merge it with postal code data.

    Parameters:
    num_customers (int): The number of customers to generate.

    Returns:
    pd.DataFrame: A DataFrame containing the generated customer data merged with postal code data.
    """
    # Generate source:
    # Postal codes are weighted by their number of addresses, so busy areas get more customers:
    customer_data = generate_customers(num_customers, code_df['id'].to_numpy(), code_df['address_count'].to_numpy())

    # Merge source:
    postal_codes = code_df[['id', 'postal_code', 'city']]
    customer_data = pd.merge(customer_data, postal_codes, how='left', left_on='postal_code_id', right_on='id').drop(columns=['id', 'postal_code_id'])

    return customer_data