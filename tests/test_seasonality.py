import settings.main_settings as s


def test_november_and_december_are_the_strongest_months(medium_sales):
    lines_by_month = medium_sales.groupby(medium_sales["order_date"].dt.month).size()
    assert set(lines_by_month.nlargest(2).index) == {11, 12}
    assert lines_by_month[11] > 2 * lines_by_month[2]


def test_weekday_profile_follows_settings(medium_sales):
    share = medium_sales["order_date"].dt.dayofweek.value_counts(normalize=True).sort_index()
    days_by_weight = sorted(range(7), key=lambda day: s.base_weekday_seasonality[day])
    weakest, strongest = days_by_weight[:2], days_by_weight[-2:]
    assert share[strongest].min() > share[weakest].max()


def test_sales_grow_year_over_year(medium_sales):
    lines_by_year = medium_sales.groupby(medium_sales["order_date"].dt.year).size()
    growth = lines_by_year[s.end_year] / lines_by_year[s.start_year] - 1
    assert 0.08 < growth < 0.35
