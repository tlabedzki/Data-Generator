"""Draggable seasonality weights: chart, drag store -> number fields, typed numbers -> chart, restore defaults."""
from pathlib import Path

from func import service
from ui import app as ui_app
from ui import figures

DEFAULTS = service.GenerationParams()


def test_weights_figure_shows_polish_values_and_fixed_range():
    fig = figures.weights_figure([0.06, 0.1, 0.23, None, 5], ["a", "b", "c", "d", "e"])
    assert list(fig.data[0].text) == ["0,06", "0,10", "0,23", "0,00", "1,00"]  # empty -> 0, above max -> max
    assert list(fig.data[0].y) == [0.06, 0.1, 0.23, 0.0, 1.0]
    assert fig.layout.meta["max"] == figures.WEIGHT_MAX and fig.layout.yaxis.range[0] == 0


def test_drag_values_fill_the_number_fields():
    values = [0.06, 0.07, 0.08, 0.08, 0.08, 0.06, 0.264, 0.08, 0.08, 0.1, 0.21, 1.7]
    assert ui_app.months_from_drag(values)[6] == 0.26
    assert ui_app.months_from_drag(values)[-1] == figures.WEIGHT_MAX
    assert all(v is ui_app.no_update for v in ui_app.weekdays_from_drag([0.1, 0.2]))  # wrong length is ignored


def test_typed_numbers_redraw_the_chart():
    fig = ui_app.redraw_weekdays([0.3, 0.17, 0.05, 0.05, 0.07, 0.15, 0.22])
    assert fig.data[0].text[0] == "0,30" and list(fig.data[0].x) == ui_app.WEEKDAYS


def test_restore_defaults():
    months, days = ui_app.reset_weights(1)
    assert months == list(DEFAULTS.monthly_seasonality) and days == list(DEFAULTS.weekday_seasonality)
    months, days = ui_app.reset_weights(None)
    assert all(v is ui_app.no_update for v in months + days)


def test_drag_script_is_served_and_targets_the_stores():
    script = (Path(ui_app.__file__).parent / "assets" / "drag_weights.js").read_text(encoding="utf-8")
    assert "set_props" in script and '-drag' in script and "pointerdown" in script
    client = ui_app.app.server.test_client()
    page = client.get("/").data.decode()
    assert "drag_weights.js" in page
    layout = client.get("/_dash-layout").data.decode()
    assert "weights-month-graph" in layout and "weights-day-drag" in layout and "weights-reset" in layout
