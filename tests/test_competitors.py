"""
Competitor prices: five shops, validity periods, price level and coverage per shop, the matcher, the flash sale shop
and no effect on other tables.
"""
import numpy as np
import pandas as pd
import pytest
from conftest import ALL_FILES, generate

import func.calendar as fc
import func.competitors as cp
import settings.main_settings as s
import settings.market_settings as ms

END = pd.Timestamp(s.end_year, 12, 31)


@pytest.fixture(scope="module")
def data():
    return generate(customers=300, products=4000, order_lines=1500)


@pytest.fixture(scope="module")
def offers(data):
    return data["competitor_prices"]


def prices_on(offers, day):
    return offers[(offers["valid_from"] <= day) & (offers["valid_to"].isna() | (offers["valid_to"] >= day))]


def flash_shop():
    return next((key, value) for key, value in ms.competitor_settings.items() if "sale_events_per_year" in value)


def test_five_shops_with_different_names_and_strategies(offers):
    shops = ms.competitor_settings.values()
    assert len(ms.competitor_settings) == 5
    assert len({shop["name"] for shop in shops}) == 5
    assert len({shop["strategy"] for shop in shops}) == 5
    assert offers["competitor_id"].nunique() == 5 and offers["competitor_name"].nunique() == 5
    assert {shop["strategy"] for shop in shops} == {"discounter", "matcher", "premium", "marketplace", "flash_sale"}


def test_columns_and_keys(offers, data):
    assert list(offers.columns) == cp.COMPETITOR_COLUMNS
    assert offers["competitor_price_id"].tolist() == list(range(1, len(offers) + 1))
    assert offers["product_id"].isin(data["product_data"]["product_id"]).all()
    assert set(offers["competitor_id"]) == set(ms.competitor_settings)
    names = {shop_id: shop["name"] for shop_id, shop in ms.competitor_settings.items()}
    assert (offers["competitor_name"] == offers["competitor_id"].map(names)).all()
    assert set(offers["change_type"]) == {"initial", "increase", "decrease"}


def test_periods_are_continuous_and_do_not_overlap(offers):
    offer = offers.groupby(["product_id", "competitor_id"])
    gap = (offers["valid_from"] - offer["valid_to"].shift()).dt.days.dropna()
    assert (gap == 1).all()
    assert (offers["valid_to"].isna() | (offers["valid_to"] >= offers["valid_from"])).all()
    first = offers.drop_duplicates(["product_id", "competitor_id"])
    assert (first["change_type"] == "initial").all()
    assert (offers.loc[~offers.index.isin(first.index), "change_type"] != "initial").all()


def test_one_open_period_for_offers_active_at_the_end(offers, data):
    products = data["product_data"].set_index("product_id")
    last = offers.groupby(["product_id", "competitor_id"]).tail(1)
    discontinued = last["product_id"].map(products["discontinued_date"])
    assert (last["valid_to"].isna() == discontinued.isna()).all()
    assert (last["valid_to"].dropna() == discontinued.dropna()).all()
    assert offers.groupby(["product_id", "competitor_id"])["valid_to"].apply(lambda to: to.isna().sum()).max() == 1


def test_offers_stay_inside_the_selling_period(offers, data):
    products = data["product_data"].set_index("product_id")
    launch = offers["product_id"].map(products["launch_date"]).clip(lower=pd.Timestamp(s.start_year, 1, 1))
    first = offers.drop_duplicates(["product_id", "competitor_id"])
    assert (first["valid_from"] == launch[first.index]).all()
    assert (offers["valid_from"] <= END).all()


def test_prices_are_positive_with_the_shop_ending(offers):
    assert ((offers["price_gross"] > offers["price_net"]) & (offers["price_net"] > 0)).all()
    cents = np.round(offers["price_gross"] * 100).astype(int) % 100
    for shop_id, shop in ms.competitor_settings.items():
        mine = offers["competitor_id"] == shop_id
        if shop["price_ending"] == "99":
            assert (cents[mine] == 99).all()
        else:
            whole = mine & (offers["price_gross"] >= cp.CHEAP_PRICE_GROSS)
            assert (cents[whole] == 0).all() and (offers.loc[whole, "price_gross"] % 10 == 9).all()


def test_net_price_uses_the_vat_of_the_product(offers, data):
    products = data["product_data"].set_index("product_id")
    vat = offers["product_id"].map(products["sales_price_gross"] / products["sales_price_net"])
    assert np.allclose(offers["price_net"], offers["price_gross"] / vat, atol=0.006)


@pytest.mark.parametrize("day", [pd.Timestamp(s.start_year, 1, 1), pd.Timestamp(s.end_year, 6, 30), END])
def test_shop_price_level_matches_its_truth(offers, day):
    current = prices_on(offers, day)
    current = current[~current["is_promotion"]]
    ratio = current["price_gross"] / current["true_market_price_gross"]
    level = ratio.groupby(current["competitor_id"]).mean()
    truth = current.groupby("competitor_id")["true_price_level"].first()
    assert (level - truth).abs().max() <= 0.02


def test_market_price_comes_from_cost(offers, data):
    products = data["product_data"]
    vat = products["sales_price_gross"] / products["sales_price_net"]
    market = pd.Series((cp.market_reference(products) * vat).round(2).to_numpy(), index=products["product_id"])
    assert np.allclose(offers["true_market_price_gross"], offers["product_id"].map(market))
    assert (offers.groupby("product_id")["true_market_price_gross"].nunique() == 1).all()


