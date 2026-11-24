"""Shop costs (1.7.0): parcel sizes, carrier costs, return costs, payment fees and affiliate commission."""
import numpy as np
import pandas as pd
import pytest

import func.costs as costs
import settings.commerce_settings as cs
import settings.market_settings as ms
from tests.conftest import generate

NOT_SHIPPED = ["cancelled", "payment_failed"]


def test_new_columns_sit_at_the_end_of_their_tables(small_data):
    assert list(small_data["payment_data"].columns) == costs.PAYMENT_COLUMNS
    assert list(small_data["shipment_data"].columns[-2:]) == costs.SHIPMENT_COST_COLUMNS
    assert list(small_data["return_data"].columns[-4:]) == costs.RETURN_COST_COLUMNS
    assert small_data["order_data"].columns[-1] == "affiliate_commission"
    assert small_data["product_data"].columns[-1] == "parcel_size"
    assert list(small_data["sales_data"].columns[-2:]) == costs.NEW_SALES_COLUMNS


def test_parcel_size_of_products_and_shipments(small_data):
    products, shipments = small_data["product_data"], small_data["shipment_data"]
    assert set(products["parcel_size"]) <= set(cs.parcel_sizes)
    assert (products["parcel_size"].eq("bulky") == products["product_type"].isin(cs.bulky_product_types)).all()
    assert (shipments["parcel_size"].eq("bulky") == shipments["is_bulky"]).all()
    lines = small_data["order_data"].merge(products[["product_id", "parcel_size"]], on="product_id")
    largest = lines.groupby("order_id")["parcel_size"].agg(lambda sizes: costs.size_rank(sizes).max())
    rank = pd.Series(costs.size_rank(shipments["parcel_size"]), index=shipments["order_id"])
    assert (rank >= largest.reindex(rank.index)).all()  # never smaller than the largest product


def test_settings_cover_every_category_method_and_size():
    assert not set(cs.product_type_parcel_size.values()) - {"small", "medium", "large"}  # bulky only from the list
    assert not set(cs.category_parcel_size.values()) - set(cs.parcel_sizes)
    for rates in list(cs.carrier_rates.values()) + [cs.default_carrier_rates, cs.return_label_rates]:
        assert set(rates) == set(cs.parcel_sizes)
    assert set(cs.carrier_rates) == set(cs.delivery_methods)
    assert set(cs.payment_fee_rate) == set(ms.payment_method_with_probabilities)
    assert set(cs.payment_fixed_fee) == set(ms.payment_provider_with_probabilities)


def test_carrier_cost_follows_the_rates_and_free_delivery_still_costs(small_data):
    shipments, orders = small_data["shipment_data"], small_data["order_data"].drop_duplicates("order_id")
    payments = small_data["payment_data"].set_index("order_id")
    method = shipments["order_id"].map(orders.set_index("order_id")["payment_method"])
    base = [cs.carrier_rates[m][p] for m, p in zip(shipments["delivery_method"], shipments["parcel_size"], strict=True)]
    cod = method.eq("COD").to_numpy()
    collection = np.where(cod, shipments["order_id"].map(payments["payment_amount"]) * cs.cod_collection_fee["rate"]
                          + cs.cod_collection_fee["fixed"], 0.0)
    assert np.allclose(shipments["carrier_cost"], np.round(np.array(base) + collection, 2), atol=0.005)
    assert (shipments.loc[shipments["shipping_cost"] == 0, "carrier_cost"] > 0).all()


