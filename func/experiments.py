"""
A/B experiments with a known effect.

Variants are assigned first, at random and without looking at outcomes: units are shuffled within strata (sessions
by day, channel and device; customers by the day of their first session) and the share actual_split_b of every
stratum goes to B. Channel, device and day mix are therefore the same in A and B, and with the planned split the
sample ratio test passes easily. A different actual_split_b plants a sample ratio mismatch (a bug to detect).

The effect is applied after the split:
- conversion_rate (session experiments): a share of the converting A sessions trade places with B sessions without
  an order from the same day, channel and device. The two sessions are interchangeable before the outcome, so this is
  the same as B winning that order; B then converts (1 + true_effect) times as often as A.
- units_per_line (customer experiments): order lines of B customers in the window get extra units, true_effect more
  units per line on average.
"""
import numpy as np
import pandas as pd

import settings.experiment_settings as es

EXPERIMENT_COLUMNS = ["experiment_id", "experiment_name", "unit", "metric", "start_date", "end_date",
                      "planned_split_b", "true_effect", "has_sample_ratio_mismatch"]
ASSIGNMENT_COLUMNS = ["experiment_id", "unit", "unit_id", "variant", "assigned_at"]


def experiment_window(calendar: pd.DataFrame, definition: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
    """First and last day of an experiment, from its start_share of the period and duration_days."""
    days = len(calendar)
    start = int(round(definition["start_share"] * (days - 1)))
    end = min(start + int(definition["duration_days"]) - 1, days - 1)
    return calendar["date"].iloc[start], calendar["date"].iloc[end]


def rank_within(strata: np.ndarray, generator: np.random.Generator) -> np.ndarray:
    """A random order (0, 1, 2, ...) of the units inside each stratum."""
    shuffled = generator.permutation(len(strata))
    ranks = np.empty(len(strata), dtype=np.int64)
    ranks[shuffled] = pd.Series(strata[shuffled]).groupby(strata[shuffled]).cumcount().to_numpy()
    return ranks


def stratified_split(strata: np.ndarray, split_b: float, generator: np.random.Generator) -> np.ndarray:
    """
    Complete randomization inside each stratum: a random split_b share of its units goes to B (the fractional unit
    goes to B with the matching probability, so the expected share is exactly split_b).

    Returns:
    np.ndarray: True for units in variant B.
    """
    codes, uniques = pd.factorize(strata)
    sizes = np.bincount(codes, minlength=len(uniques))
    quota = np.floor(sizes * split_b + generator.random(len(uniques))).astype(np.int64)
    return rank_within(codes, generator) < quota[codes]


def pair_within(strata: np.ndarray, donors: np.ndarray, receivers: np.ndarray,
                generator: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Match donor positions to distinct receiver positions of the same stratum, at random."""
    donor_rank = rank_within(strata[donors], generator)
    receiver_rank = rank_within(strata[receivers], generator)
    left = pd.DataFrame({"stratum": strata[donors], "rank": donor_rank, "donor": donors})
    right = pd.DataFrame({"stratum": strata[receivers], "rank": receiver_rank, "receiver": receivers})
    pairs = left.merge(right, on=["stratum", "rank"], how="inner").sort_values("donor", kind="stable")
    return pairs["donor"].to_numpy(), pairs["receiver"].to_numpy()


def apply_conversion_effect(is_b: np.ndarray, converted: np.ndarray, strata: np.ndarray, lift: float,
                            generator: np.random.Generator) -> np.ndarray:
    """
    Make B convert (1 + lift) times as often as A by trading places of converting and non-converting sessions of the
    same stratum between the variants; the number of units in each variant and stratum stays the same.

    With n_A and n_B units and the same conversion rate c in both after the random split, moving a share m of A's
    conversions to B gives (c n_B + m c n_A) / n_B = (1 + lift) (1 - m) c, so m = lift / (1 + lift + n_A / n_B).
    A negative lift moves B's conversions to A in the same way.
    """
    is_b = is_b.copy()
    n_b, n_a = is_b.sum(), (~is_b).sum()
    if lift == 0 or n_a == 0 or n_b == 0:
        return is_b
    if lift > 0:
        share, losing = lift / (1 + lift + n_a / n_b), ~is_b
    else:
        ratio = n_a / n_b
        share, losing = -lift * ratio / (ratio + 1 + lift), is_b
    candidates = np.flatnonzero(losing & converted)
    donors = np.sort(generator.choice(candidates, size=int(round(share * len(candidates))), replace=False))
    receivers = np.flatnonzero(~losing & ~converted)
    donors, receivers = pair_within(strata, donors, receivers, generator)
    is_b[donors], is_b[receivers] = is_b[receivers], is_b[donors]
    return is_b


def session_strata(window: pd.DataFrame) -> np.ndarray:
    """Day, channel and device of every session, as one key."""
    day = window["session_start"].dt.strftime("%Y-%m-%d").to_numpy(dtype=object)
    return day + "|" + window["channel"].astype(str).to_numpy(dtype=object) + "|" + \
        window["device"].astype(str).to_numpy(dtype=object)


def assign_sessions(sessions: pd.DataFrame, in_window: np.ndarray, definition: dict,
                    generator: np.random.Generator) -> pd.DataFrame:
    """Assign every session of the window to A or B, then apply the conversion effect to B."""
    window = sessions[in_window]
    strata = session_strata(window)
    is_b = stratified_split(strata, definition["actual_split_b"], generator)
    converted = window["order_id"].notna().to_numpy()
    is_b = apply_conversion_effect(is_b, converted, strata, definition["true_effect"], generator)
    return pd.DataFrame({"unit": "session", "unit_id": window["session_id"].to_numpy(),
                         "variant": np.where(is_b, "B", "A"), "assigned_at": window["session_start"].to_numpy()})


def assign_customers(sessions: pd.DataFrame, in_window: np.ndarray, order_data: pd.DataFrame, definition: dict,
                     generator: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Assign known customers with a session in the window (stratified by the day of their first session); orders of B
    customers in the window get extra units (true_effect more units per order line on average).
    """
    window = sessions[in_window & sessions["customer_id"].notna()]
    first_seen = window.groupby("customer_id")["session_start"].min()
    strata = first_seen.dt.strftime("%Y-%m-%d").to_numpy(dtype=object)
    is_b = stratified_split(strata, definition["actual_split_b"], generator)
    assignment = pd.DataFrame({"unit": "customer", "unit_id": first_seen.index.to_numpy(dtype=np.int64),
                               "variant": np.where(is_b, "B", "A"), "assigned_at": first_seen.to_numpy()})
    treated = set(assignment.loc[assignment["variant"] == "B", "unit_id"])
    ordered_in_window = window.dropna(subset=["order_id"])["order_id"].astype(np.int64)
    lines = order_data["order_id"].isin(ordered_in_window) & order_data["customer_id"].isin(treated)
    order_data.loc[lines, "quantity"] += generator.poisson(definition["true_effect"], lines.sum())
    return assignment, order_data


def run_experiments(order_data: pd.DataFrame, sessions: pd.DataFrame, calendar: pd.DataFrame,
                    generator: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run the experiments of settings.experiment_settings on the generated sessions and orders.

    Returns:
    tuple: (order lines, experiment_data, experiment_assignment_data).
    """
    rows, assignments = [], []
    session_day = sessions["session_start"].dt.normalize()
    for number, (name, definition) in enumerate(es.experiments.items(), start=1):
        start, end = experiment_window(calendar, definition)
        in_window = session_day.between(start, end).to_numpy()
        if definition["unit"] == "customer":
            assignment, order_data = assign_customers(sessions, in_window, order_data, definition, generator)
        else:
            assignment = assign_sessions(sessions, in_window, definition, generator)
        assignment.insert(0, "experiment_id", number)
        assignments.append(assignment)
        rows.append({
            "experiment_id": number, "experiment_name": name, "unit": definition["unit"],
            "metric": definition["metric"], "start_date": start, "end_date": end,
            "planned_split_b": definition["planned_split_b"], "true_effect": definition["true_effect"],
            "has_sample_ratio_mismatch": definition["actual_split_b"] != definition["planned_split_b"],
        })
    experiment_data = pd.DataFrame(rows, columns=EXPERIMENT_COLUMNS)
    assignment_data = (pd.concat(assignments, ignore_index=True) if assignments
                       else pd.DataFrame(columns=ASSIGNMENT_COLUMNS))
    assignment_data["unit_id"] = assignment_data["unit_id"].astype(np.int64)
    assignment_data["assigned_at"] = pd.to_datetime(assignment_data["assigned_at"])
    return order_data, experiment_data, assignment_data[ASSIGNMENT_COLUMNS]
