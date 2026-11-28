"""Markdowns, clearance and the outlet (1.9.0): off by default, on with stockouts."""
import numpy as np
import pandas as pd
import pytest

import func.inventory as inventory
import func.markdowns as markdowns
import settings.inventory_settings as inv
from tests.conftest import generate

LINE_KEY = ["order_date", "customer_id", "quantity", "discount_rate"]


def generate_with(markdowns_on, **changes):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(inv, "stockouts", True)
        mp.setattr(inv, "markdowns", markdowns_on)
        for name, value in changes.items():
            mp.setattr(inv, name, value)
        return generate(customers=3000, products=300, order_lines=30000)


@pytest.fixture(scope="module")
def plain():
    return generate_with(False)


@pytest.fixture(scope="module")
def marked():
    return generate_with(True)


def all_lines(data):
    """Served and lost lines together: the demand before the stock check."""
    keep = ["product_id", *LINE_KEY]
    return pd.concat([data["order_data"][keep], data["lost_demand_data"][keep]], ignore_index=True)


def test_markdowns_need_stockouts():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(inv, "markdowns", True)
        with pytest.raises(ValueError, match="stockouts"):
            inventory.build_inventory(pd.DataFrame(), pd.DataFrame(), [], np.random.default_rng(0), stockouts=False)


def test_off_by_default_the_new_tables_are_empty(small_data, plain):
    assert inv.markdowns is False
    for data in (small_data, plain):
        assert data["markdown_data"].empty and data["outlet_data"].empty
        assert list(data["markdown_data"].columns) == markdowns.MARKDOWN_COLUMNS
        assert list(data["outlet_data"].columns) == markdowns.OUTLET_COLUMNS
        assert not data["price_history"]["change_type"].isin(["markdown", "markdown_end"]).any()


def test_markdowns_have_their_columns_and_prices(marked):
    md = marked["markdown_data"]
    assert list(md.columns) == markdowns.MARKDOWN_COLUMNS
    assert set(md["reason"]) == {"slow_stock", "clearance"}
    assert md["markdown_id"].tolist() == list(range(1, len(md) + 1))
    cents = (md["markdown_price_gross"] * 100).round().astype(int) % 100
    assert (cents == 99).all()
    assert (md["markdown_price_gross"] < md["regular_price_gross"]).all()
    assert np.allclose(md["markdown_rate"], (1 - md["markdown_price_gross"] / md["regular_price_gross"]).round(4))
    uplift = (md["markdown_price_gross"] / md["regular_price_gross"]) ** -md["true_elasticity"]
    assert np.allclose(md["true_uplift"], uplift.round(4))
    ended = md.dropna(subset=["end_date"])
    assert (ended["end_date"] >= ended["start_date"]).all()
    assert set(md["end_reason"]) <= {"planned", "sold_out", "clearance", "withdrawn", "ongoing"}
    assert (md["end_date"].isna() == (md["end_reason"] == "ongoing")).all()


def test_markdowns_of_a_product_never_overlap(marked):
    md = marked["markdown_data"].sort_values(["product_id", "start_date"])
    end = md["end_date"].fillna(pd.Timestamp("2100-01-01"))
    next_start = md.groupby("product_id")["start_date"].shift(-1)
    assert (next_start.isna() | (next_start > end)).all()


def test_clearance_comes_before_withdrawal_and_slow_markdowns_before_it(marked):
    md = marked["markdown_data"].merge(marked["product_data"][["product_id", "launch_date", "discontinued_date"]])
    clearance = md[md["reason"] == "clearance"]
    window = pd.Timedelta(days=inv.clearance_days)
    assert (clearance["start_date"] >= clearance["discontinued_date"] - window).all()
    assert (clearance["end_date"].dropna() < clearance.dropna(subset=["end_date"])["discontinued_date"]).all()
    slow = md[md["reason"] == "slow_stock"]
    assert (slow["start_date"] > slow["launch_date"] + pd.Timedelta(days=inv.markdown_min_age_days)).all()
    assert (slow["discontinued_date"].isna() | (slow["start_date"] < slow["discontinued_date"] - window)).all()


def test_order_lines_carry_the_markdown_price(marked):
    md = marked["markdown_data"].dropna(subset=["end_date"])
    lines = marked["order_data"][["product_id", "order_date", "unit_price_gross"]].merge(md, on="product_id")
    inside = lines[(lines["order_date"] >= lines["start_date"]) & (lines["order_date"] <= lines["end_date"])]
    assert len(inside) > 100
    assert np.allclose(inside["unit_price_gross"], inside["markdown_price_gross"])
    history = marked["price_history"]
    starts = history[history["change_type"] == "markdown"]
    assert len(starts) == len(marked["markdown_data"])
    assert (history.groupby("product_id")["valid_from"].diff().dropna() > pd.Timedelta(0)).all()


