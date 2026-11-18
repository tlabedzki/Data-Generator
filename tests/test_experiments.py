"""Pack F: A/B experiments with a known effect."""
import numpy as np
import pandas as pd
import pytest
from conftest import generate

import func.experiments as ex
import settings.experiment_settings as es


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
        assert share_b == pytest.approx(definition["actual_split_b"], abs=0.01), name


def test_measured_conversion_lift_matches_the_true_effect(data):
    sessions = data["session_data"].set_index("session_id")
    assignments = data["experiment_assignment_data"]
    units = assignments[assignments["experiment_id"] == 1]
    converted = sessions.loc[units["unit_id"], "order_id"].notna().to_numpy()
    b = units["variant"].to_numpy() == "B"
    pa, pb = converted[~b].mean(), converted[b].mean()
    se = np.sqrt((1 - pa) / (pa * (~b).sum()) + (1 - pb) / (pb * b.sum()))
    # The measured lift has the noise of a real test: the true +10% lies inside its 99% interval.
    assert abs(np.log(pb / pa) - np.log(1.10)) < 2.58 * se


def synthetic_sessions(count, conversion, generator):
    import pandas as pd
    return pd.DataFrame({
        "session_id": np.arange(count),
        "session_start": pd.Timestamp("2024-01-01") + pd.to_timedelta(generator.integers(0, 28, count), unit="D"),
        "channel": generator.choice(["email", "social", "direct"], count),
        "device": generator.choice(["mobile", "desktop"], count),
        "order_id": np.where(generator.random(count) < conversion, 1.0, np.nan)})


def test_assignment_math_gives_the_effect():
    rng = np.random.default_rng(0)
    sessions = synthetic_sessions(200_000, 0.1, rng)
    definition = {"actual_split_b": 0.4, "true_effect": 0.2}
    assignment = ex.assign_sessions(sessions, np.ones(len(sessions), bool), definition, rng)
    b = assignment["variant"].to_numpy() == "B"
    converted = sessions["order_id"].notna().to_numpy()
    assert b.mean() == pytest.approx(0.4, abs=0.001)
    assert converted[b].mean() / converted[~b].mean() - 1 == pytest.approx(0.2, abs=0.03)


@pytest.mark.parametrize("lift", [0.1, -0.1, 0.0])
def test_effect_keeps_the_random_split_in_every_stratum(lift):
    rng = np.random.default_rng(1)
    sessions = synthetic_sessions(60_000, 0.08, rng)
    definition = {"actual_split_b": 0.5, "true_effect": lift}
    assignment = ex.assign_sessions(sessions, np.ones(len(sessions), bool), definition, rng)
    b = assignment["variant"].to_numpy() == "B"
    strata = ex.session_strata(sessions)
    share_b = sessions.assign(b=b).groupby(strata)["b"].agg(["mean", "size"])
    # Every stratum is split within one unit of the planned share, before and after the effect:
    assert ((share_b["mean"] - 0.5).abs() * share_b["size"] <= 1).all()
    converted = sessions["order_id"].notna().to_numpy()
    assert converted[b].mean() / converted[~b].mean() - 1 == pytest.approx(lift, abs=0.04)


def test_sample_ratio_test_passes_without_a_planted_mismatch(data):
    import math
    assignments, experiments = data["experiment_assignment_data"], data["experiment_data"]
    for row in experiments.itertuples():
        variants = assignments.loc[assignments["experiment_id"] == row.experiment_id, "variant"]
        observed = np.array([(variants == "A").sum(), (variants == "B").sum()])
        expected = np.array([1 - row.planned_split_b, row.planned_split_b]) * len(variants)
        p_value = math.erfc(math.sqrt(((observed - expected) ** 2 / expected).sum() / 2))
        assert (p_value < 0.001) if row.has_sample_ratio_mismatch else (p_value > 0.5), row.experiment_name


def test_channel_mix_is_balanced(data):
    sessions = data["session_data"].set_index("session_id")
    units = data["experiment_assignment_data"]
    units = units[units["experiment_id"] == 1]
    channel = sessions.loc[units["unit_id"], "channel"].to_numpy()
    b = units["variant"].to_numpy() == "B"
    mix_a = pd.Series(channel[~b]).value_counts(normalize=True)
    mix_b = pd.Series(channel[b]).value_counts(normalize=True)
    assert (mix_a - mix_b).abs().max() < 0.01
