"""Order status (cancellations, failed payments), reviews and the churn truth of customers."""
import pandas as pd
import pytest
from conftest import generate

import func.charts as ch
import settings.commerce_settings as cs
import settings.localization as loc
import settings.quality_settings as qs

STATUSES = {"delivered", "returned", "cancelled", "payment_failed"}
NOT_SHIPPED = ["cancelled", "payment_failed"]
PAYMENT_OF_STATUS = {"delivered": {"paid"}, "returned": {"refunded"}, "payment_failed": {"failed"},
                     "cancelled": {"refunded", "unpaid"}}


@pytest.fixture(scope="module")
def data():
    return generate(customers=3000, products=1500, order_lines=15000)


def orders_of(data):
    return data["order_data"].drop_duplicates("order_id").set_index("order_id")


def experience(data):
    """on_time, late or defect of every reviewed line, measured from shipments and returns."""
    reviews, shipments, returns = data["review_data"], data["shipment_data"], data["return_data"]
    late = reviews["order_id"].map(shipments.set_index("order_id")["is_late"]).astype(bool)
    defect = reviews["order_line_id"].isin(
        returns.loc[returns["return_reason"].isin(cs.defect_return_reasons), "order_line_id"])
    return pd.Series("on_time", index=reviews.index).mask(late, "late").mask(defect, "defect")


# Order status --------------------------------------------------------------------------------------------------- #

def test_order_status_is_one_per_order_and_matches_the_payment(data):
    lines, orders = data["order_data"], orders_of(data)
    assert set(lines["order_status"]) == STATUSES
    columns = ["order_status", "payment_status", "cancel_reason", "cancelled_at"]
    assert (lines.groupby("order_id")[columns].nunique(dropna=False) == 1).all().all()
    for status, payments in PAYMENT_OF_STATUS.items():
        assert set(orders.loc[orders["order_status"] == status, "payment_status"]) <= payments
    cod = orders[(orders["order_status"] == "cancelled") & (orders["payment_method"] == "COD")]
    assert (cod["payment_status"] == "unpaid").all()


def test_cancelled_and_failed_orders_never_ship_return_or_get_reviewed(data):
    lost = orders_of(data).query("order_status in @NOT_SHIPPED").index
    assert len(lost) > 0
    assert not data["shipment_data"]["order_id"].isin(lost).any()
    assert not data["return_data"]["order_id"].isin(lost).any()
    assert not data["review_data"]["order_id"].isin(lost).any()


def test_only_cancelled_orders_have_a_reason_and_a_cancel_time_after_the_order(data):
    orders = orders_of(data)
    cancelled = orders[orders["order_status"] == "cancelled"]
    assert cancelled["cancel_reason"].isin(list(cs.cancel_reasons)).all()
    assert (cancelled["cancelled_at"] > cancelled["order_datetime"]).all()
    assert (cancelled["cancelled_at"] - cancelled["order_datetime"] < pd.Timedelta(days=7)).all()
    others = orders[orders["order_status"] != "cancelled"]
    assert others["cancel_reason"].isna().all() and others["cancelled_at"].isna().all()


def test_payment_failures_follow_the_payment_method_and_spare_fraud(data):
    orders = orders_of(data)
    failed = orders.groupby("payment_method")["order_status"].apply(lambda status: (status == "payment_failed").mean())
    assert failed["Deferred payment"] > 3 * failed["BLIK"]
    assert failed.get("COD", 0) == 0
    assert (orders.loc[orders["is_fraud"], "order_status"].isin(["delivered", "returned"])).all()


def test_returned_orders_came_back_in_full_and_were_refunded(data):
    lines, returns = data["order_data"], data["return_data"]
    refunded = returns[returns["return_status"] == "refunded"].set_index("order_line_id")["returned_quantity"]
    full = lines["order_line_id"].map(refunded).fillna(0) >= lines["quantity"]
    all_back = full.groupby(lines["order_id"]).all()
    orders = orders_of(data)
    returned = orders.index[orders["order_status"] == "returned"]
    assert len(returned) > 0 and all_back[returned].all()
    delivered = orders.index[orders["order_status"] == "delivered"]
    assert not all_back[delivered].any()


