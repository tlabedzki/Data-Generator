"""
Daily demand calendar: the expected share of all orders on every day of the period.

A day's weight is the year weight (annual growth) × the month weight (seasonality with one random fluctuation per
month and year) split over the days of the month by the weekday weights. Month and year totals therefore follow the
settings exactly, apart from the deliberate fluctuation.
"""
import numpy as np
import pandas as pd

import settings.behaviour_settings as bs
import settings.main_settings as s


def build_calendar(generator, month_noise_sd=None):
    """
    Build the daily calendar of the configured period.

    Parameters:
    generator (np.random.Generator): Random stream for the yearly and monthly fluctuations.
    month_noise_sd (float, optional): Overrides behaviour_settings.monthly_noise_sd.

    Returns:
    pd.DataFrame: One row per day with date, year, month, weekday (0 = Monday) and weight (sums to 1).
    """
    month_noise_sd = bs.monthly_noise_sd if month_noise_sd is None else month_noise_sd
    dates = pd.date_range(f"{s.start_year}-01-01", f"{s.end_year}-12-31", freq="D")
    calendar = pd.DataFrame({"date": dates, "year": dates.year, "month": dates.month, "weekday": dates.dayofweek})

    years = np.arange(s.start_year, s.end_year + 1)
    year_weights = 1 + s.annual_growth_rate * (years - s.start_year) + generator.normal(0, 0.02, len(years))
    year_weights = np.clip(year_weights, 1e-6, None)
    year_weights = year_weights / year_weights.sum()

    base_months = np.asarray(s.base_monthly_seasonality, dtype=float)
    noise = np.clip(1 + generator.normal(0, month_noise_sd, (len(years), 12)), 0.05, None)
    month_weights = base_months * noise
    month_weights = month_weights / month_weights.sum(axis=1, keepdims=True)

    weekday_weights = np.asarray(s.base_weekday_seasonality, dtype=float)
    day_weight = weekday_weights[calendar["weekday"].to_numpy()]
    month_key = (calendar["year"] - s.start_year) * 12 + calendar["month"] - 1
    month_total = pd.Series(day_weight).groupby(month_key.to_numpy()).transform("sum").to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        within_month = np.where(month_total > 0, day_weight / month_total, 0.0)

    year_index = calendar["year"].to_numpy() - s.start_year
    month_index = calendar["month"].to_numpy() - 1
    calendar["weight"] = year_weights[year_index] * month_weights[year_index, month_index] * within_month
    calendar["weight"] = calendar["weight"] / calendar["weight"].sum()
    return calendar


def draw_days(calendar, generator, size, low=None, high=None, weights=None):
    """
    Draw day indexes from the calendar weights, optionally restricted to [low, high] per draw.

    Parameters:
    calendar (pd.DataFrame): Calendar from build_calendar.
    generator (np.random.Generator): Random stream.
    size (int): Number of draws.
    low, high (np.array, optional): Inclusive day index bounds per draw.
    weights (np.array, optional): Day weights to use instead of calendar["weight"].

    Returns:
    np.array: Day indexes.
    """
    weights = calendar["weight"].to_numpy() if weights is None else weights
    cumulative = np.concatenate([[0.0], np.cumsum(weights)])
    low = np.zeros(size, dtype=int) if low is None else np.asarray(low)
    high = np.full(size, len(weights) - 1) if high is None else np.asarray(high)
    u = cumulative[low] + generator.random(size) * (cumulative[high + 1] - cumulative[low])
    days = np.searchsorted(cumulative, u, side="right") - 1
    return np.clip(days, low, high)
