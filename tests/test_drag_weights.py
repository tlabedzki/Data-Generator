"""Seasonality weights are set only by dragging chart points: stores feed the generator, readout, restore defaults."""
from pathlib import Path

from func import service
from ui import app as ui_app
from ui import figures

DEFAULTS = service.GenerationParams()


def _ids(component):
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from _ids(child)
        return
    if getattr(component, "id", None) is not None:
        yield component.id
    children = getattr(component, "children", None)
    if children is not None and not isinstance(children, str):
        yield from _ids(children)


def test_weights_figure_shows_polish_values_and_fixed_range():
    fig = figures.weights_figure([0.06, 0.1, 0.23, None, 5], ["a", "b", "c", "d", "e"])
    assert list(fig.data[0].text) == ["0,06", "0,10", "0,23", "0,00", "1,00"]  # empty -> 0, above max -> max
    assert list(fig.data[0].y) == [0.06, 0.1, 0.23, 0.0, 1.0]
    assert fig.layout.meta["max"] == figures.WEIGHT_MAX and fig.layout.yaxis.range[0] == 0


def test_no_number_fields_only_charts_and_stores():
    ids = set(map(str, _ids(ui_app.parameters())))
    assert not any("w-month" in i or "w-day" in i for i in ids)
    for kind in ("month", "day"):
        assert {f"weights-{kind}-graph", f"weights-{kind}-drag", f"weights-{kind}-readout"} <= ids


def test_dragged_values_reach_the_generator(monkeypatch):
    """start_run reads the drag stores: the parameters it validates and starts carry the dragged weights."""
    started = {}
    monkeypatch.setattr(ui_app.runs, "start", lambda params: started.setdefault("params", params) and "run-1")
    months = list(DEFAULTS.monthly_seasonality)
    days = [0.10, 0.17, 0.05, 0.05, 0.07, 0.15, 0.22]  # Monday dragged from 0.23 down to 0.10
    ui_app.start_run(1, 5_000, 5_000, 10_000, 2023, 2024, 20, months, days, "en", 42, False)
    assert started["params"].weekday_seasonality == tuple(days)
    assert started["params"].monthly_seasonality == tuple(months)


def test_readout_lists_every_weight_in_polish_notation():
    items = ui_app.weekdays_readout([0.1, 0.17, 0.05, 0.05, 0.07, 0.15, 1.7])
    texts = [item.children[1] for item in items]
    assert texts == ["0,10", "0,17", "0,05", "0,05", "0,07", "0,15", "1,00"]
    assert [item.children[0].children for item in ui_app.months_readout(list(DEFAULTS.monthly_seasonality))] == \
        ui_app.MONTHS


def test_restore_defaults_resets_stores_and_charts():
    months, days, month_fig, day_fig = ui_app.reset_weights(1)
    assert months == list(DEFAULTS.monthly_seasonality) and days == list(DEFAULTS.weekday_seasonality)
    assert list(day_fig.data[0].y) == days and list(month_fig.data[0].x) == ui_app.MONTHS
    assert all(v is ui_app.no_update for v in ui_app.reset_weights(None))


def test_drag_script_is_served_and_targets_the_stores():
    script = (Path(ui_app.__file__).parent / "assets" / "drag_weights.js").read_text(encoding="utf-8")
    assert "set_props" in script and "-drag" in script and "pointerdown" in script
    client = ui_app.app.server.test_client()
    assert "drag_weights.js" in client.get("/").data.decode()
    layout = client.get("/_dash-layout").data.decode()
    assert "weights-month-graph" in layout and "weights-day-drag" in layout and "weights-reset" in layout
