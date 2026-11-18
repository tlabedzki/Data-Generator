import pandas as pd
import pytest
from conftest import generate

import func.generator as g
import func.localization as loc
import func.save as sv
import settings.category_hierarchy as ch
import settings.main_settings as s
import settings.product_catalog as pc


def test_same_seed_gives_identical_data(small_data):
    again = generate()
    for name, frame in small_data.items():
        pd.testing.assert_frame_equal(frame, again[name])


def test_different_seed_gives_different_data(small_data):
    other = generate(seed=7)
    assert not small_data["customer_data"]["email"].equals(other["customer_data"]["email"])


def test_selected_files_reject_unknown_names(monkeypatch):
    monkeypatch.setattr(s, "generated_files", ["customer_data", "invoices"])
    with pytest.raises(ValueError):
        g.get_selected_files()


def test_selected_files_reject_empty_list(monkeypatch):
    monkeypatch.setattr(s, "generated_files", [])
    with pytest.raises(ValueError):
        g.get_selected_files()


def test_only_selected_dataset_is_returned(monkeypatch):
    monkeypatch.setattr(s, "generated_files", ["customer_data"])
    monkeypatch.setattr(s, "customer_data_rows", 50)
    assert list(g.run_generation_pipeline()) == ["customer_data"]


def test_polish_localization(small_data, monkeypatch):
    monkeypatch.setattr(s, "data_language", "pl")
    products = small_data["product_data"]
    localized = loc.localize_dataset(products)
    electronics = products["category"] == "Electronics"
    assert electronics.any()
    assert (localized.loc[electronics, "category"] == "Elektronika").all()
    expected_name = localized[["product_type", "brand", "product_series", "product_model"]].agg(" ".join, axis=1)
    assert (localized["product_name"] == expected_name).all()
    # The source frame stays in English:
    assert (products.loc[electronics, "category"] == "Electronics").all()


def test_unsupported_language_is_rejected(small_data, monkeypatch):
    monkeypatch.setattr(s, "data_language", "de")
    with pytest.raises(ValueError):
        loc.localize_dataset(small_data["customer_data"])


def test_category_hierarchy_validator_blocks_duplicated_levels():
    broken = {category: dict(mapping) for category, mapping in ch.subcategory_by_product_type.items()}
    category = next(iter(broken))
    product_type = next(iter(broken[category]))
    broken[category][product_type] = product_type
    with pytest.raises(ValueError, match="duplicates product type"):
        ch.validate_category_hierarchy(pc.product_catalog, broken)


def test_product_catalog_validator_blocks_empty_models():
    broken = {"Toys": {"Puzzle": {
        "weight": 1,
        "price_range": (1, 2),
        "margin_range": (0.1, 0.2),
        "brand_series_models": {"Trefl": {"Classic": []}},
    }}}
    with pytest.raises(ValueError, match="no models"):
        pc.validate_product_catalog(broken)


@pytest.mark.parametrize("saving_format", ["parquet", "csv"])
def test_save_formats(small_data, tmp_path, monkeypatch, saving_format):
    monkeypatch.setattr(s, "saving_format", saving_format)
    path = tmp_path / f"customer_data.{saving_format}"
    sv.save_table(small_data["customer_data"], "customer_data", path)
    saved = pd.read_parquet(path) if saving_format == "parquet" else pd.read_csv(path, sep=";")
    assert len(saved) == len(small_data["customer_data"])


def test_unknown_save_format_is_rejected(small_data, tmp_path, monkeypatch):
    monkeypatch.setattr(s, "saving_format", "xlsx")
    with pytest.raises(ValueError):
        sv.save_table(small_data["customer_data"], "customer_data", tmp_path / "x.xlsx")


def test_command_line_log_is_english_and_printed_once(capsys):
    import io
    import logging

    import func.log as log
    stream = io.StringIO()
    log.configure(stream=stream)
    log.configure(stream=stream)  # configuring twice must not print every line twice
    try:
        generate(customers=200, products=200, order_lines=400)
    finally:
        for handler in list(log.logger.handlers):
            if not isinstance(handler, logging.NullHandler):
                log.logger.removeHandler(handler)
        log.logger.setLevel(logging.NOTSET)
    lines = stream.getvalue().splitlines()
    assert any("Data is ready." in line for line in lines)
    assert sum("Data is ready." in line for line in lines) == 1
    # Polish letters appear only in generated values (locality names), never in the messages:
    messages = [line for line in lines if "locality" not in line]
    assert not any(letter in line for line in messages for letter in "ąćęłńśźżĄĆĘŁŃŚŹŻ")
    assert capsys.readouterr().out == ""  # nothing goes to stdout when the log has its own stream


def test_library_is_silent_without_configuration(capsys):
    generate(customers=200, products=200, order_lines=400)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_default_settings_save_every_table():
    assert list(dict.fromkeys(s.generated_files)) == g.DATASET_NAMES
