"""Pack E: dirty data. Issue shares follow the level and every issue is listed with its clean value."""
import pandas as pd
import pytest

import func.quality as q
import settings.quality_settings as qs
from conftest import generate

LEVEL = "medium"
RATE = qs.data_quality_rates[LEVEL]


@pytest.fixture(scope="module")
def dirty():
    return generate(customers=1500, products=800, order_lines=4000, quality_level=LEVEL)


def multiplier(table, column, issue_type):
    return next(m for t, c, i, m in qs.data_quality_issues if (t, c, i) == (table, column, issue_type))


def test_clean_level_has_no_issues(small_data):
    issues = small_data["quality_issue_data"]
    assert issues.empty and list(issues.columns) == q.ISSUE_COLUMNS
    assert small_data["customer_data"].notna().all().all()
    assert small_data["order_data"]["order_line_id"].is_unique


@pytest.mark.parametrize("column", ["phone_number", "city", "age", "email"])
def test_missing_share_follows_level(dirty, column):
    customers = dirty["customer_data"]
    original = (customers["customer_id"] < customers["customer_id"].max() - dirty_new_ids(dirty) + 1).sum()
    expected = RATE * multiplier("customer_data", column, "missing") * original
    missing = customers[column].isna().sum()
    assert abs(missing - expected) <= max(0.2 * expected, 2)


def dirty_new_ids(data):
    issues = data["quality_issue_data"]
    return int((issues["issue_type"] == "duplicate_customer").sum())


def test_every_recorded_issue_is_in_the_data(dirty):
    issues = dirty["quality_issue_data"]
    customers = dirty["customer_data"].set_index("customer_id")
    for row in issues[issues["table_name"] == "customer_data"].itertuples():
        if row.issue_type == "duplicate_customer":
            continue
        value = customers.at[int(row.key_value), row.column_name]
        assert q.as_text(value) == row.dirty_value
        assert row.dirty_value != row.clean_value


def test_duplicate_customers_point_to_a_real_person(dirty):
    issues = dirty["quality_issue_data"]
    duplicates = issues[issues["issue_type"] == "duplicate_customer"]
    customers = dirty["customer_data"].set_index("customer_id")
    assert len(duplicates) == round(RATE * multiplier("customer_data", "customer_id", "duplicate_customer") * 1500)
    for row in duplicates.itertuples():
        new, original = customers.loc[int(row.dirty_value)], customers.loc[int(row.clean_value)]
        assert (new["first_name"], new["last_name"]) == (original["first_name"], original["last_name"])
        assert new["email"] != original["email"]


def test_duplicate_order_lines_and_outliers(dirty):
    orders, issues = dirty["order_data"], dirty["quality_issue_data"]
    duplicated = issues.loc[issues["issue_type"] == "duplicate_row", "key_value"].astype(int)
    assert orders["order_line_id"].duplicated().sum() == len(duplicated) > 0
    outliers = issues[(issues["column_name"] == "quantity")]
    assert (outliers["dirty_value"].astype(int) >= 50).all()
    assert len(dirty["sales_data"]) == len(orders)


def test_issues_do_not_change_the_clean_data():
    clean = generate(customers=500, products=300, order_lines=1500)
    dirty = generate(customers=500, products=300, order_lines=1500, quality_level="low")
    issues = dirty["quality_issue_data"]
    touched = set(issues.loc[issues["table_name"] == "product_data", "key_value"].astype(int))
    untouched = ~clean["product_data"]["product_id"].isin(touched)
    pd.testing.assert_frame_equal(clean["product_data"][untouched].reset_index(drop=True),
                                  dirty["product_data"][untouched].reset_index(drop=True), check_dtype=False)


def test_unknown_level_is_rejected():
    with pytest.raises(ValueError):
        q.quality_rate("extreme")
