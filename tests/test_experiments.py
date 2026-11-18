"""Pack F: A/B experiments with a known effect."""
import numpy as np
import pytest

import func.experiments as ex
import settings.experiment_settings as es
from conftest import generate


@pytest.fixture(scope="module")
def data():
    return generate(customers=5000, products=1500, order_lines=30000)


def test_experiment_table(data):
    experiments = data["experiment_data"]
    assert list(experiments["experiment_name"]) == list(es.experiments)
    assert (experiments["end_date"] >= experiments["start_date"]).all()
    mismatch = experiments.set_index("experiment_name")["has_sample_ratio_mismatch"]
    assert mismatch["free_shipping_banner"] and not mismatch["checkout_redesign"]


def test_assignments_are_unique_and_inside_the_window(data):
    assignments, experiments = data["experiment_assignment_data"], data["experiment_data"].set_index("experiment_id")
    assert not assignments.duplicated(["experiment_id", "unit_id"]).any()
    assert set(assignments["variant"]) == {"A", "B"}
    day = assignments["assigned_at"].dt.normalize()
    assert (day >= assignments["experiment_id"].map(experiments["start_date"])).all()
    assert (day <= assignments["experiment_id"].map(experiments["end_date"])).all()


def test_split_follows_the_actual_split(data):
    assignments = data["experiment_assignment_data"]
    for number, (name, definition) in enumerate(es.experiments.items(), start=1):
        share_b = (assignments.loc[assignments["experiment_id"] == number, "variant"] == "B").mean()
        assert share_b == pytest.approx(definition["actual_split_b"], abs=0.03), name


def test_conversion_effect_points_the_right_way(data):
    sessions = data["session_data"].set_index("session_id")
    assignments = data["experiment_assignment_data"]
    units = assignments[assignments["experiment_id"] == 1]
    converted = sessions.loc[units["unit_id"], "order_id"].notna().to_numpy()
    b = units["variant"].to_numpy() == "B"
    assert converted[b].mean() > converted[~b].mean()


def test_assignment_math_gives_the_effect():
    import pandas as pd
    rng = np.random.default_rng(0)
    sessions = pd.DataFrame({"session_id": np.arange(200_000), "session_start": pd.Timestamp("2024-01-01"),
                             "order_id": np.where(rng.random(200_000) < 0.1, 1.0, np.nan)})
    definition = {"actual_split_b": 0.4, "true_effect": 0.2}
    assignment = ex.assign_sessions(sessions, np.ones(len(sessions), bool), definition, rng)
    b = assignment["variant"].to_numpy() == "B"
    converted = sessions["order_id"].notna().to_numpy()
    assert b.mean() == pytest.approx(0.4, abs=0.005)
    assert converted[b].mean() / converted[~b].mean() - 1 == pytest.approx(0.2, abs=0.03)
