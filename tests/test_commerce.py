"""Pack D: special days, product life cycle, price history, discounts, shipping and returns."""
import pandas as pd
import pytest
from conftest import generate

import func.calendar as cal
import settings.commerce_settings as cs
import settings.main_settings as s


@pytest.fixture(scope="module")
def data():
    return generate(customers=3000, products=1500, order_lines=15000)


def test_named_days():
    assert cal.black_friday(2024) == pd.Timestamp(2024, 11, 29)
    assert cal.black_friday(2023) == pd.Timestamp(2023, 11, 24)
    assert cal.easter_sunday(2024) == pd.Timestamp(2024, 3, 31)
    assert cal.easter_sunday(2025) == pd.Timestamp(2025, 4, 20)


def test_special_days_keep_month_totals(monkeypatch):
    import func.rng as rng
    with_days = cal.build_calendar(rng.stream("calendar"))
    monkeypatch.setattr(cs, "special_days", {})
    without = cal.build_calendar(rng.stream("calendar"))
    months = ["year", "month"]
    pd.testing.assert_series_equal(with_days.groupby(months)["weight"].sum(), without.groupby(months)["weight"].sum())


def test_black_friday_and_christmas(data):
    per_day = data["order_data"].drop_duplicates("order_id").groupby("order_date").size()
    friday = cal.black_friday(s.end_year)
    november = per_day[(per_day.index.month == 11) & (per_day.index.year == s.end_year)]
    assert per_day[friday] > 2.5 * november.mean()
    december = per_day[(per_day.index.month == 12) & (per_day.index.year == s.end_year)]
    assert per_day.get(pd.Timestamp(s.end_year, 12, 25), 0) < 0.6 * december.mean()


def test_evening_is_busier_than_night(data):
    hours = data["order_data"].drop_duplicates("order_id")["order_datetime"].dt.hour
    assert (hours.between(19, 22)).mean() > 4 * (hours.between(2, 5)).mean()


def test_products_sell_only_while_on_sale(data):
    lines, products = data["sales_data"], data["product_data"].set_index("product_id")
    legit = lines[~lines["is_fraud"]]
    launch = legit["product_id"].map(products["launch_date"])
    stop = legit["product_id"].map(products["discontinued_date"])
    assert (legit["order_date"] >= launch).all()
    assert not (legit["order_date"] >= stop).any()


def test_price_history_is_consistent(data):
    history, products = data["price_history"], data["product_data"]
    assert set(history["product_id"]) == set(products["product_id"])
    last = history.groupby("product_id").tail(1).set_index("product_id")["sales_price_gross"]
    current = products.set_index("product_id")["sales_price_gross"].sort_index()
    pd.testing.assert_series_equal(last.sort_index(), current,
                                   check_names=False)
    assert (history["sales_price_gross"] % 10 == 9).all()
    gaps = history.groupby("product_id")["valid_from"].diff().dropna()
    assert (gaps > pd.Timedelta(0)).all()


def test_line_price_comes_from_price_history(data):
    lines, history = data["sales_data"], data["price_history"]
    merged = pd.merge_asof(lines.sort_values("order_date"), history.sort_values("valid_from"), left_on="order_date",
                           right_on="valid_from", by="product_id", suffixes=("", "_history"))
    assert (merged["unit_price_gross"] == merged["sales_price_gross_history"]).all()


def test_discounts_raise_quantity(data):
    lines = data["sales_data"]
    assert lines.loc[lines["discount_rate"] > 0.2, "quantity"].mean() > 1.1 * lines.loc[
        lines["discount_rate"] == 0, "quantity"].mean()


def test_bulky_goods_never_go_to_lockers(data):
    shipments = data["shipment_data"]
    assert shipments["is_bulky"].any()
    assert not shipments.loc[shipments["is_bulky"], "delivery_method"].isin(cs.locker_delivery_methods).any()


def test_shipments(data):
    shipments, orders = data["shipment_data"], data["order_data"].drop_duplicates("order_id").set_index("order_id")
    assert len(shipments) == len(orders) and shipments["order_id"].is_unique
    placed = shipments["order_id"].map(orders["order_datetime"])
    assert (shipments["shipped_at"] > placed).all()
    assert (shipments["delivered_at"] > shipments["shipped_at"]).all()
    value = (data["sales_data"].groupby("order_id")["revenue_gross"].sum()).reindex(shipments["order_id"]).to_numpy()
    free = (value >= cs.free_shipping_threshold) & ~shipments["is_bulky"].to_numpy()
    assert (shipments.loc[free, "shipping_cost"] == 0).all()
    late = shipments.groupby(shipments["shipped_at"].dt.month.isin(cs.peak_months))["is_late"].mean()
    assert late[True] > late[False]


def test_returns(data):
    returns, lines = data["return_data"], data["sales_data"].set_index("order_line_id")
    assert returns["order_line_id"].isin(lines.index).all()
    line = lines.loc[returns["order_line_id"]]
    assert (returns["returned_quantity"].to_numpy() <= line["quantity"].to_numpy()).all()
    assert (returns["return_date"].to_numpy() > line["order_date"].to_numpy()).all()
    assert not line["is_fraud"].any()
    refunded = returns["return_status"] == "refunded"
    expected = (returns["returned_quantity"] * line["unit_price_gross"].to_numpy()
                * (1 - line["discount_rate"].to_numpy())).round(2)
    pd.testing.assert_series_equal(returns.loc[refunded, "refund_amount"], expected[refunded], check_names=False)
    rate = returns.merge(data["product_data"][["product_id", "category"]]).groupby("category").size() / \
        data["sales_data"].groupby("category").size()
    assert rate["Clothing"] > 2.5 * rate["Electronics"]
    clothing = returns.merge(data["product_data"][["product_id", "category"]]).query("category == 'Clothing'")
    assert clothing["return_reason"].value_counts().idxmax() == "wrong_size"


def test_return_spike_is_labelled(data):
    spike = data["anomaly_data"].query("anomaly_type == 'return_spike'").iloc[0]
    assert spike["affected_rows"] > 0
    product = int(spike["description"].split("product ")[1].split(":")[0])
    lines = data["sales_data"]
    in_spike = lines["order_date"].between(spike["start_date"], spike["end_date"])
    window = lines[(lines["product_id"] == product) & in_spike]
    returned = window["order_line_id"].isin(data["return_data"]["order_line_id"]).mean()
    assert returned > 0.3
