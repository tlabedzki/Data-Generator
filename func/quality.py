"""
Dirty data for cleaning exercises: missing values, typos, mixed formats, outliers and duplicates.

Issues are injected into the source tables (customers, products, order lines) before the sales lines are joined, so
the joined table is dirty in the same way. Every issue is recorded in quality_issue_data with the clean value.
"""
import numpy as np
import pandas as pd

import func.data as d
import func.rng as rng
import settings.quality_settings as qs

ISSUE_COLUMNS = ["issue_id", "table_name", "key_column", "key_value", "column_name", "issue_type", "dirty_value",
                 "clean_value"]
KEY_COLUMNS = {"customer_data": "customer_id", "product_data": "product_id", "order_data": "order_line_id"}
AGE_OUTLIERS = [0, 1, 2, 117, 150, 999]


def empty_issue_data():
    return pd.DataFrame({column: pd.Series(dtype="int64" if column == "issue_id" else "object")
                         for column in ISSUE_COLUMNS})


def quality_rate(level=None):
    level = qs.data_quality_level if level is None else level
    if level not in qs.data_quality_rates:
        raise ValueError(f"Unsupported data_quality_level: {level}. Use one of {list(qs.data_quality_rates)}.")
    return qs.data_quality_rates[level]


def as_text(value):
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# ---------------------------------------------------------------------------------------------------------------- #
# Single-value changes

def city_typo(city, generator):
    kind = generator.integers(5)
    if kind == 0:
        return city.lower()
    if kind == 1:
        return city.upper()
    if kind == 2 and d.remove_polish_accents(city) != city:
        return d.remove_polish_accents(city)
    if kind == 3 and len(city) > 3:
        position = int(generator.integers(1, len(city) - 2))
        return city[:position] + city[position + 1] + city[position] + city[position + 2:]
    return f" {city}  "


def phone_format(phone, generator):
    digits = "".join(character for character in phone if character.isdigit())
    national = digits[2:] if digits.startswith("48") and len(digits) == 11 else digits
    kind = generator.integers(4)
    if kind == 0:
        return national
    if kind == 1:
        return "-".join([national[:3], national[3:6], national[6:]])
    if kind == 2:
        return f"0048{national}"
    return f"({national[:2]}) {national[2:]}"


def postal_code_format(code, generator):
    return code.replace("-", "") if generator.random() < 0.7 else code.replace("-", " ")


def email_format(email, generator):
    return email.upper() if generator.random() < 0.6 else f" {email} "


def change_value(table_name, column, issue_type, value, generator):
    """Return the dirty version of one value."""
    if issue_type == "missing":
        return None
    if column == "city":
        return city_typo(value, generator)
    if column == "phone_number":
        return phone_format(value, generator)
    if column == "postal_code":
        return postal_code_format(value, generator)
    if column == "email":
        return email_format(value, generator)
    if column == "age":
        return int(generator.choice(AGE_OUTLIERS))
    if column == "quantity":
        return int(generator.integers(50, 501))
    if column == "net_purchase_price":
        return round(float(value) * 100, 2)
    raise ValueError(f"No rule for issue {issue_type} in {table_name}.{column}.")


# ---------------------------------------------------------------------------------------------------------------- #
# Table-level issues

