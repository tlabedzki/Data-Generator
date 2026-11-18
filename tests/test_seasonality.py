import pandas as pd

import settings.main_settings as s


def test_november_and_december_are_the_strongest_months(medium_sales):
    lines_by_month = medium_sales.groupby(medium_sales["order_date"].dt.month).size()
    assert set(lines_by_month.nlargest(2).index) == {11, 12}
    assert lines_by_month[11] > 2 * lines_by_month[2]


def test_weekday_profile_follows_settings(medium_sales):
    orders = medium_sales.drop_duplicates("order_id")
    share = orders["order_date"].dt.dayofweek.value_counts(normalize=True).sort_index()
    weights = pd.Series(s.base_weekday_seasonality) / sum(s.base_weekday_seasonality)
    # Special days and weekly e-mail campaigns move a day by a point or two; the configured profile stays visible:
    assert (share - weights).abs().max() < 0.03
    assert share.idxmin() == weights.idxmin()


def test_sales_grow_year_over_year(medium_sales):
    lines_by_year = medium_sales.groupby(medium_sales["order_date"].dt.year).size()
    growth = lines_by_year[s.end_year] / lines_by_year[s.start_year] - 1
    assert 0.08 < growth < 0.35
