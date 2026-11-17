"""Numbers on screen use Polish notation in both data languages: 1 234,56 (no-break space, decimal comma)."""
import re

import pytest

import func.charts as ch
import func.export as ex
import func.number_format as nf
from func import service
from ui import app as ui_app
from ui import figures, runs

NBSP = " "
ENGLISH_NUMBER = re.compile(r"\d,\d{3}|\d\.\d")  # 1,234 or 6.6 would be English notation


@pytest.mark.parametrize("value, decimals, expected", [
    (1234.5, 2, f"1{NBSP}234,50"),
    (6900, 0, f"6{NBSP}900"),
    (961, 0, "961"),
    (-1234567.891, 1, f"-1{NBSP}234{NBSP}567,9"),
])
def test_number(value, decimals, expected):
    assert nf.number(value, decimals) == expected


def test_percent_compact_and_plotly_separators():
    assert nf.percent(0.334, 1) == "33,4%" and nf.percent(0.24) == "24%"
    assert nf.compact(6_600_000) == "6,6M" and nf.compact(672_100) == "672,1k" and nf.compact(961) == "961"
    assert nf.PLOTLY_SEPARATORS == f",{NBSP}"


def _texts(component):
    """All strings inside a Dash component tree."""
    if isinstance(component, str):
        yield component
    elif isinstance(component, (list, tuple)):
        for child in component:
            yield from _texts(child)
    elif hasattr(component, "children"):
        yield from _texts(component.children)


@pytest.fixture(scope="module", params=["en", "pl"])
def run(request):
    run_id = runs.start(service.GenerationParams(customers=300, products=300, order_lines=1500,
                                                 language=request.param), background=False)
    return runs.get(run_id)


def test_screen_numbers_use_polish_notation_in_both_languages(run):
    sales = run.datasets["sales_data"]
    language = run.params.language
    texts = list(_texts(ui_app.preview_view(run))) + list(_texts(ui_app.file_list(run, "csv")))
    texts += [*ch.monthly_revenue_text(sales)[1], ch.monthly_revenue_text(sales)[0],
              *ch.weekday_text(sales, run.params.weekday_seasonality)[1],
              *ch.category_text(sales, language)[1], ch.category_text(sales, language)[0]]
    assert any(NBSP in text for text in texts)
    assert not [text for text in texts if ENGLISH_NUMBER.search(text) and "csv" not in text]
    for fig in (figures.monthly_revenue(sales), figures.weekday_profile(sales, run.params.weekday_seasonality),
                figures.category_mix(sales, language)):
        assert fig.layout.separators == f",{NBSP}"
        for trace in fig.data:
            if getattr(trace, "mode", None) == "text":
                assert not any(ENGLISH_NUMBER.search(label) for label in trace.text)
    cells = ui_app.table_view(sales)[0].children.data["body"][0]
    assert any(re.fullmatch(r"\d+,\d\d", cell) for cell in cells)
    assert not any(ENGLISH_NUMBER.search(cell) for cell in cells if not re.fullmatch(r"\d{4}-\d\d-\d\d", cell))


def test_downloads_keep_machine_format(run):
    csv = ex.dataframe_to_bytes(run.datasets["sales_data"], "csv").decode("utf-8-sig")
    assert NBSP not in csv
    header, first = csv.splitlines()[:2]
    assert re.search(r";\d+\.\d+;", first) and not re.search(r";\d+,\d+;", first)


def test_sizes_and_cells():
    assert ui_app.format_cell(1234.5) == f"1{NBSP}234,50"
    assert ui_app.size_label(b"x" * 3_600_000) == "3,6 MB"
