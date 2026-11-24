"""
What selling costs the shop beyond the purchase price, in PLN without VAT: the parcel size of every product, what the
carrier charges for a shipment, the return label, handling and goods written off after a return, the payment
operator's fee (payment_data) and the affiliate network's commission.

The rates live in settings.commerce_settings, section Shop costs. Every cost follows from them except the units
written off after a return, drawn from their own random stream ("costs"), so the tables of earlier versions stay
the same and the new columns sit at the end of their tables.
"""
import numpy as np
import pandas as pd

import settings.commerce_settings as cs
import settings.market_settings as ms

PAYMENT_COLUMNS = ["payment_id", "order_id", "payment_amount", "fee_rate", "fixed_fee", "payment_fee"]
SHIPMENT_COST_COLUMNS = ["parcel_size", "carrier_cost"]
RETURN_COST_COLUMNS = ["return_shipping_cost", "handling_cost", "written_off_quantity", "write_off_cost"]
# Columns added in 1.7.0 that reach sales_data through the join; they go to its end so older columns keep their place.
NEW_SALES_COLUMNS = ["affiliate_commission", "parcel_size"]
NOT_SHIPPED = ("cancelled", "payment_failed")


def size_rank(sizes):
    """Position of each parcel size in cs.parcel_sizes (small = 0 ... bulky = 3)."""
    return pd.Series(sizes).map({size: rank for rank, size in enumerate(cs.parcel_sizes)}).to_numpy(dtype=int)


def parcel_size_of_types(product_types, categories):
    """Parcel size by product type and category: bulky types first, then exceptions, then the category size."""
    types = pd.Series(product_types).reset_index(drop=True)
    size = pd.Series(categories).reset_index(drop=True).map(cs.category_parcel_size).fillna(cs.default_parcel_size)
    exception = types.map(cs.product_type_parcel_size)
    size = exception.where(exception.notna(), size)
    return np.where(types.isin(cs.bulky_product_types), "bulky", size.to_numpy()).astype(object)


def add_parcel_size(product_data):
    """Add product_data.parcel_size (small, medium, large or bulky) as the last column."""
    product_data = product_data.copy()
    product_data["parcel_size"] = parcel_size_of_types(product_data["product_type"], product_data["category"])
    return product_data


def line_value_gross(order_data):
    """Value of every order line as paid: quantity × list price on the order day after the line discount."""
    return (order_data["quantity"] * order_data["unit_price_gross"] * (1 - order_data["discount_rate"])).to_numpy()


def build_payment_data(order_data, planned_shipments):
    """
    One payment per order (payment_data): the amount charged at checkout, the operator's rate and fixed fee, and the
    fee itself. Orders paid on delivery have no operator; a failed payment costs the fee of a declined attempt; a
    cancelled cash-on-delivery order was never charged.
    """
    goods = pd.Series(line_value_gross(order_data)).groupby(order_data["order_id"].to_numpy()).sum()
    orders = order_data.drop_duplicates("order_id").set_index("order_id")
    delivery = planned_shipments.set_index("order_id")["shipping_cost"].reindex(orders.index).fillna(0.0)
    amount = np.round(goods.reindex(orders.index).to_numpy() + delivery.to_numpy(), 2)

    method = orders["payment_method"].to_numpy()
    provider = orders["payment_provider"].to_numpy()
    status = orders["order_status"].to_numpy()
    unpaid = orders["payment_status"].eq("unpaid").to_numpy()
    failed = status == "payment_failed"
    no_operator = np.isin(method, cs.methods_without_operator)

    rate = np.array([cs.payment_fee_rate.get(m, cs.default_payment_fee_rate) for m in method], dtype=float)
    fixed = np.array([cs.payment_fixed_fee.get(p, cs.default_payment_fixed_fee) for p in provider], dtype=float)
    declined = np.array([cs.failed_payment_fee.get(m, 0.0) for m in method], dtype=float)
    rate = np.where(failed | no_operator, 0.0, rate)
    fixed = np.where(failed, declined, np.where(no_operator, 0.0, fixed))
    amount = np.where(unpaid, 0.0, amount)

    return pd.DataFrame({
        "payment_id": np.arange(1, len(orders) + 1),
        "order_id": orders.index.to_numpy(),
        "payment_amount": amount,
        "fee_rate": rate,
        "fixed_fee": fixed,
        "payment_fee": np.round(amount * rate + fixed, 2),
    })[PAYMENT_COLUMNS]


