"""Pack B: products bought together, customer preferences and replenishment."""
import pytest

import settings.basket_settings as bk
from conftest import generate


@pytest.fixture(scope="module")
def data():
    return generate(customers=3000, products=2500, order_lines=20000)


def lift(lines, first, second):
    baskets = lines.groupby("order_id")["product_type"].agg(set)
    a = baskets.map(lambda types: first in types)
    b = baskets.map(lambda types: second in types)
    return (a & b).mean() / (a.mean() * b.mean())


def test_complements_are_bought_together(data):
    lines = data["sales_data"][~data["sales_data"]["is_fraud"]]
    assert lift(lines, "Laptop", "Wireless Mouse") > 3
    assert lift(lines, "Smartphone", "Headphones") > 2


def test_customers_have_preferences(data):
    customers = data["customer_data"]
    assert set(customers["price_tier"]) == set(bk.price_tiers)
    assert customers["preferred_category"].notna().all()
    lines = data["sales_data"]
    assert (lines["category"] == lines["preferred_category"]).mean() > bk.category_loyalty


def test_premium_customers_buy_dearer_products(data):
    lines = data["sales_data"]
    median = lines.groupby("price_tier")["unit_price_gross"].median()
    assert median["premium"] > 1.2 * median["budget"]


def test_replenishment_follows_the_cycle():
    # Fewer orders per customer than the shared sample, so occasional pet food purchases do not hide the cycle.
    lines = generate(customers=8000, products=2000, order_lines=16000)["sales_data"]
    pet = lines[lines["product_type"].isin(["Dog Food", "Cat Food"])].drop_duplicates(["order_id", "product_id"])
    gaps = pet.sort_values("order_date").groupby(["customer_id", "product_id"])["order_date"].diff().dt.days.dropna()
    assert len(gaps) > 20
    assert 20 <= gaps.median() <= 45


def test_months_still_follow_the_calendar(data):
    orders = data["order_data"].drop_duplicates("order_id")
    share = orders["order_date"].dt.month.value_counts(normalize=True)
    assert share[11] > share[6] * 2
