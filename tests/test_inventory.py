"""Suppliers, purchase orders and stock (1.8.0), with stockouts off (default) and on."""
import numpy as np
import pandas as pd
import pytest

import func.inventory as inventory
import settings.inventory_settings as inv
from tests.conftest import generate

NEW_TABLES = ["supplier_data", "product_supplier_data", "purchase_order_data", "stock_movement_data",
              "lost_demand_data"]
COLUMNS = {"supplier_data": inventory.SUPPLIER_COLUMNS, "product_supplier_data": inventory.PRODUCT_SUPPLIER_COLUMNS,
           "purchase_order_data": inventory.PURCHASE_ORDER_COLUMNS,
           "stock_movement_data": inventory.MOVEMENT_COLUMNS, "lost_demand_data": inventory.LOST_DEMAND_COLUMNS}
LINE_KEY = ["order_date", "customer_id", "product_id", "quantity"]


def generate_with(stockouts=False, **changes):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(inv, "stockouts", stockouts)
        for name, value in changes.items():
            mp.setattr(inv, name, value)
        return generate(customers=600, products=300, order_lines=4000)


@pytest.fixture(scope="module")
def served():
    return generate_with()


@pytest.fixture(scope="module")
def short():
    return generate_with(stockouts=True)


def stock_by_day(movements):
    """End-of-day stock of every product on every day it moved."""
    return movements.groupby(["product_id", "movement_date"])["stock_after"].last()


def test_new_tables_have_their_columns(served):
    for name in NEW_TABLES:
        assert list(served[name].columns) == COLUMNS[name]


def test_every_product_has_one_supplier_with_a_pack_and_minimum(served):
    supply, products = served["product_supplier_data"], served["product_data"]
    assert supply["product_id"].tolist() == products["product_id"].tolist()
    assert supply["supplier_id"].isin(served["supplier_data"]["supplier_id"]).all()
    assert (supply["pack_size"] >= 1).all()
    assert (supply["min_order_quantity"] % supply["pack_size"] == 0).all()
    pairs = supply.merge(products[["product_id", "category", "brand"]], on="product_id")
    assert (pairs.groupby(["category", "brand"])["supplier_id"].nunique() == 1).all()


def test_suppliers_are_fictional_and_promise_their_mean_lead_time(served):
    suppliers = served["supplier_data"]
    assert suppliers["supplier_name"].is_unique
    assert set(suppliers["country"]) <= set(inv.supplier_origins)
    assert (suppliers["promised_lead_time_days"] == suppliers["true_lead_time_mean_days"].round().clip(lower=1)).all()
    for days in suppliers["order_weekdays"]:
        assert set(days.split(",")) <= {"Mon", "Tue", "Wed", "Thu", "Fri"}


def test_stock_never_goes_below_zero_and_adds_up(served, short):
    for data in (served, short):
        movements = data["stock_movement_data"]
        assert (movements["stock_after"] >= 0).all()
        ordered = movements.sort_values(["product_id", "stock_movement_id"])
        assert (ordered.groupby("product_id")["quantity"].cumsum() == ordered["stock_after"]).all()
        assert movements["stock_movement_id"].is_monotonic_increasing


def test_sales_movements_are_the_order_lines(served, short):
    for data in (served, short):
        lines = data["order_data"].groupby(["product_id", "order_date"])["quantity"].sum()
        sales = data["stock_movement_data"].query("movement_type == 'sale'")
        sold = -sales.set_index(["product_id", "movement_date"])["quantity"]
        pd.testing.assert_series_equal(sold.sort_index(), lines.sort_index(), check_names=False)


def test_receipts_are_the_received_purchase_order_lines(served):
    orders, movements = served["purchase_order_data"], served["stock_movement_data"]
    receipts = movements.query("movement_type == 'receipt'").set_index("purchase_order_line_id")
    received = orders.dropna(subset=["received_date"]).set_index("purchase_order_line_id")
    assert receipts.index.sort_values().tolist() == received.index.sort_values().tolist()
    match = received.loc[receipts.index]
    assert (receipts["quantity"].to_numpy() == match["received_quantity"].to_numpy()).all()
    assert (receipts["movement_date"].to_numpy() == match["received_date"].to_numpy()).all()
    assert (orders["ordered_quantity"] > 0).all()
    supply = served["product_supplier_data"].set_index("product_id")
    assert (orders["ordered_quantity"] % orders["product_id"].map(supply["pack_size"]) == 0).all()


