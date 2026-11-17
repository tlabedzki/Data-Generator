"""Tests of the Dash app layer: run registry, figures and the result views (no browser needed)."""
import pytest

from func import service
from ui import app as ui_app
from ui import figures, runs

SMALL = dict(customers=200, products=300, order_lines=800)


@pytest.fixture(scope="module")
def run():
    run_id = runs.start(service.GenerationParams(**SMALL), background=False)
    return run_id, runs.get(run_id)


def test_run_finishes_with_all_tables(run):
    _, result = run
    assert result.error is None and result.done
    assert set(result.datasets) == set(service.DATASET_NAMES)
    assert result.fraction == pytest.approx(1.0)


def test_invalid_run_reports_error_instead_of_raising():
    run_id = runs.start(service.GenerationParams(customers=1), background=False)
    assert "customers" in runs.get(run_id).error


def test_registry_keeps_only_recent_runs():
    ids = [runs.start(service.GenerationParams(customers=1), background=False) for _ in range(runs.MAX_RUNS + 2)]
    assert runs.get(ids[0]) is None and runs.get(ids[-1]) is not None
    assert runs.get(None) is None


def test_exports_are_cached_per_format(run):
    _, result = run
    first = runs.exports_for(result, "csv")
    assert runs.exports_for(result, "csv") is first
    assert set(first["tables"]) == set(service.DATASET_NAMES) and first["zip"][:2] == b"PK"


def test_figures_highlight_one_mark(run):
    sales = run[1].datasets["sales_data"]
    weekday = figures.weekday_profile(sales, service.GenerationParams().weekday_seasonality)
    category = figures.category_mix(sales)
    for fig in (weekday, category):
        colors = fig.data[0].marker.color
        assert list(colors).count(figures.t.ACCENT) == 1
    revenue = figures.monthly_revenue(sales)
    assert revenue.data[1].marker.color == figures.t.ACCENT and len(revenue.data[1].x) == 1


def test_result_views_render(run):
    _, result = run
    assert ui_app.preview_view(result) and ui_app.charts_view(result)
    assert ui_app.table_view(result.datasets["sales_data"])
    zip_button, rows = ui_app.file_list(result, "parquet")
    assert "ZIP" in zip_button.children and len(rows.children) == 4


def test_layout_builds():
    assert ui_app.page() is not None


def _download(trigger, run_id, file_format="csv"):
    """Call the download callback the way Dash does after a click on `trigger`."""
    from contextvars import copy_context

    from dash._callback_context import context_value
    from dash._utils import AttributeDict

    def call():
        context_value.set(AttributeDict(triggered_inputs=[{"prop_id": f"{trigger}.n_clicks", "value": 1}]))
        return ui_app.download(1, [1, None, None, None], file_format, run_id)

    return copy_context().run(call)


def test_download_zip_and_single_table():
    run_id = runs.start(service.GenerationParams(**SMALL), background=False)  # fresh: older runs may be evicted
    zipped = _download("dl-zip", run_id)
    assert zipped["filename"] == "data-generator-seed-42-csv.zip" and zipped["base64"]
    table = _download('{"name":"sales_data","type":"dl-table"}', run_id, "parquet")
    assert table["filename"] == "sales_data.parquet"


def test_fonts_are_bundled_locally():
    """Text, heading and number faces each have @font-face rules whose files exist, with an OFL licence each."""
    import re
    from pathlib import Path

    from ui import theme

    assets = Path(ui_app.__file__).parent / "assets"
    css = (assets / "fonts.css").read_text(encoding="utf-8")
    assert set(re.findall(r"font-family: '([^']+)'", css)) == {theme.SANS, theme.HEAD, theme.NUM}
    for url in re.findall(r"url\('([^']+)'\)", css):
        assert (assets / url).is_file(), url
    assert len(list((assets / "fonts").glob("OFL-*.txt"))) == 3
    assert len(list((assets / "fonts").glob("*.woff2"))) == 6