def add_shipment_costs(shipment_data, order_data, product_data, payment_data):
    """
    Add shipment_data.parcel_size (the largest product, one size up from parcel_size_step_up_units units, at most
    large unless bulky) and carrier_cost (the carrier's rate for the method and size, plus the collection fee of
    cash on delivery).
    """
    shipment_data = shipment_data.copy()
    sizes = order_data["product_id"].map(product_data.set_index("product_id")["parcel_size"])
    lines = pd.DataFrame({"order_id": order_data["order_id"].to_numpy(), "rank": size_rank(sizes),
                          "quantity": order_data["quantity"].to_numpy()})
    per_order = lines.groupby("order_id").agg(rank=("rank", "max"), units=("quantity", "sum"))
    bulky = len(cs.parcel_sizes) - 1
    step_up = (per_order["units"] >= cs.parcel_size_step_up_units) & (per_order["rank"] < bulky)
    rank = np.where(step_up, np.minimum(per_order["rank"] + 1, bulky - 1), per_order["rank"])
    size = pd.Series(np.asarray(cs.parcel_sizes, dtype=object)[rank], index=per_order.index)
    shipment_data["parcel_size"] = shipment_data["order_id"].map(size).to_numpy()

    method = shipment_data["delivery_method"].to_numpy()
    base = np.array([cs.carrier_rates.get(m, cs.default_carrier_rates)[p]
                     for m, p in zip(method, shipment_data["parcel_size"], strict=True)], dtype=float)
    collected = shipment_data["order_id"].map(payment_data.set_index("order_id")["payment_amount"]).to_numpy()
    payment = shipment_data["order_id"].map(order_data.drop_duplicates("order_id").set_index("order_id")
                                            ["payment_method"]).to_numpy()
    cod = np.isin(payment, cs.methods_without_operator)
    collection = np.where(cod, collected * cs.cod_collection_fee["rate"] + cs.cod_collection_fee["fixed"], 0.0)
    shipment_data["carrier_cost"] = np.round(base + collection, 2)
    return shipment_data


def add_return_costs(return_data, product_data, generator):
    """
    Add the shop's costs of every return: the return label (only for shop-paid reasons), handling, the units that
    cannot be sold again (none for a rejected return) and their purchase cost.
    """
    return_data = return_data.copy()
    products = product_data.set_index("product_id")
    size = return_data["product_id"].map(products["parcel_size"]).to_numpy()
    reason = return_data["return_reason"].to_numpy()
    quantity = return_data["returned_quantity"].to_numpy()

    label = np.array([cs.return_label_rates[p] for p in size], dtype=float)
    shop_pays = np.isin(reason, cs.shop_paid_return_reasons)
    handling = (cs.return_handling_cost["per_return"] + cs.return_handling_cost["per_unit"] * quantity
                + np.where(size == "bulky", cs.return_handling_cost["bulky_extra"], 0.0))
    share = np.array([cs.write_off_share.get(r, cs.default_write_off_share) for r in reason], dtype=float)
    refunded = return_data["return_status"].eq("refunded").to_numpy()
    written_off = generator.binomial(np.where(refunded, quantity, 0), share).astype(np.int64)
    cost = return_data["product_id"].map(products["net_purchase_price"]).to_numpy(dtype=float)

    return_data["return_shipping_cost"] = np.where(shop_pays, label, 0.0)
    return_data["handling_cost"] = np.round(handling, 2)
    return_data["written_off_quantity"] = written_off
    return_data["write_off_cost"] = np.round(written_off * cost, 2)
    return return_data


def add_affiliate_commission(order_data, product_data, return_data):
    """
    Add order_data.affiliate_commission: for affiliate orders that shipped, the category rate times the value
    without VAT of the units the customer kept (refunded units come off); 0 for every other line.
    """
    order_data = order_data.copy()
    category = order_data["product_id"].map(product_data.set_index("product_id")["category"])
    rate = category.map(cs.affiliate_commission_rate).fillna(cs.default_affiliate_commission_rate).to_numpy()
    refunded = return_data.loc[return_data["return_status"] == "refunded"].groupby("order_line_id")[
        "returned_quantity"].sum()
    back = order_data["order_line_id"].map(refunded).fillna(0).to_numpy()
    quantity = order_data["quantity"].to_numpy()
    kept = np.clip(quantity - back, 0, None)
    unit_value = line_value_gross(order_data) / np.where(quantity > 0, quantity, 1)
    eligible = (order_data["channel"].eq("affiliate").to_numpy()
                & ~order_data["order_status"].isin(NOT_SHIPPED).to_numpy())
    commission = rate * kept * unit_value / (1 + ms.vat_rate)
    order_data["affiliate_commission"] = np.where(eligible, np.round(commission, 2), 0.0)
    return order_data