def test_markdowns_move_lines_and_never_add_them(plain, marked):
    before, after = all_lines(plain), all_lines(marked)
    pd.testing.assert_frame_equal(before[LINE_KEY].sort_values(LINE_KEY).reset_index(drop=True),
                                  after[LINE_KEY].sort_values(LINE_KEY).reset_index(drop=True), check_dtype=False)
    # Lines switch to marked-down products of their own category first: the lines of each category and day stay
    # nearly as they were, and the lines of each day exactly.
    category = marked["product_data"].set_index("product_id")["category"]

    def per_category_day(lines):
        return lines.assign(category=lines["product_id"].map(category)).groupby(["order_date", "category"]).size()

    pd.testing.assert_series_equal(before.groupby("order_date").size(), after.groupby("order_date").size())
    change = per_category_day(after).sub(per_category_day(before), fill_value=0).abs().sum()
    assert 0 < change <= 0.02 * len(before)
    assert (before.sort_values(LINE_KEY, kind="stable")["product_id"].to_numpy()
            != after.sort_values(LINE_KEY, kind="stable")["product_id"].to_numpy()).any()


def test_demand_rises_by_the_true_uplift(plain, marked):
    """Lines of a marked-down product during its markdown, against its lines on the same days without markdowns."""
    md = marked["markdown_data"].copy()
    md["end_date"] = md["end_date"].fillna(marked["order_data"]["order_date"].max())

    def lines_in_windows(data):
        lines = all_lines(data).groupby(["product_id", "order_date"]).size().rename("lines").reset_index()
        joined = lines.merge(md[["markdown_id", "product_id", "start_date", "end_date"]], on="product_id")
        inside = joined[(joined["order_date"] >= joined["start_date"]) & (joined["order_date"] <= joined["end_date"])]
        return inside.groupby("markdown_id")["lines"].sum().reindex(md["markdown_id"], fill_value=0)

    natural, observed = lines_in_windows(plain).to_numpy(), lines_in_windows(marked).to_numpy()
    expected = (natural * md["true_uplift"].to_numpy()).sum()
    assert natural.sum() > 200
    assert abs(observed.sum() / expected - 1) < 0.10


def test_the_outlet_takes_the_stock_left_on_the_withdrawal_day(marked):
    outlet, movements = marked["outlet_data"], marked["stock_movement_data"]
    assert not outlet.empty
    assert list(outlet.columns) == markdowns.OUTLET_COLUMNS
    products = marked["product_data"].set_index("product_id")
    assert (outlet["sale_date"] >= outlet["product_id"].map(products["discontinued_date"])).all()
    assert np.allclose(outlet["unit_price_net"],
                       (inv.outlet_recovery_rate * outlet["product_id"].map(products["net_purchase_price"])).round(2))
    assert np.allclose(outlet["revenue_net"], (outlet["quantity"] * outlet["unit_price_net"]).round(2))
    to_outlet = movements[movements["movement_type"] == "outlet"]
    assert (to_outlet["stock_after"] == 0).all()
    assert sorted(-to_outlet["quantity"]) == sorted(outlet["quantity"])
    assert (movements["stock_after"] >= 0).all()
    ordered = movements.sort_values(["product_id", "stock_movement_id"])
    assert (ordered.groupby("product_id")["quantity"].cumsum() == ordered["stock_after"]).all()


def test_the_buyer_stops_ordering_before_the_clearance(marked):
    orders = marked["purchase_order_data"].merge(marked["product_data"][["product_id", "discontinued_date"]])
    late = orders["order_date"] >= orders["discontinued_date"] - pd.Timedelta(days=inv.clearance_days)
    assert not late.any()


def test_sales_movements_are_the_order_lines(marked):
    lines = marked["order_data"].groupby(["product_id", "order_date"])["quantity"].sum()
    sales = marked["stock_movement_data"].query("movement_type == 'sale'")
    sold = -sales.set_index(["product_id", "movement_date"])["quantity"]
    pd.testing.assert_series_equal(sold.sort_index(), lines.sort_index(), check_names=False)


def test_markdown_price_ends_in_99_below_the_target():
    assert markdowns.markdown_price(769, 0.2) == 614.99
    assert markdowns.markdown_price(29, 0.1) == 25.99
    assert markdowns.markdown_price(100, 0.5) == 49.99
    assert markdowns.markdown_price(1.5, 0.5) == 0.99
