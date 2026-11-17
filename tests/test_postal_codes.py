import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import func.customer as c

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_postal_codes.py"
spec = importlib.util.spec_from_file_location("build_postal_codes", SCRIPT)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_source_file_matches_generator_contract():
    codes = c.code_df
    assert list(codes.columns) == ["id", "postal_code", "city", "address_count"]
    assert codes["id"].tolist() == list(range(len(codes)))
    assert codes["postal_code"].is_unique
    assert codes["postal_code"].str.fullmatch(r"\d{2}-\d{3}").all()
    assert codes["city"].notna().all()
    assert (codes["address_count"] > 0).all()


def test_customers_get_postal_codes_from_source(small_data):
    customers = small_data["customer_data"]
    pairs = set(zip(c.code_df["postal_code"], c.code_df["city"]))
    assert set(zip(customers["postal_code"], customers["city"])) <= pairs


def test_postal_code_draw_follows_weights():
    np.random.seed(0)
    drawn = c.draw_postal_code_ids(5000, [10, 20, 30], [0, 1, 3])
    assert 10 not in drawn
    share_30 = (drawn == 30).mean()
    assert 0.70 < share_30 < 0.80


def test_convert_keeps_contract_and_drops_bad_rows():
    source = pd.DataFrame({
        "kod_pocztowy": ["00-003", "00-002", "00-002", "bad", "01-001"],
        "miejscowosc_glowna": ["Warszawa", "Warszawa", "Warszawa", "X", "Warszawa"],
        "liczba_adresow": [3, 1, 1, 5, 0],
        "powiat": ["Warszawa"] * 5,
    })
    converted = build.convert(source)
    assert list(converted.columns) == ["id", "postal_code", "city", "address_count"]
    assert converted["postal_code"].tolist() == ["00-002", "00-003"]
    assert converted["id"].tolist() == [0, 1]


def test_convert_rejects_missing_columns():
    with pytest.raises(ValueError, match="Missing columns"):
        build.convert(pd.DataFrame({"kod_pocztowy": ["00-001"]}))