def test_coverage_per_shop_matches_settings(offers, data):
    coverage = offers.groupby("competitor_id")["product_id"].nunique() / len(data["product_data"])
    for shop_id, shop in ms.competitor_settings.items():
        assert abs(coverage[shop_id] - shop["coverage"]) <= 0.03


def test_our_price_is_sometimes_above_and_sometimes_below_the_competitors(offers, data):
    median = prices_on(offers, END).groupby("product_id")["price_gross"].median()
    index = (data["product_data"].set_index("product_id")["sales_price_gross"] / median).dropna()
    assert index.between(0.8, 1.25).mean() >= 0.85
    assert (index < 0.95).mean() >= 0.15 and (index > 1.05).mean() >= 0.15


def test_matcher_follows_our_price_changes(offers, data):
    shop_id, shop = next((key, value) for key, value in ms.competitor_settings.items() if "reaction_probability"
                         in value)
    low, high = shop["reaction_delay_days"]
    history = data["price_history"]
    ours = history[history["change_type"] != "initial"]
    changes = offers[(offers["competitor_id"] == shop_id) & (offers["change_type"] != "initial")]
    pairs = changes.merge(ours[["product_id", "valid_from"]], on="product_id", suffixes=("", "_ours"))
    delay = (pairs["valid_from"] - pairs["valid_from_ours"]).dt.days
    followed = pairs[delay.between(low, high)].drop_duplicates("competitor_price_id")
    assert len(changes) > 0 and len(followed) == len(changes)


def test_only_the_flash_sale_shop_has_sales(offers):
    shop_id, _ = flash_shop()
    assert offers["is_promotion"].dtype == bool
    assert offers.loc[offers["is_promotion"], "competitor_id"].eq(shop_id).all()
    assert offers.loc[offers["competitor_id"] == shop_id, "is_promotion"].any()


def test_sales_are_short_deep_and_end_with_the_regular_price(offers):
    shop_id, shop = flash_shop()
    mine = offers[offers["competitor_id"] == shop_id]
    before = mine.groupby("product_id")["price_gross"].shift(1)
    after = mine.groupby("product_id")["price_gross"].shift(-1)
    after_is_sale = mine.groupby("product_id")["is_promotion"].shift(-1)
    sale = mine["is_promotion"]
    assert before[sale].notna().all() and (mine.loc[sale, "change_type"] == "decrease").all()
    priced = sale & (before >= 50)  # under 50 PLN the ,99 ending moves the discount by more than 2 points
    discount = 1 - mine.loc[priced, "price_gross"] / before[priced]
    low, high = min(shop["sale_discounts"]), max(shop["sale_discounts"])
    assert discount.between(low - 0.02, high + 0.02).all()
    assert discount.mean() == pytest.approx(np.mean(shop["sale_discounts"]), abs=0.02)
    ended = sale & mine["valid_to"].notna() & after.notna()
    days = (mine.loc[ended, "valid_to"] - mine.loc[ended, "valid_from"]).dt.days + 1
    assert days.between(*shop["sale_days"]).all()
    assert not after_is_sale[ended].astype(bool).any()
    assert (after[ended] == before[ended]).mean() >= 0.9


def test_sales_never_overlap_and_black_friday_is_one_of_them(offers):
    _, shop = flash_shop()
    events = cp.sale_events(shop, np.random.default_rng(0))
    assert (events["start"].diff().dropna() >= pd.Timedelta(days=shop["sale_gap_days"])).all()
    assert (events["end"] >= events["start"]).all()
    for year in range(s.start_year, s.end_year + 1):
        friday = fc.black_friday(year)
        assert ((events["start"] == friday) & (events["end"] == friday + pd.Timedelta(days=3))).any()
    shop_id, _ = flash_shop()
    on_friday = prices_on(offers[offers["competitor_id"] == shop_id], fc.black_friday(s.end_year))
    assert on_friday["is_promotion"].mean() == pytest.approx(shop["black_friday_share"], abs=0.1)
    ordinary = events[~events["start"].isin([fc.black_friday(year) for year in range(s.start_year, s.end_year + 1)])]
    assert (ordinary["share"] == shop["sale_share"]).all() and len(ordinary) >= s.end_year - s.start_year + 1


def test_same_seed_same_table_and_other_seed_differs(offers):
    again = generate(customers=300, products=4000, order_lines=1500)["competitor_prices"]
    pd.testing.assert_frame_equal(offers, again)
    other = generate(customers=300, products=4000, order_lines=1500, seed=7)["competitor_prices"]
    assert not other["price_gross"].head(500).equals(offers["price_gross"].head(500))


def test_other_tables_do_not_depend_on_competitor_prices(data):
    without = generate(customers=300, products=4000, order_lines=1500,
                       generated_files=[name for name in ALL_FILES if name != "competitor_prices"])
    assert "competitor_prices" not in without
    for name, frame in without.items():
        pd.testing.assert_frame_equal(frame, data[name], obj=name)


def test_table_is_the_same_at_any_quality_level_and_language(offers):
    dirty = generate(customers=300, products=4000, order_lines=1500, quality_level="high")["competitor_prices"]
    pd.testing.assert_frame_equal(offers, dirty)
    polish = generate(customers=300, products=4000, order_lines=1500, language="pl")["competitor_prices"]
    pd.testing.assert_frame_equal(offers, polish)


def test_round_price_endings():
    assert cp.round_price([149.37, 0.2], "99").tolist() == [148.99, 0.99]
    assert cp.round_price([153.0, 155.0, 12.4], "9").tolist() == [149.0, 159.0, 11.99]
    with pytest.raises(ValueError):
        cp.round_price([10.0], "95")
