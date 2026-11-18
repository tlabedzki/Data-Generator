"""
Daily demand calendar: the expected share of all orders on every day of the period.

A day's weight is the year weight (annual growth) × the month weight (seasonality with one random fluctuation per
month and year) split over the days of the month by the weekday weights. Month and year totals therefore follow the
settings exactly, apart from the deliberate fluctuation.
"""
import numpy as np
import pandas as pd

import settings.behaviour_settings as bs
import settings.commerce_settings as cs
import settings.main_settings as s

NO_EVENT = ""


def build_calendar(generator, month_noise_sd=None, day_multiplier=None):
    """
    Build the daily calendar of the configured period.

    Parameters:
    generator (np.random.Generator): Random stream for the yearly and monthly fluctuations.
    month_noise_sd (float, optional): Overrides behaviour_settings.monthly_noise_sd.
    day_multiplier (np.array, optional): Extra demand per day (campaigns), applied before special days; month
        totals stay the same.

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
    weight = year_weights[year_index] * month_weights[year_index, month_index] * within_month
    if day_multiplier is not None:
        boosted = weight * np.asarray(day_multiplier)
        total = pd.Series(weight).groupby(month_key.to_numpy()).transform("sum").to_numpy()
        boosted_total = pd.Series(boosted).groupby(month_key.to_numpy()).transform("sum").to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            weight = np.where(boosted_total > 0, boosted * total / boosted_total, 0.0)

    # Special days move demand inside their month; the month total stays the same. A special day starts from the
    # average day of its month (not its weekday), so Black Friday is a peak even when Fridays are quiet.
    events = special_day_names(calendar["date"])
    demand = np.array([cs.special_days[e]["demand"] if e else 1.0 for e in events])
    month_sum = pd.Series(weight).groupby(month_key.to_numpy()).transform("sum").to_numpy()
    average_day = month_sum / calendar["date"].dt.days_in_month.to_numpy()
    adjusted = np.where(events != NO_EVENT, average_day, weight) * demand
    adjusted_sum = pd.Series(adjusted).groupby(month_key.to_numpy()).transform("sum").to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        weight = np.where(adjusted_sum > 0, adjusted * month_sum / adjusted_sum, 0.0)

    calendar["weight"] = weight / weight.sum()
    calendar["event"] = events
    names = [NO_EVENT] + list(cs.special_days)
    calendar["event_index"] = [names.index(e) for e in events]
    calendar["discount_boost"] = [cs.special_days[e]["discount"] if e else 1.0 for e in events]
    return calendar


def event_names():
    """Special day names in the order of calendar["event_index"] (0 = an ordinary day)."""
    return [NO_EVENT] + list(cs.special_days)


def easter_sunday(year):
    """Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return pd.Timestamp(year, month, day)


def black_friday(year):
    first = pd.Timestamp(year, 11, 1)
    first_thursday = first + pd.Timedelta(days=(3 - first.dayofweek) % 7)
    return first_thursday + pd.Timedelta(days=22)


def named_days(name, year):
    if name == "black_friday":
        return [black_friday(year)]
    if name == "cyber_monday":
        return [black_friday(year) + pd.Timedelta(days=3)]
    if name == "black_week":
        return [black_friday(year) - pd.Timedelta(days=n) for n in range(1, 5)]
    if name == "easter_sunday":
        return [easter_sunday(year)]
    if name == "easter_monday":
        return [easter_sunday(year) + pd.Timedelta(days=1)]
    raise ValueError(f"Unknown special day: {name}.")


def special_day_names(dates):
    """Name of the special day for every date, or "" for an ordinary day."""
    names = pd.Series(NO_EVENT, index=pd.DatetimeIndex(dates))
    for year in sorted(set(names.index.year)):
        for name, definition in reversed(list(cs.special_days.items())):  # the first entry wins on overlaps
            rule = definition["dates"]
            if isinstance(rule, str):
                days = named_days(rule, year)
            else:
                days = pd.date_range(f"{year}-{rule[0]}", f"{year}-{rule[1]}", freq="D")
            days = [day for day in days if day in names.index]
            names.loc[days] = name
    return names.to_numpy()


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
