"""Parameters section: size presets, Size and Period groups, Advanced section."""
from contextvars import copy_context

import pytest
from dash._callback_context import context_value
from dash._utils import AttributeDict

from func import service
from ui import app as ui_app


def _ids(component):
    """All component ids inside a Dash component tree."""
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from _ids(child)
        return
    if getattr(component, "id", None) is not None:
        yield component.id
    children = getattr(component, "children", None)
    if children is not None and not isinstance(children, str):
        yield from _ids(children)


def test_medium_preset_is_the_app_default():
    defaults = service.GenerationParams()
    assert ui_app.preset_for(defaults.customers, defaults.products, defaults.order_lines) == "medium"
    assert ui_app.preset_for(1_000, 1_000, 2_001) == "custom"


def test_presets_are_valid_parameters():
    for preset in ui_app.PRESETS.values():
        params = service.GenerationParams(customers=preset["customers"], products=preset["products"],
                                          order_lines=preset["order_lines"])
        assert params.errors() == []


def test_parameters_have_all_fields_and_presets():
    ids = set(map(str, _ids(ui_app.parameters())))
    for field in ("customers", "products", "order-lines", "start-year", "end-year", "growth", "language", "seed",
                  "new-seed", "generate"):
        assert field in ids
    assert {str({"type": "preset", "name": name}) for name in ("small", "medium", "large", "custom")} <= ids


@pytest.mark.parametrize("name", ["small", "large"])
def test_preset_click_fills_sizes(name):
    def call():
        context_value.set(AttributeDict(triggered_inputs=[{"prop_id": f'{{"name":"{name}","type":"preset"}}.n_clicks',
                                                           "value": 1}]))
        return ui_app.apply_preset([1, 0, 0, 0])

    preset = ui_app.PRESETS[name]
    assert copy_context().run(call) == (preset["customers"], preset["products"], preset["order_lines"])


def test_manual_change_marks_custom():
    ids = [{"type": "preset", "name": name} for name in ("small", "medium", "large", "custom")]
    assert ui_app.mark_preset(5_000, 5_000, 10_000, ids) == ["dg-preset", "dg-preset is-active", "dg-preset",
                                                            "dg-preset"]
    assert ui_app.mark_preset(5_000, 5_000, 12_000, ids)[-1] == "dg-preset is-active"


def test_rendering_the_button_does_not_start_a_run():
    """A rendered but not clicked Generate button (n_clicks None) never starts a run."""
    result = ui_app.start_run(None, 5_000, 5_000, 10_000, 2023, 2024, 20, [1] * 12, [1] * 7, "en", 42, False)
    assert all(value is ui_app.no_update for value in result)