def test_cancelled_orders_bring_no_revenue(data):
    sales = data["sales_data"]
    paid = ch.realised(sales)
    assert not paid["order_status"].isin(NOT_SHIPPED).any()
    assert len(paid) < len(sales)
    assert ch.headline_numbers(data)["revenue"] == pytest.approx(paid["revenue_gross"].sum())


def test_status_settings_decide_the_status(monkeypatch):
    monkeypatch.setattr(cs, "payment_failure_rate", {})
    monkeypatch.setattr(cs, "default_payment_failure_rate", 0.0)
    monkeypatch.setattr(cs, "cancellation_rate", 0.0)
    calm = generate()
    assert set(calm["order_data"]["order_status"]) <= {"delivered", "returned"}
    assert calm["shipment_data"]["order_id"].nunique() == calm["order_data"]["order_id"].nunique()
    monkeypatch.setattr(cs, "cancellation_rate", 1.0)
    cancelled = generate()
    orders = orders_of(cancelled)
    assert (orders.loc[~orders["is_fraud"], "order_status"] == "cancelled").all()
    assert set(cancelled["shipment_data"]["order_id"]) == set(orders.index[orders["is_fraud"]])
    assert not cancelled["review_data"]["order_id"].isin(orders.index[~orders["is_fraud"]]).any()


# Reviews -------------------------------------------------------------------------------------------------------- #

def test_reviews_rate_delivered_lines_after_delivery(data):
    reviews, lines, shipments = data["review_data"], data["order_data"], data["shipment_data"]
    assert len(reviews) > 0 and reviews["review_id"].is_unique and reviews["order_line_id"].is_unique
    assert reviews["review_score"].between(1, 5).all()
    line = lines.set_index("order_line_id").loc[reviews["order_line_id"]]
    for column in ("order_id", "product_id", "customer_id"):
        assert (line[column].to_numpy() == reviews[column].to_numpy()).all()
    assert line["order_status"].isin(["delivered", "returned"]).all() and not line["is_fraud"].any()
    delivered = reviews["order_id"].map(shipments.set_index("order_id")["delivered_at"]).dt.normalize()
    assert (reviews["review_date"] > delivered).all()
    sentences = {sentence for group in cs.review_comments.values() for sentence in group}
    assert set(reviews["review_comment"].dropna()) <= sentences
    assert reviews["review_comment"].isna().any()


def test_late_deliveries_and_defects_lower_the_rating(data):
    mean = data["review_data"].groupby(experience(data))["review_score"].mean()
    assert mean["on_time"] - mean["late"] > 0.5
    assert mean["late"] - mean["defect"] > 0.5


def test_bad_experiences_get_reviewed_more_often(data):
    lines = data["order_data"][data["order_data"]["order_id"].isin(data["shipment_data"]["order_id"])]
    late_lines = lines["order_id"].map(data["shipment_data"].set_index("order_id")["is_late"]).astype(bool)
    reviewed = lines["order_line_id"].isin(data["review_data"]["order_line_id"])
    assert reviewed[late_lines].mean() > 1.3 * reviewed[~late_lines].mean()


def test_low_ratings_after_a_bad_experience_name_the_cause(data):
    reviews = data["review_data"].assign(experience=experience(data))
    late = reviews.query("experience == 'late' and review_score <= 4")["review_comment"].dropna()
    assert len(late) > 0 and late.isin(cs.review_comments["late"]).all()
    defect = reviews.query("experience == 'defect' and review_score <= 3")["review_comment"].dropna()
    assert len(defect) > 0 and defect.isin(cs.review_comments["defect"]).all()


