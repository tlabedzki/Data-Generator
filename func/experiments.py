"""
A/B experiments with a known effect: variants are assigned to sessions or customers so that the measured difference
between B and A matches true_effect in experiment_data (up to random noise), including a sample ratio mismatch and
an A/A test for practice.
"""
import numpy as np
import pandas as pd

import settings.experiment_settings as es

EXPERIMENT_COLUMNS = ["experiment_id", "experiment_name", "unit", "metric", "start_date", "end_date",
                      "planned_split_b", "true_effect", "has_sample_ratio_mismatch"]
ASSIGNMENT_COLUMNS = ["experiment_id", "unit", "unit_id", "variant", "assigned_at"]


def experiment_window(calendar, definition):
    days = len(calendar)
    start = int(round(definition["start_share"] * (days - 1)))
    end = min(start + int(definition["duration_days"]) - 1, days - 1)
    return calendar["date"].iloc[start], calendar["date"].iloc[end]


def assign_sessions(sessions, in_window, definition, generator):
    """
    Assign every session of the window to A or B. Converting sessions go to B with chance q and the others with
    chance r, chosen so that B gets actual_split_b of the sessions and converts (1 + true_effect) times as often.
    """
    window = sessions[in_window]
    converted = window["order_id"].notna().to_numpy()
    c = converted.mean() if len(window) else 0.0
    split, lift = definition["actual_split_b"], definition["true_effect"]
    x = c / (1 + lift * split)  # conversion rate of A
    q = (1 + lift) * split / (1 + lift * split)
    r = split * (1 - x * (1 + lift)) / (1 - c) if c < 1 else split
    chance = np.where(converted, q, np.clip(r, 0, 1))
    variant = np.where(generator.random(len(window)) < chance, "B", "A")
    return pd.DataFrame({"unit": "session", "unit_id": window["session_id"].to_numpy(), "variant": variant,
                         "assigned_at": window["session_start"].to_numpy()})


def assign_customers(sessions, in_window, order_data, definition, generator):
    """
    Assign known customers with a session in the window; orders of B customers in the window get extra units
    (true_effect more units per order line on average).
    """
    window = sessions[in_window & sessions["customer_id"].notna()]
    first_seen = window.groupby("customer_id")["session_start"].min()
    variant = np.where(generator.random(len(first_seen)) < definition["actual_split_b"], "B", "A")
    assignment = pd.DataFrame({"unit": "customer", "unit_id": first_seen.index.to_numpy(dtype=np.int64),
                               "variant": variant, "assigned_at": first_seen.to_numpy()})
    treated = set(assignment.loc[assignment["variant"] == "B", "unit_id"])
    ordered_in_window = window.dropna(subset=["order_id"])["order_id"].astype(np.int64)
    lines = order_data["order_id"].isin(ordered_in_window) & order_data["customer_id"].isin(treated)
    order_data.loc[lines, "quantity"] += generator.poisson(definition["true_effect"], lines.sum())
    return assignment, order_data


def run_experiments(order_data, sessions, calendar, generator):
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
