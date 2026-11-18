"""Pack E: labelled anomalies. Fraud rings and shop outages are in anomaly_data and visible in the orders."""
import pytest
from conftest import generate

import settings.quality_settings as qs


@pytest.fixture(scope="module")
def data():
    return generate(customers=1500, products=1000, order_lines=8000)


def test_anomaly_table(data):
    anomalies = data["anomaly_data"]
    assert set(anomalies["anomaly_type"]) == {"fraud_ring", "shop_outage", "return_spike"}
    assert anomalies["anomaly_id"].is_unique
    assert (anomalies["end_date"] >= anomalies["start_date"]).all()


def test_fraud_orders_are_labelled_and_unusual(data):
    sales = data["sales_data"]
    orders = sales.groupby("order_id").agg(value=("revenue_gross", "sum"), fraud=("is_fraud", "first"),
                                           home=("postal_code", "first"), ship=("shipping_postal_code", "first"))
    fraud = orders[orders["fraud"]]
    rings = data["anomaly_data"].query("anomaly_type == 'fraud_ring'")
    assert sales["is_fraud"].sum() == rings["affected_rows"].sum()
    assert len(fraud) == pytest.approx(qs.fraud_order_share * len(orders), abs=qs.fraud_orders_per_account[1])
    assert fraud["value"].mean() >= 3 * orders.loc[~orders["fraud"], "value"].mean()
    assert (fraud["ship"] != fraud["home"]).mean() >= 0.9
    legit = orders[~orders["fraud"]]
    assert (legit["ship"] != legit["home"]).mean() == pytest.approx(qs.other_shipping_address_share, abs=0.02)


def test_outage_day_has_almost_no_orders(data):
    orders = data["order_data"].drop_duplicates("order_id")
    per_day = orders.groupby("order_date").size()
    for day in data["anomaly_data"].query("anomaly_type == 'shop_outage'")["start_date"]:
        assert per_day.get(day, 0) <= 0.1 * per_day.median() + 1


def test_orders_are_numbered_after_anomalies(data):
    orders = data["order_data"]
    order_ids = orders["order_id"].drop_duplicates()
    assert order_ids.tolist() == list(range(100001, 100001 + len(order_ids)))
    assert orders["order_line_id"].is_unique and orders["order_date"].is_monotonic_increasing


def test_anomalies_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(qs, "inject_anomalies", False)
    data = generate(customers=300, products=300, order_lines=800)
    assert data["anomaly_data"].empty and not data["order_data"]["is_fraud"].any()