def duplicate_customers(customer_data, order_data, rows, generator):
    """
    Give a few customers a second account: a copy with a new ID and a slightly different e-mail; about half of their
    orders after the first one move to the new account.

    Returns:
    tuple: (customers, order lines, issue records).
    """
    if not len(rows):
        return customer_data, order_data, []
    originals = customer_data.loc[rows].copy()
    next_id = int(customer_data["customer_id"].max()) + 1
    new_ids = np.arange(next_id, next_id + len(originals))
    original_ids = originals["customer_id"].to_numpy()
    originals["customer_id"] = new_ids
    emails = originals["email"].astype(str)
    originals["email"] = [
        email.replace("@", f"{int(generator.integers(1, 99))}@", 1) if "@" in email else email for email in emails
    ]
    customer_data = pd.concat([customer_data, originals], ignore_index=True)

    if order_data is not None:
        mapping = dict(zip(original_ids, new_ids, strict=True))
        orders = order_data.drop_duplicates("order_id")[["order_id", "customer_id"]]
        orders = orders[orders["customer_id"].isin(mapping)]
        later = orders[orders.duplicated("customer_id")]
        moved = later[generator.random(len(later)) < 0.5]
        moved_ids = dict(zip(moved["order_id"], moved["customer_id"].map(mapping), strict=True))
        lines = order_data["order_id"].isin(moved_ids)
        order_data.loc[lines, "customer_id"] = order_data.loc[lines, "order_id"].map(moved_ids)

    records = [("customer_data", "customer_id", str(new_id), "customer_id", "duplicate_customer", str(new_id),
                str(original_id)) for new_id, original_id in zip(new_ids, original_ids, strict=True)]
    return customer_data, order_data, records


def duplicate_order_lines(order_data, rows):
    if not len(rows):
        return order_data, []
    copies = order_data.loc[rows]
    order_data = pd.concat([order_data, copies]).sort_index(kind="stable").reset_index(drop=True)
    records = [("order_data", "order_line_id", str(key), "order_line_id", "duplicate_row", str(key), "")
               for key in copies["order_line_id"]]
    return order_data, records


def choose_rows(table, column, share, used, generator):
    """Draw distinct row labels for one issue, skipping rows that already carry an issue in the same column."""
    available = table.index.difference(used.get(column, pd.Index([])))
    if column != "customer_id":
        available = available[table.loc[available, column].notna().to_numpy()]
    count = min(int(round(len(table) * share)), len(available))
    rows = pd.Index(generator.choice(available, size=count, replace=False)) if count else pd.Index([])
    used[column] = used.get(column, pd.Index([])).union(rows)
    return rows


def inject_quality_issues(tables, level=None):
    """
    Inject data quality issues into the source tables.

    Parameters:
    tables (dict): "customer_data", "product_data" and "order_data" mapped to DataFrames (or None).
    level (str, optional): Overrides settings.quality_settings.data_quality_level.

    Returns:
    tuple: (tables with issues, quality_issue_data).
    """
    rate = quality_rate(level)
    if rate == 0:
        return tables, empty_issue_data()

    generator = rng.stream("quality")
    tables = {name: (None if table is None else table.copy()) for name, table in tables.items()}
    used = {name: {} for name in tables}
    records = []

    for table_name, column, issue_type, multiplier in qs.data_quality_issues:
        table = tables.get(table_name)
        if table is None or column not in table:
            continue
        rows = choose_rows(table, column, rate * multiplier, used[table_name], generator)
        if issue_type == "duplicate_customer":
            customers, orders, new = duplicate_customers(table, tables.get("order_data"), rows, generator)
            tables["customer_data"], tables["order_data"] = customers, orders
            records += new
            continue
        if issue_type == "duplicate_row":
            tables[table_name], new = duplicate_order_lines(table, rows)
            records += new
            continue
        key_column = KEY_COLUMNS[table_name]
        if issue_type == "missing" or column == "age":
            table[column] = table[column].astype(object if table[column].dtype == object else "Float64")
        for row in rows:
            clean = table.at[row, column]
            dirty = change_value(table_name, column, issue_type, clean, generator)
            table.at[row, column] = pd.NA if dirty is None and table[column].dtype != object else dirty
            records.append((table_name, key_column, as_text(table.at[row, key_column]), column, issue_type,
                            as_text(dirty), as_text(clean)))
        if column == "age":
            table[column] = table[column].astype("Int64")

    if not records:
        return tables, empty_issue_data()
    issue_data = pd.DataFrame(records, columns=ISSUE_COLUMNS[1:])
    issue_data.insert(0, "issue_id", np.arange(1, len(issue_data) + 1))
    return tables, issue_data