def test_one_payment_per_order_with_its_fee(small_data):
    orders = small_data["order_data"].drop_duplicates("order_id").set_index("order_id")
    pay = small_data["payment_data"].set_index("order_id")
    assert pay.index.is_unique and set(pay.index) == set(orders.index)
    assert np.allclose(pay["payment_fee"], np.round(pay["payment_amount"] * pay["fee_rate"] + pay["fixed_fee"], 2))
    joined = pay.join(orders[["payment_method", "payment_provider", "order_status", "payment_status"]])
    paid = joined[~joined["order_status"].eq("payment_failed") & ~joined["payment_method"].isin(["COD"])]
    assert (paid["fee_rate"] == paid["payment_method"].map(cs.payment_fee_rate)).all()
    assert (paid["fixed_fee"] == paid["payment_provider"].map(cs.payment_fixed_fee)).all()
    cod = joined[joined["payment_method"].eq("COD")]
    assert (cod["payment_fee"] == 0).all()
    failed = joined[joined["order_status"].eq("payment_failed")]
    assert (failed["fee_rate"] == 0).all()
    assert (failed["payment_fee"] == failed["payment_method"].map(cs.failed_payment_fee).fillna(0.0)).all()
    assert (joined.loc[joined["payment_status"].eq("unpaid"), "payment_amount"] == 0).all()

    lines = small_data["order_data"]
    goods = (lines["quantity"] * lines["unit_price_gross"] * (1 - lines["discount_rate"])).groupby(
        lines["order_id"]).sum()
    shipped = small_data["shipment_data"].set_index("order_id")["shipping_cost"]
    delivered = pay.index[pay.index.isin(shipped.index)]
    assert np.allclose(pay.loc[delivered, "payment_amount"], (goods + shipped).loc[delivered].round(2), atol=0.005)


def test_return_costs(small_data):
    returns = small_data["return_data"]
    products = small_data["product_data"].set_index("product_id")
    shop_pays = returns["return_reason"].isin(cs.shop_paid_return_reasons)
    assert (returns.loc[~shop_pays, "return_shipping_cost"] == 0).all()
    size = returns["product_id"].map(products["parcel_size"])
    assert (returns.loc[shop_pays, "return_shipping_cost"] == size[shop_pays].map(cs.return_label_rates)).all()
    handling = cs.return_handling_cost
    assert (returns["handling_cost"] >= handling["per_return"] + handling["per_unit"]).all()
    assert returns["written_off_quantity"].between(0, returns["returned_quantity"]).all()
    assert (returns.loc[returns["return_status"].eq("rejected"), "written_off_quantity"] == 0).all()
    cost = returns["written_off_quantity"] * returns["product_id"].map(products["net_purchase_price"])
    assert np.allclose(returns["write_off_cost"], cost.round(2), atol=0.005)


def test_affiliate_commission_only_on_kept_affiliate_units(small_data):
    lines = small_data["order_data"]
    others = ~lines["channel"].eq("affiliate") | lines["order_status"].isin(NOT_SHIPPED)
    assert (lines.loc[others, "affiliate_commission"] == 0).all()
    refunded = small_data["return_data"].query("return_status == 'refunded'").groupby("order_line_id")[
        "returned_quantity"].sum()
    kept = lines["quantity"] - lines["order_line_id"].map(refunded).fillna(0)
    category = lines["product_id"].map(small_data["product_data"].set_index("product_id")["category"])
    rate = category.map(cs.affiliate_commission_rate).fillna(cs.default_affiliate_commission_rate)
    expected = (rate * kept * lines["unit_price_gross"] * (1 - lines["discount_rate"]) / (1 + ms.vat_rate)).round(2)
    assert np.allclose(lines.loc[~others, "affiliate_commission"], expected[~others], atol=0.005)
    assert (lines.loc[~others, "affiliate_commission"] > 0).any()


@pytest.fixture(scope="module")
def changed_costs():
    """The same run with every unit of a refunded return written off and no shop-paid labels."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cs, "write_off_share", {})
        mp.setattr(cs, "default_write_off_share", 1.0)
        mp.setattr(cs, "shop_paid_return_reasons", [])
        return generate()


def test_cost_settings_change_only_the_cost_columns(small_data, changed_costs):
    for name, frame in small_data.items():
        old = [column for column in frame.columns if column not in costs.RETURN_COST_COLUMNS]
        pd.testing.assert_frame_equal(changed_costs[name][old], frame[old])
    returns = changed_costs["return_data"]
    refunded = returns["return_status"].eq("refunded")
    assert (returns.loc[refunded, "written_off_quantity"] == returns.loc[refunded, "returned_quantity"]).all()
    assert (returns["return_shipping_cost"] == 0).all()
    assert not returns["written_off_quantity"].equals(small_data["return_data"]["written_off_quantity"])
