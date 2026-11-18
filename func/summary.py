"""Short console summaries of the generated tables (command line only; the log is silent unless configured)."""
import logging

import pandas as pd

from func import log


def top_value(data: pd.DataFrame, column: str) -> str:
    """The most common value of a column with its share, e.g. `Card (41.2%)`."""
    shares = data[column].value_counts(normalize=True)
    if shares.empty:
        return "n/a"
    return f"{shares.index[0]} ({shares.iloc[0]:.1%})"


def top_share(values: pd.Series, total: float) -> str:
    """The largest entry of a sorted-or-not Series with its share of total."""
    if values.empty or not total:
        return "n/a"
    values = values.sort_values(ascending=False)
    return f"{values.index[0]} ({values.iloc[0] / total:.1%})"


def date_range(dates: pd.Series) -> str:
    return f"{dates.min():%Y-%m-%d} to {dates.max():%Y-%m-%d}"


def customers(data: pd.DataFrame) -> None:
    log.log_section("Customers")
    log.log_metric("Rows", f"{len(data):,}")
    log.log_metric("Customer IDs", f"{data['customer_id'].min()} to {data['customer_id'].max()}")
    log.log_metric("Age", f"{data['age'].min()} to {data['age'].max()}, mean {data['age'].mean():.1f}")
    log.log_metric("Most common gender", top_value(data, "gender"))
    log.log_metric("Localities", f"{data['city'].nunique():,}")
    log.log_metric("Most common locality", top_value(data, "city"))


def products(data: pd.DataFrame) -> None:
    price = data["sales_price_gross"]
    log.log_section("Products")
    log.log_metric("Rows", f"{len(data):,}")
    log.log_metric("Product IDs", f"{data['product_id'].min()} to {data['product_id'].max()}")
    log.log_metric("Categories / subcategories / types",
                   f"{data['category'].nunique()} / {data['subcategory'].nunique()} / {data['product_type'].nunique()}")
    log.log_metric("Brands", f"{data['brand'].nunique():,}")
    log.log_metric("Most common category", top_value(data, "category"))
    log.log_metric("Gross price", f"mean {price.mean():,.2f} PLN, {price.min():,.2f} to {price.max():,.2f} PLN")
    log.log_metric("Mean margin", f"{data['sales_margin'].mean():.1%}")


def orders(data: pd.DataFrame) -> None:
    log.log_section("Order lines")
    log.log_metric("Rows", f"{len(data):,}")
    log.log_metric("Orders", f"{data['order_id'].nunique():,}")
    log.log_metric("Dates", date_range(data["order_date"]))
    log.log_metric("Customers / products ordered",
                   f"{data['customer_id'].nunique():,} / {data['product_id'].nunique():,}")
    log.log_metric("Lines per order", f"{data.groupby('order_id').size().mean():.2f}")
    log.log_metric("Units per line", f"{data['quantity'].mean():.2f}")
    log.log_metric("Discounted lines", f"{(data['discount_rate'] > 0).mean():.1%}")
    log.log_metric("Most common payment", top_value(data, "payment_method"))
    log.log_metric("Most common delivery", top_value(data, "delivery_method"))


def sales(data: pd.DataFrame) -> None:
    revenue = data["revenue_gross"]
    order_revenue = revenue.groupby(data["order_id"]).sum()
    margin = (data["sales_price_net_after_discount"] - data["net_purchase_price"]) * data["quantity"]
    log.log_section("Sales lines")
    log.log_metric("Rows", f"{len(data):,}")
    log.log_metric("Dates", date_range(data["order_date"]))
    log.log_metric("Gross revenue", f"{revenue.sum():,.2f} PLN")
    log.log_metric("Order value", f"mean {order_revenue.mean():,.2f} PLN, median {order_revenue.median():,.2f} PLN")
    log.log_metric("Top category by revenue", top_share(revenue.groupby(data["category"]).sum(), revenue.sum()))
    log.log_metric("Top category by margin", top_share(margin.groupby(data["category"]).sum(), margin.sum()))


SUMMARIES = {"customer_data": customers, "product_data": products, "order_data": orders, "sales_data": sales}


def log_table(name: str, data: pd.DataFrame) -> None:
    """Log a summary of one generated table (row count only for the extra tables); skipped when nobody listens."""
    if not log.logger.isEnabledFor(logging.INFO):
        return
    if name in SUMMARIES:
        SUMMARIES[name](data)
    else:
        log.log_section(name)
        log.log_metric("Rows", f"{len(data):,}")
