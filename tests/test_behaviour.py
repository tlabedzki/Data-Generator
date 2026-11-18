"""Pack A: customer behaviour. Segments, signup, churn and demographics leave measurable traces in the orders."""
import numpy as np
import pandas as pd
import pytest
from conftest import generate

import func.calendar as cal
import func.rng as rng
import settings.behaviour_settings as bs
import settings.main_settings as s


@pytest.fixture(scope="module")
def data():
    return generate(customers=4000, products=1500, order_lines=12000)


def test_customers_have_segment_and_signup(data):
    customers = data["customer_data"]
    assert set(customers["customer_segment"]) == set(bs.customer_segments)
    shares = customers["customer_segment"].value_counts(normalize=True)
    for name, segment in bs.customer_segments.items():
        assert shares[name] == pytest.approx(segment["share"], abs=0.03)
    assert customers["signup_date"].max() <= pd.Timestamp(s.end_year, 12, 31)
    existing = (customers["signup_date"] < pd.Timestamp(s.start_year, 1, 1)).mean()
    assert existing == pytest.approx(bs.existing_customer_share, abs=0.03)


def test_no_order_before_signup(data):
    sales = data["sales_data"]
    assert (sales["order_date"] >= sales["signup_date"]).all()


def test_one_time_customers_order_at_most_once(data):
    sales = data["sales_data"]
    normal = sales[~sales["is_fraud"]]
    orders = normal[normal["customer_segment"] == "one_time"].groupby("customer_id")["order_id"].nunique()
    assert orders.max() == 1


def test_loyal_customers_buy_more_often(data):
    sales, customers = data["sales_data"], data["customer_data"]
    orders = sales.groupby("customer_id")["order_id"].nunique().reindex(customers["customer_id"], fill_value=0)
    by_segment = orders.groupby(customers.set_index("customer_id")["customer_segment"]).mean()
    assert by_segment["loyal"] > 2 * by_segment["regular"] > 2 * by_segment["one_time"]
    assert orders.var() / orders.mean() > 2


def test_deal_hunters_get_more_discounts(data):
    sales = data["sales_data"]
    discounted = (sales["discount_rate"] > 0).groupby(sales["customer_segment"]).mean()
    assert discounted["deal_hunter"] > 1.8 * discounted["loyal"]


def test_retention_falls_after_the_first_month(data):
    sales = data["sales_data"]
    orders = sales[sales["signup_date"] >= pd.Timestamp(s.start_year, 1, 1)].drop_duplicates("order_id")
    first = orders.groupby("customer_id")["order_date"].transform("min")
    months = ((orders["order_date"] - first).dt.days // 30)
    active = pd.DataFrame({"customer": orders["customer_id"], "month": months}).drop_duplicates()
    cohort = active.loc[active["month"] == 0, "customer"].nunique()
    retention = active.groupby("month")["customer"].nunique() / cohort
    assert retention[1] > retention[11]


def test_age_changes_the_category_mix(data):
    sales = data["sales_data"]
    young, old = sales[sales["age"] < 30], sales[sales["age"] >= 55]
    assert (young["category"] == "Electronics").mean() > (old["category"] == "Electronics").mean()
    assert (old["category"] == "Health").mean() > (young["category"] == "Health").mean()


def test_expensive_orders_use_deferred_payment_more_often(data):
    sales = data["sales_data"]
    orders = sales.groupby("order_id").agg(value=("revenue_gross", "sum"), method=("payment_method", "first"))
    expensive = orders["value"] > bs.high_value_order_threshold
    deferred = orders["method"] == "Deferred payment"
    assert deferred[expensive].mean() > 1.5 * deferred[~expensive].mean()


def test_calendar_months_follow_settings_without_bias(monkeypatch):
    target = np.asarray(s.base_monthly_seasonality) / np.sum(s.base_monthly_seasonality)
    shares = []
    for seed in range(10):
        monkeypatch.setattr(s, "random_state", seed)
        calendar = cal.build_calendar(rng.stream("calendar"))
        shares.append(calendar.groupby("month")["weight"].sum().to_numpy())
    np.testing.assert_allclose(np.mean(shares, axis=0), target, atol=0.004)


def test_calendar_without_noise_is_exact(monkeypatch):
    calendar = cal.build_calendar(rng.stream("calendar"), month_noise_sd=0.0)
    year = calendar[calendar["year"] == s.start_year]
    shares = year.groupby("month")["weight"].sum() / year["weight"].sum()
    target = np.asarray(s.base_monthly_seasonality) / np.sum(s.base_monthly_seasonality)
    np.testing.assert_allclose(shares.to_numpy(), target, atol=1e-9)


def test_many_customers_and_few_lines_still_work():
    small = generate(customers=3000, products=200, order_lines=150)
    assert len(small["order_data"]) >= 150
    assert small["order_data"]["customer_id"].isin(small["customer_data"]["customer_id"]).all()