def test_regular_orders_follow_the_supplier(served):
    orders = served["purchase_order_data"].query("~is_express")
    suppliers = served["supplier_data"].set_index("supplier_id")
    received = orders.dropna(subset=["received_date"])
    assert (received["received_date"] > received["order_date"]).all()
    assert (received["received_date"].dt.weekday != 6).all()  # no deliveries on Sunday
    regular = orders[orders["order_date"] >= served["order_data"]["order_date"].min()]
    weekday = regular["order_date"].dt.strftime("%a")
    allowed = regular["supplier_id"].map(suppliers["order_weekdays"])
    launch = regular["product_id"].map(served["product_data"].set_index("product_id")["launch_date"])
    first_line = ~regular.duplicated("product_id")  # the first delivery of a new product comes before its launch
    first_delivery = first_line & (launch > served["order_data"]["order_date"].min())
    assert all(day in days for day, days in zip(weekday[~first_delivery], allowed[~first_delivery], strict=True))
    assert (orders.groupby("purchase_order_id")["supplier_id"].nunique() == 1).all()


def test_express_deliveries_cover_an_empty_shelf_only_with_stockouts_off(served, short):
    assert served["purchase_order_data"]["is_express"].any()
    assert served["lost_demand_data"].empty
    assert not short["purchase_order_data"]["is_express"].any()
    assert not short["lost_demand_data"].empty


def test_lost_lines_are_the_demand_the_stock_could_not_serve(served, short):
    demand = served["order_data"][LINE_KEY]
    kept_and_lost = pd.concat([short["order_data"][LINE_KEY], short["lost_demand_data"][LINE_KEY]])
    key = LINE_KEY
    pd.testing.assert_frame_equal(demand.sort_values(key).reset_index(drop=True),
                                  kept_and_lost.sort_values(key).reset_index(drop=True), check_dtype=False)
    # A lost line did not fit: the product had fewer units left at the end of that day than the line asked for.
    end_stock = stock_by_day(short["stock_movement_data"])
    lost = short["lost_demand_data"]
    moved = set(end_stock.index.get_level_values(0))

    def stock_at_end_of(product, day):
        history = end_stock.loc[product][:day] if product in moved else []
        return history.iloc[-1] if len(history) else 0

    left = [stock_at_end_of(p, day) for p, day in zip(lost["product_id"], lost["order_date"], strict=True)]
    assert (np.asarray(left) < lost["quantity"].to_numpy()).all()


def test_stockouts_keep_the_other_tables_consistent(short):
    lines, sessions = short["order_data"], short["session_data"]
    ids = lines["order_id"].drop_duplicates().to_numpy()
    assert (np.diff(ids) == 1).all()
    assert (np.diff(lines["order_line_id"].to_numpy()) == 1).all()
    linked = sessions["order_id"].dropna()
    assert linked.isin(ids).all() and linked.is_unique
    assert set(lines["order_id"]) == set(linked)
    assert short["shipment_data"]["order_id"].isin(ids).all()
    assert short["return_data"]["order_line_id"].isin(lines["order_line_id"]).all()
    lost = short["lost_demand_data"]
    assert (lost["lost_revenue_gross"] > 0).all()
    assert np.allclose(lost["lost_revenue_gross"],
                       (lost["quantity"] * lost["unit_price_gross"] * (1 - lost["discount_rate"])).round(2))


def test_inventory_settings_change_only_the_new_tables(served):
    changed = generate_with(buyer_cover_days=30, empty_shelf_notice_rate=1.0)
    for name, frame in served.items():
        if name in ("purchase_order_data", "stock_movement_data"):
            assert not changed[name].equals(frame)
        else:
            pd.testing.assert_frame_equal(changed[name], frame)
