import pandas as pd

import func.generator as g
import settings.main_settings as s
import settings.product_catalog as pc

CUSTOMER_COLUMNS = {
    "customer_id", "age", "gender", "first_name", "last_name", "email",
    "phone_number", "bank_account_number", "postal_code", "city",
}
ORDER_COLUMNS = {
    "order_id", "order_date", "product_id", "quantity", "customer_id",
    "payment_method", "payment_provider", "delivery_method", "discount_rate",
}


def test_all_datasets_are_generated(small_data):
    assert list(small_data) == g.DATASET_NAMES


def test_customer_data(small_data):
    customers = small_data["customer_data"]
    assert len(customers) == 300
    assert CUSTOMER_COLUMNS <= set(customers.columns)
    assert customers["customer_id"].is_unique
    assert customers["email"].is_unique
    assert customers["email"].str.fullmatch(r"[a-z0-9.\-]+@example\.(com|org|net)").all()
    assert customers["age"].between(18, 65).all()
    assert set(customers["gender"]) <= {"Male", "Female"}
    assert customers["postal_code"].str.fullmatch(r"\d{2}-\d{3}").all()
    assert customers["city"].notna().all()
    assert customers["bank_account_number"].str.fullmatch(r"PL\d{26}").all()


def test_product_data(small_data):
    products = small_data["product_data"]
    assert len(products) == 400
    assert products["product_id"].is_unique
    assert (products["net_purchase_price"] > 0).all()
    assert (products["sales_price_net"] > products["net_purchase_price"]).all()
    assert (products["sales_price_gross"] % 10 == 9).all()
    expected_name = products[["product_type", "brand", "product_series", "product_model"]].agg(" ".join, axis=1)
    assert (products["product_name"] == expected_name).all()


def test_prices_and_margins_follow_catalog(small_data):
    products = small_data["product_data"]
    for row in products.itertuples():
        definition = pc.product_catalog[row.category][row.product_type]
        low_price, high_price = definition["price_range"]
        low_margin, high_margin = definition["margin_range"]
        assert low_price <= row.net_purchase_price <= high_price
        assert low_margin <= row.sales_margin <= high_margin
        assert row.brand in definition["brand_series_models"]


def test_order_data(small_data):
    orders = small_data["order_data"]
    assert ORDER_COLUMNS <= set(orders.columns)
    assert len(orders) >= 1200
    first_day, last_day = pd.Timestamp(s.start_year, 1, 1), pd.Timestamp(s.end_year, 12, 31)
    assert orders["order_date"].between(first_day, last_day).all()
    assert orders["quantity"].between(1, 5).all()
    assert orders["discount_rate"].between(0, 0.45).all()
    assert orders["order_date"].is_monotonic_increasing


def test_order_ids_are_consecutive_and_consistent(small_data):
    orders = small_data["order_data"]
    order_ids = orders["order_id"].drop_duplicates()
    assert order_ids.tolist() == list(range(100001, 100001 + len(order_ids)))
    shared = ["order_date", "customer_id", "payment_method", "payment_provider", "delivery_method"]
    assert (orders.groupby("order_id")[shared].nunique() == 1).all().all()
    assert orders.groupby("order_id").size().max() <= max(s.order_line_number)


def test_sales_data_joins_and_revenue(small_data):
    sales = small_data["sales_data"]
    customers = small_data["customer_data"]
    products = small_data["product_data"]
    assert len(sales) == len(small_data["order_data"])
    assert sales["customer_id"].isin(customers["customer_id"]).all()
    assert sales["product_id"].isin(products["product_id"]).all()
    assert sales[["city", "product_name", "sales_price_gross"]].notna().all().all()
    expected = sales["quantity"] * sales["sales_price_gross"] * (1 - sales["discount_rate"])
    pd.testing.assert_series_equal(sales["revenue_gross"], expected, check_names=False)
