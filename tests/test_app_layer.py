import io
import zipfile

import pandas as pd
import pytest

import func.charts as ch
import func.export as ex
import func.generator as g
import settings.main_settings as s
from func import service

SMALL = dict(customers=200, products=300, order_lines=800)
ORIGINAL_SETTINGS = (s.customer_data_rows, s.data_language, s.random_state, list(s.base_weekday_seasonality))


@pytest.fixture(scope="module")
def generated():
    params = service.GenerationParams(**SMALL)
    return params, service.generate(params)


# Parameters ----------------------------------------------------------------------------------------------------- #

def test_default_params_are_valid():
    assert service.GenerationParams().errors() == []


@pytest.mark.parametrize("changes, fragment", [
    ({"customers": 10}, "customers"),
    ({"order_lines": 1_000_000}, "order_lines"),
    ({"start_year": 2024, "end_year": 2023}, "earlier"),
    ({"start_year": 2010, "end_year": 2030}, "at most"),
    ({"language": "de"}, "language"),
    ({"seed": -1}, "seed"),
    ({"monthly_seasonality": (1.0,) * 11}, "12 values"),
    ({"weekday_seasonality": (0.0,) * 7}, "not all zero"),
    ({"annual_growth_rate": -0.5, "start_year": 2016, "end_year": 2025}, "too steep"),
    ({"annual_growth_rate": -0.2, "start_year": 2020, "end_year": 2025}, "too steep"),
])
def test_invalid_params_are_reported(changes, fragment):
    errors = service.GenerationParams(**changes).errors()
    assert any(fragment in error for error in errors)


def test_moderate_decline_shrinks_sales():
    params = service.GenerationParams(**SMALL, annual_growth_rate=-0.3, start_year=2022, end_year=2024)
    assert params.errors() == []
    sales = service.generate(params)["sales_data"]
    lines_by_year = sales.groupby(sales["order_date"].dt.year).size()
    assert lines_by_year[2024] < lines_by_year[2022]
    assert ch.monthly_revenue_text(sales)[0].startswith("Sales shrink")


def test_defaults_do_not_follow_overridden_settings():
    with service.overridden_settings({"base_weekday_seasonality": [1, 1, 1, 1, 1, 1, 1]}):
        assert service.GenerationParams().weekday_seasonality == service.DEFAULT_WEEKDAY_SEASONALITY


def test_generate_rejects_invalid_params():
    with pytest.raises(ValueError):
        service.generate(service.GenerationParams(customers=1))


def test_params_reach_the_generator(generated):
    params, datasets = generated
    assert len(datasets["customer_data"]) == SMALL["customers"]
    assert len(datasets["product_data"]) == SMALL["products"]
    assert len(datasets["order_data"]) >= SMALL["order_lines"]
    years = datasets["sales_data"]["order_date"].dt.year
    assert years.min() >= params.start_year and years.max() <= params.end_year


def test_settings_are_restored_after_generation(generated):
    current = (s.customer_data_rows, s.data_language, s.random_state, list(s.base_weekday_seasonality))
    assert current == ORIGINAL_SETTINGS


def test_same_params_give_same_data(generated):
    params, datasets = generated
    again = service.generate(params)
    pd.testing.assert_frame_equal(datasets["sales_data"], again["sales_data"])


def test_language_and_years_are_applied():
    params = service.GenerationParams(**SMALL, language="pl", start_year=2020, end_year=2020)
    sales = service.generate(params)["sales_data"]
    assert set(sales["order_date"].dt.year) == {2020}
    assert "Odzież" in set(sales["category"])


def test_progress_is_reported_and_ends_at_one():
    calls = []
    service.generate(service.GenerationParams(**SMALL),
                     progress=lambda fraction, stage: calls.append((fraction, stage)))
    fractions = [fraction for fraction, _ in calls]
    assert fractions == sorted(fractions)
    assert fractions[-1] == pytest.approx(1.0)
    assert {stage for _, stage in calls} == set(g.STAGE_SHARES)


# Export --------------------------------------------------------------------------------------------------------- #

def test_csv_export_round_trip(generated):
    _, datasets = generated
    content = ex.dataframe_to_bytes(datasets["customer_data"], "csv")
    assert content.startswith(b"\xef\xbb\xbf")
    restored = pd.read_csv(io.BytesIO(content), sep=";", encoding="utf-8-sig", dtype={"postal_code": str})
    assert restored.shape == datasets["customer_data"].shape


def test_parquet_export_round_trip(generated):
    _, datasets = generated
    content = ex.dataframe_to_bytes(datasets["sales_data"], "parquet")
    pd.testing.assert_frame_equal(pd.read_parquet(io.BytesIO(content)), datasets["sales_data"].reset_index(drop=True))


def test_zip_contains_every_table(generated):
    _, datasets = generated
    archive = zipfile.ZipFile(io.BytesIO(ex.datasets_to_zip(datasets, "parquet")))
    assert sorted(archive.namelist()) == sorted(f"{name}.parquet" for name in datasets)


def test_unknown_export_format_is_rejected(generated):
    _, datasets = generated
    with pytest.raises(ValueError):
        ex.dataframe_to_bytes(datasets["customer_data"], "xlsx")


# Charts --------------------------------------------------------------------------------------------------------- #

def test_headline_numbers(generated):
    _, datasets = generated
    numbers = ch.headline_numbers(datasets)
    sales = datasets["sales_data"]
    assert numbers["orders"] == sales["order_id"].nunique()
    assert numbers["revenue"] == pytest.approx(sales["revenue_gross"].sum())
    assert 0 <= numbers["discounted_line_share"] <= 1


def test_chart_data_shares_sum_to_one(generated):
    params, datasets = generated
    sales = datasets["sales_data"]
    weekdays = ch.weekday_data(sales, params.weekday_seasonality)
    categories = ch.category_data(sales)
    assert weekdays["share"].sum() == pytest.approx(1.0)
    assert weekdays["configured"].sum() == pytest.approx(1.0)
    assert categories["share"].sum() == pytest.approx(1.0)
    assert categories["is_top"].sum() == 1 and categories.iloc[0]["is_top"]
    assert ch.monthly_revenue_data(sales)["revenue"].sum() == pytest.approx(sales["revenue_gross"].sum())


def test_polish_category_targets_are_translated():
    sales = service.generate(service.GenerationParams(**SMALL, language="pl"))["sales_data"]
    categories = ch.category_data(sales, "pl")
    assert "Odzież" in set(categories["category"])
    assert "Clothing" not in set(categories["category"])


def test_chart_titles_state_the_conclusion(generated):
    params, datasets = generated
    sales = datasets["sales_data"]
    title, _ = ch.category_text(sales)
    top = ch.category_data(sales).iloc[0]
    assert title.startswith(top["category"])
    assert "a year" in ch.monthly_revenue_text(sales)[0]
