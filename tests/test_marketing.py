"""Pack C: campaigns, channels, devices and web sessions."""
import pandas as pd
import pytest

import settings.marketing_settings as mk
from conftest import generate


@pytest.fixture(scope="module")
def data():
    return generate(customers=3000, products=1500, order_lines=15000)


def test_every_order_has_one_converting_session(data):
    orders, sessions = data["order_data"], data["session_data"]
    converting = sessions.dropna(subset=["order_id"])
    assert converting["order_id"].is_unique
    assert set(converting["order_id"]) == set(orders["order_id"])
    by_session = converting.set_index("order_id")["session_id"]
    assert (orders["session_id"] == orders["order_id"].map(by_session)).all()
    placed = orders.drop_duplicates("order_id").set_index("order_id")["order_datetime"]
    assert (converting["session_start"].to_numpy() < converting["order_id"].map(placed).to_numpy()).all()


def test_conversion_follows_settings(data):
    sessions = data["session_data"]
    for channel, rate in mk.channel_conversion_rates.items():
        group = sessions[sessions["channel"] == channel]
        expected = sum(rate * mk.device_conversion_multipliers[d] * share
                       for d, share in group["device"].value_counts(normalize=True).items())
        assert group["order_id"].notna().mean() == pytest.approx(expected, rel=0.15)


def test_funnel_flags(data):
    sessions = data["session_data"]
    converted = sessions["order_id"].notna()
    assert sessions.loc[converted, ["added_to_cart", "reached_checkout"]].all().all()
    assert not (sessions["reached_checkout"] & ~sessions["added_to_cart"]).any()
    assert (sessions.loc[~converted, "added_to_cart"]).mean() == pytest.approx(mk.non_converting_add_to_cart_share,
                                                                                abs=0.02)


def test_campaigns_and_attribution(data):
    campaigns, orders = data["campaign_data"], data["order_data"].drop_duplicates("order_id")
    assert set(campaigns["channel"]) == set(mk.campaign_plans)
    assert (campaigns["end_date"] >= campaigns["start_date"]).all() and (campaigns["total_cost"] > 0).all()
    credited = orders.dropna(subset=["campaign_id"]).merge(campaigns, on="campaign_id", suffixes=("", "_campaign"))
    assert (credited["channel"] == credited["channel_campaign"]).all()
    assert (credited["order_date"] >= credited["start_date"]).all()
    used = orders.dropna(subset=["voucher_code"]).merge(campaigns, on="campaign_id", suffixes=("", "_campaign"))
    assert (used["voucher_code"] == used["voucher_code_campaign"]).all()


def test_campaign_days_bring_orders_from_their_channel(data):
    campaigns, orders = data["campaign_data"], data["order_data"].drop_duplicates("order_id")
    email_days = set(campaigns.loc[campaigns["channel"] == "email", "start_date"])
    is_email_day = orders["order_date"].isin(email_days)
    share = orders.groupby(is_email_day)["channel"].apply(lambda c: (c == "email").mean())
    assert share[True] > 1.3 * share[False]


def test_new_customers_come_through_their_acquisition_channel(data):
    customers, orders = data["customer_data"], data["order_data"].drop_duplicates("order_id")
    first = orders[~orders["customer_id"].duplicated()].merge(customers, on="customer_id")
    new = first[first["signup_date"] >= pd.Timestamp(2023, 1, 1)]
    assert (new["channel"] == new["acquisition_channel"]).mean() > 0.6