def test_rating_settings_are_the_truth(monkeypatch):
    same = {5: 0.5, 4: 0.2, 3: 0.1, 2: 0.1, 1: 0.1}
    monkeypatch.setattr(cs, "review_score_weights", {"on_time": same, "late": same, "defect": same})
    flat = generate(customers=3000, products=1500, order_lines=15000)
    mean = flat["review_data"].groupby(experience(flat))["review_score"].mean()
    assert abs(mean["on_time"] - mean["late"]) < 0.3  # without the setting, a late delivery costs no stars


def test_the_defective_batch_shows_in_the_ratings(monkeypatch):
    monkeypatch.setattr(cs, "return_spike_days", 400)
    data = generate(customers=3000, products=1500, order_lines=15000)
    spike = data["anomaly_data"].query("anomaly_type == 'return_spike'").iloc[0]
    product = int(spike["description"].split("product ")[1].split(":")[0])
    reviews = data["review_data"][data["review_data"]["product_id"] == product]
    ordered = reviews["order_line_id"].map(data["order_data"].set_index("order_line_id")["order_date"])
    inside = ordered.between(spike["start_date"], spike["end_date"])
    assert inside.sum() >= 5 and (~inside).sum() >= 1
    assert reviews.loc[inside, "review_score"].mean() < 2.5 < reviews.loc[~inside, "review_score"].mean()


def test_review_comments_are_translated_to_polish():
    pl = generate(language="pl")["review_data"]["review_comment"].dropna()
    translated = set(loc.translations["pl"]["review_comment"].values())
    assert len(pl) > 0 and set(pl) <= translated
    sentences = {sentence for group in cs.review_comments.values() for sentence in group}
    assert sentences == set(loc.translations["pl"]["review_comment"])


# Churn truth ---------------------------------------------------------------------------------------------------- #

def test_churn_truth_columns_are_complete(data):
    customers = data["customer_data"]
    assert customers["true_churn_date"].notna().all() and (customers["true_purchase_rate"] >= 0).all()
    assert (customers["true_churn_date"] >= customers["signup_date"]).all()
    one_time = customers["customer_segment"] == "one_time"
    assert (customers.loc[one_time, "true_purchase_rate"] == 0).all()
    assert (customers.loc[~one_time, "true_purchase_rate"] > 0).all()


def test_nobody_orders_after_their_true_churn_date(data):
    orders = orders_of(data)
    legit = orders[~orders["is_fraud"]]
    churn = legit["customer_id"].map(data["customer_data"].set_index("customer_id")["true_churn_date"])
    assert ((legit["order_date"] - churn).dt.days <= qs.outage_recovery_days).all()


def test_one_time_buyers_order_once(data):
    orders = orders_of(data)
    one_time = data["customer_data"].loc[data["customer_data"]["customer_segment"] == "one_time", "customer_id"]
    legit = orders[~orders["is_fraud"] & orders["customer_id"].isin(one_time)]
    assert legit.groupby("customer_id").size().max() == 1


def test_true_purchase_rate_predicts_repeat_orders(data):
    customers = data["customer_data"].set_index("customer_id")
    orders = orders_of(data)
    legit = orders[~orders["is_fraud"]]
    start, end = pd.Timestamp(2023, 1, 1), pd.Timestamp(2024, 12, 31)
    first = legit.groupby("customer_id")["order_date"].min().reindex(customers.index)
    count = legit.groupby("customer_id").size().reindex(customers.index, fill_value=0)
    existing = customers["signup_date"] < start
    years = ((customers["true_churn_date"].clip(upper=end) - first.where(~existing, start)).dt.days.clip(lower=0)
             + existing.astype(int)) / 365
    repeats = (count - (~existing).astype(int)).clip(lower=0)
    active = existing | first.notna()
    assert repeats[active].sum() / (customers["true_purchase_rate"] * years)[active].sum() == pytest.approx(1, abs=0.1)
    heavy = customers["true_purchase_rate"] > customers["true_purchase_rate"].median()
    per_year = repeats / years.where(years > 0.25)
    assert per_year[heavy & active].mean() > 2 * per_year[~heavy & active].mean()
