"""Every net price is the gross price without VAT: gross / net = 1 + vat_rate, to the grosz (fixed in 1.7.1)."""
import pandas as pd

import settings.market_settings as ms

GROSS_NET = {
    "product_data": ("sales_price_gross", "sales_price_net"),
    "price_history": ("sales_price_gross", "sales_price_net"),
    "order_data": ("unit_price_gross", "unit_price_net"),
    "sales_data": ("sales_price_gross_after_discount", "sales_price_net_after_discount"),
    "competitor_prices": ("price_gross", "price_net"),
}


def vat_mismatches(frame: pd.DataFrame, gross: str, net: str) -> int:
    """Rows whose net price is more than half a grosz away from gross / (1 + vat_rate)."""
    return int(((frame[gross] / (1 + ms.vat_rate) - frame[net]).abs() > 0.005 + 1e-9).sum())


def test_every_net_price_is_the_gross_price_without_vat(small_data):
    for table, (gross, net) in GROSS_NET.items():
        assert vat_mismatches(small_data[table], gross, net) == 0, table
    sales = small_data["sales_data"]
    assert vat_mismatches(sales, "unit_price_gross", "unit_price_net") == 0
    assert vat_mismatches(sales, "sales_price_gross", "sales_price_net") == 0


def test_a_broken_net_price_is_caught(small_data):
    broken = small_data["order_data"].copy()
    broken.loc[broken.index[0], "unit_price_net"] += 0.02
    assert vat_mismatches(broken, "unit_price_gross", "unit_price_net") == 1


def test_the_margin_is_the_margin_of_the_net_list_price(small_data):
    products = small_data["product_data"]
    margin = (1 - products["net_purchase_price"] / products["sales_price_net"]).round(4)
    assert (products["sales_margin"] == margin).all()
