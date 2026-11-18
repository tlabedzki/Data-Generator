"""
Ratings of delivered order lines (review_data): 1 to 5 stars, lower and more frequent after a late delivery or a
defect (settings.commerce_settings, section Reviews, holds the true effect).
"""
import numpy as np
import pandas as pd

import settings.commerce_settings as cs

REVIEW_COLUMNS = ["review_id", "order_id", "order_line_id", "product_id", "customer_id", "review_date",
                  "review_score", "review_comment"]
EXPERIENCES = ["on_time", "late", "defect"]


def empty_review_data():
    types = {"review_id": "int64", "order_id": "int64", "order_line_id": "int64", "product_id": "int64",
             "customer_id": "int64", "review_date": "datetime64[ns]", "review_score": "int64",
             "review_comment": "object"}
    return pd.DataFrame({column: pd.Series(dtype=types[column]) for column in REVIEW_COLUMNS})


def line_experience(lines, shipments, return_data, spikes):
    """on_time, late or defect for every line (defect wins over late)."""
    late = lines["order_id"].map(shipments.set_index("order_id")["is_late"]).fillna(False).to_numpy(dtype=bool)
    defective = return_data.loc[return_data["return_reason"].isin(cs.defect_return_reasons), "order_line_id"]
    defect = lines["order_line_id"].isin(defective).to_numpy()
    for spike in spikes:
        if spike.get("anomaly_type") != "return_spike" or spike.get("product_id") is None:
            continue
        defect |= ((lines["product_id"] == spike["product_id"]).to_numpy()
                   & lines["order_date"].between(spike["start_date"], spike["end_date"]).to_numpy())
    return np.where(defect, "defect", np.where(late, "late", "on_time"))


def comment_group(score, experience):
    """Which ready sentences fit a rating: the cause for low ratings after a bad experience, else the tone."""
    return np.where((experience == "defect") & (score <= 3), "defect",
                    np.where((experience == "late") & (score <= 4), "late",
                             np.where(score >= 4, "positive", np.where(score == 3, "neutral", "negative"))))


def build_reviews(order_data, shipments, return_data, spikes, generator):
    """
    Draw the reviews of order lines that reached the customer (not cancelled, not failed, not fraud).

    Parameters:
    order_data (pd.DataFrame): Order lines with order_status and is_fraud.
    shipments (pd.DataFrame): Shipments of the orders that shipped (delivered_at, is_late).
    return_data (pd.DataFrame): Returned lines with return_reason.
    spikes (list): Anomaly records; the return_spike ones mark a defective batch.
    generator (np.random.Generator): Random stream.

    Returns:
    pd.DataFrame: One row per review, oldest first.
    """
    reached = order_data["order_id"].isin(shipments["order_id"]).to_numpy()
    if "is_fraud" in order_data:
        reached &= ~order_data["is_fraud"].to_numpy(dtype=bool)
    lines = order_data[reached]
    if lines.empty:
        return empty_review_data()
    experience = line_experience(lines, shipments, return_data, spikes)
    rate = pd.Series(cs.review_rate).reindex(experience).to_numpy(dtype=float)
    reviewed = generator.random(len(lines)) < rate
    lines, experience = lines[reviewed], experience[reviewed]
    count = len(lines)

    score = np.zeros(count, dtype=np.int64)
    u = generator.random(count)
    for name in EXPERIENCES:
        slots = experience == name
        weights = cs.review_score_weights[name]
        stars = np.array(sorted(weights))
        p = np.array([weights[star] for star in stars], dtype=float)
        score[slots] = stars[np.minimum(np.searchsorted(np.cumsum(p / p.sum()), u[slots]), len(stars) - 1)]

    delivered = lines["order_id"].map(shipments.set_index("order_id")["delivered_at"]).dt.normalize()
    delay = generator.geometric(1 / max(cs.review_delay_mean_days, 1), size=count)
    review_date = delivered + pd.to_timedelta(delay, unit="D")

    with_comment = generator.random(count) < pd.Series(cs.review_comment_share).reindex(experience).to_numpy(float)
    group = comment_group(score, experience)
    pick = generator.random(count)
    comment = np.full(count, None, dtype=object)
    for name, sentences in cs.review_comments.items():
        slots = with_comment & (group == name)
        comment[slots] = np.asarray(sentences, dtype=object)[(pick[slots] * len(sentences)).astype(int)]

    reviews = pd.DataFrame({
        "order_id": lines["order_id"].to_numpy(),
        "order_line_id": lines["order_line_id"].to_numpy(),
        "product_id": lines["product_id"].to_numpy(),
        "customer_id": lines["customer_id"].to_numpy(),
        "review_date": pd.to_datetime(review_date.to_numpy()),
        "review_score": score,
        "review_comment": comment,
    }).sort_values(["review_date", "order_line_id"], kind="stable").reset_index(drop=True)
    reviews.insert(0, "review_id", np.arange(1, len(reviews) + 1))
    return reviews[REVIEW_COLUMNS]
