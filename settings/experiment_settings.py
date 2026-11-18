# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # A/B experiments (experiment_data and experiment_assignment_data):

# Every experiment runs on a part of the period: it starts at start_share of the period (0 = first day, 1 = last day)
# and lasts duration_days. Variant B is the change; A is the control.
# - unit: "session" (every session is assigned on its own) or "customer" (all sessions of a known customer get the
#   same variant; anonymous sessions are not in the experiment),
# - metric and true_effect: the effect built into the data, the answer to check an analysis against:
#   - "conversion_rate": relative change of the conversion rate of sessions (0.10 = +10%),
#   - "units_per_line": absolute change of the mean quantity per order line (0.12 = +0.12 units),
# - planned_split_b: the share of units meant for variant B,
# - actual_split_b: the share they really get; a different value is a sample ratio mismatch (a bug to detect).
# Variants are assigned at random within strata (day, channel and device for sessions), so A and B have the same
# traffic mix; the effect is added afterwards (func/experiments.py). checkout_redesign runs 9 weeks: with about 8%
# conversion that is roughly the length needed to detect +10% with 80% power at a 5% significance level. The other
# tests are shorter and underpowered on purpose (free_shipping_banner also has a sample ratio mismatch).
experiments = {
    "checkout_redesign": {
        "start_share": 0.12, "duration_days": 63, "unit": "session", "metric": "conversion_rate",
        "true_effect": 0.10, "planned_split_b": 0.5, "actual_split_b": 0.5,
    },
    "recommendation_widget": {
        "start_share": 0.33, "duration_days": 42, "unit": "customer", "metric": "units_per_line",
        "true_effect": 0.12, "planned_split_b": 0.5, "actual_split_b": 0.5,
    },
    "free_shipping_banner": {
        "start_share": 0.55, "duration_days": 35, "unit": "session", "metric": "conversion_rate",
        "true_effect": 0.06, "planned_split_b": 0.5, "actual_split_b": 0.46,
    },
    "search_ranking_aa": {
        "start_share": 0.75, "duration_days": 28, "unit": "session", "metric": "conversion_rate",
        "true_effect": 0.0, "planned_split_b": 0.5, "actual_split_b": 0.5,
    },
}
