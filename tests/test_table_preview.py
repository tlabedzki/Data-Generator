"""Table previews: one shared native scroll box, fresh for every table and run, header over its columns."""
import re
from pathlib import Path

import pytest
from dash import html

from func import service
from ui import app as ui_app
from ui import runs

CSS = (Path(ui_app.__file__).parent / "assets" / "style.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run():
    run_id = runs.start(service.GenerationParams(customers=300, products=300, order_lines=800), background=False)
    return run_id, runs.get(run_id)


@pytest.mark.parametrize("name", list(ui_app.DATASET_LABELS))
def test_every_preview_uses_the_shared_scroll_box(run, name):
    run_id, result = run
    data = result.datasets[name]
    box, caption = ui_app.table_view(data, key=f"{run_id}-{name}")
    assert isinstance(box, html.Div) and box.className == "dg-table-scroll"
    assert box.key == f"table-{run_id}-{name}"  # a new box per table and run starts at the first column
    table = box.children
    header, body = table.children
    assert [th.children for th in header.children.children] == list(data.columns)
    rows = body.children
    assert len(rows) == min(ui_app.PREVIEW_ROWS, len(data))
    assert all(len(row.children) == data.shape[1] for row in rows)  # every row lines up with the header
    for row in rows:
        for cell in row.children:
            if len(cell.children) >= ui_app.CELL_TITLE_MIN:
                assert cell.title == cell.children  # a cut value keeps its full text on hover


def test_switching_tables_gives_a_new_box(run):
    run_id, result = run
    keys = {ui_app.show_table(name, run_id)[0].key for name in ui_app.DATASET_LABELS}
    assert len(keys) == len(ui_app.DATASET_LABELS)


def test_css_keeps_scrolling_inside_the_box():
    box = re.search(r"\.dg-table-scroll \{(.*?)\}", CSS, re.S).group(1)
    assert "overflow: auto" in box and "max-height" in box and "overscroll-behavior-x: contain" in box
    assert re.search(r"\.dg-table td \{[^}]*max-width:[^}]*text-overflow: ellipsis", CSS)
    assert re.search(r"\.dg-table th \{[^}]*position: sticky", CSS)
    assert "ScrollArea" not in Path(ui_app.__file__).read_text(encoding="utf-8")
