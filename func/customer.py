"""Customers: names, e-mails, phone numbers and bank accounts from Faker, ages and genders, weighted postal codes."""
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

import func.data as d

# Polish Faker instance; generator.seed_faker() seeds it for reproducible names:
fake = Faker("pl_PL")

POSTAL_CODE_DATA = Path(__file__).resolve().parents[1] / "source" / "pl_postal_code.csv"
code_df = pd.read_csv(POSTAL_CODE_DATA, sep=";", dtype={"postal_code": str})

# Reserved example domains (RFC 2606), so generated addresses can never belong to a real mailbox:
EMAIL_DOMAINS_WITH_PROBABILITIES = {"example.com": 0.5, "example.org": 0.3, "example.net": 0.2}


def make_unique_emails(emails: list[str]) -> list[str]:
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


def generate_customers(num_customers: int, postal_code_ids: np.ndarray, postal_code_weights: np.ndarray | None,
                       generator: np.random.Generator) -> pd.DataFrame:
    """
    Generate customers with names from Faker and the other values from the random stream.

    Parameters:
    num_customers (int): The number of customers to generate.
    postal_code_ids (array-like): Postal code IDs to draw customer addresses from.
    postal_code_weights (array-like or None): Draw weights for postal_code_ids (e.g. number of addresses).
    generator (np.random.Generator): Random stream for genders, domains, ages and postal codes.

    Returns:
    pd.DataFrame: One row per customer.
    """
    genders = generator.choice(np.array(["Male", "Female"]), size=num_customers)
    first_names = [fake.first_name_male() if gender == "Male" else fake.first_name_female() for gender in genders]
    last_names = [fake.last_name() for _ in range(num_customers)]

    domain_names, domain_probabilities = d.get_param_list_and_normalized_probabilities(EMAIL_DOMAINS_WITH_PROBABILITIES)
    domains = generator.choice(np.array(domain_names), size=num_customers, p=domain_probabilities)
    emails = make_unique_emails([
        f"{d.remove_polish_accents(first)}.{d.remove_polish_accents(last)}@{domain}".lower().replace(" ", "")
        for first, last, domain in zip(first_names, last_names, domains, strict=True)
    ])

    return pd.DataFrame({
        "customer_id": np.arange(100001, 100001 + num_customers),
        "postal_code_id": draw_postal_code_ids(num_customers, postal_code_ids, postal_code_weights, generator),
        "age": generator.integers(18, 66, size=num_customers),
        "gender": genders,
        "first_name": first_names,
        "last_name": last_names,
        "email": emails,
        "phone_number": [fake.phone_number() for _ in range(num_customers)],
        "bank_account_number": [fake.iban() for _ in range(num_customers)],
    })


def draw_postal_code_ids(num_customers: int, postal_code_ids: np.ndarray, postal_code_weights: np.ndarray | None,
                         generator: np.random.Generator) -> np.ndarray:
    """
    Draw a postal code ID for every customer, weighted when weights are given.

    Parameters:
    num_customers (int): The number of customers.
    postal_code_ids (array-like): Postal code IDs.
    postal_code_weights (array-like or None): Non-negative weights, one per ID.
    generator (np.random.Generator): Random stream.

    Returns:
    np.ndarray: Drawn postal code IDs.
    """
    probabilities = None
    if postal_code_weights is not None:
        weights = np.asarray(postal_code_weights, dtype=float)
        probabilities = weights / weights.sum()

    return generator.choice(np.asarray(postal_code_ids), size=num_customers, p=probabilities)


def generate_customer_data(num_customers: int, generator: np.random.Generator) -> pd.DataFrame:
    """
    Generate customers and add the postal code and locality of their address.

    Postal codes are weighted by their number of addresses, so busy areas get more customers.

    Parameters:
    num_customers (int): The number of customers to generate.
    generator (np.random.Generator): Random stream.

    Returns:
    pd.DataFrame: Customers with postal_code and city.
    """
    customer_data = generate_customers(num_customers, code_df["id"].to_numpy(), code_df["address_count"].to_numpy(),
                                       generator)
    postal_codes = code_df[["id", "postal_code", "city"]]
    return (customer_data.merge(postal_codes, how="left", left_on="postal_code_id", right_on="id")
            .drop(columns=["id", "postal_code_id"]))
