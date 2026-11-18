"""
A thin service layer between user interfaces (the web app in ui/) and the generator.

The generator reads its parameters from the `settings` modules. `generate()` overrides the user-facing settings for
one run, calls the existing pipeline and restores the previous values afterwards. A lock keeps concurrent app
sessions from mixing settings or the global random state.
"""
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from types import ModuleType

import pandas as pd

import func.generator as g
import settings.main_settings as s
import settings.quality_settings as qs

DATASET_NAMES = list(g.DATASET_NAMES)

DATA_QUALITY_LEVELS = list(qs.data_quality_rates)

LANGUAGES = {"en": "English", "pl": "Polish"}

# Limits keep a single run in the app under roughly half a minute.
LIMITS = {
    "customers": (100, 50_000),
    "products": (100, 50_000),
    "order_lines": (100, 100_000),
    "start_year": (2000, 2035),
    "end_year": (2000, 2035),
    "years_span": 10,
    "annual_growth_rate": (-0.5, 1.0),
    "seed": (0, 2**31 - 1),
}

# The generator weights years linearly (1 + growth * years since start); keep the last year clearly positive.
MIN_LAST_YEAR_WEIGHT = 0.2

# Defaults copied at import, so a running generation (which overrides settings) never leaks into them.
DEFAULT_MONTHLY_SEASONALITY = tuple(s.base_monthly_seasonality)
DEFAULT_WEEKDAY_SEASONALITY = tuple(s.base_weekday_seasonality)

_GENERATION_LOCK = threading.Lock()


@dataclass(frozen=True)
class GenerationParams:
    """Parameters a user can change in the app. Defaults give a dataset in a few seconds."""

    customers: int = 5_000
    products: int = 5_000
    order_lines: int = 10_000
    start_year: int = s.start_year
    end_year: int = s.end_year
    annual_growth_rate: float = s.annual_growth_rate
    monthly_seasonality: tuple[float, ...] = DEFAULT_MONTHLY_SEASONALITY
    weekday_seasonality: tuple[float, ...] = DEFAULT_WEEKDAY_SEASONALITY
    seed: int | None = 42
    language: str = "en"
    data_quality_level: str = qs.data_quality_level

    def errors(self) -> list[str]:
        """Return a list of readable validation errors; an empty list means the parameters are valid."""
        problems = []
        for name in ("customers", "products", "order_lines", "start_year", "end_year", "annual_growth_rate"):
            low, high = LIMITS[name]
            value = getattr(self, name)
            if not low <= value <= high:
                problems.append(f"{name} must be between {low:,} and {high:,} (got {value:,}).")
        if self.end_year < self.start_year:
            problems.append("end_year must not be earlier than start_year.")
        elif self.end_year - self.start_year + 1 > LIMITS["years_span"]:
            problems.append(f"The date range can cover at most {LIMITS['years_span']} years.")
        elif 1 + self.annual_growth_rate * (self.end_year - self.start_year) < MIN_LAST_YEAR_WEIGHT:
            problems.append(
                "This decline is too steep for the date range: the last year would have almost no orders. "
                "Use a smaller decline or fewer years."
            )
        if self.seed is not None and not LIMITS["seed"][0] <= self.seed <= LIMITS["seed"][1]:
            problems.append("seed must be a non-negative 32-bit integer.")
        if self.language not in LANGUAGES:
            problems.append(f"language must be one of {sorted(LANGUAGES)}.")
        if self.data_quality_level not in DATA_QUALITY_LEVELS:
            problems.append(f"data_quality_level must be one of {DATA_QUALITY_LEVELS}.")
        problems += _weights_errors("monthly_seasonality", self.monthly_seasonality, 12)
        problems += _weights_errors("weekday_seasonality", self.weekday_seasonality, 7)
        return problems

    def to_settings(self) -> dict[str, object]:
        """Map the parameters to the names used in settings.main_settings."""
        return {
            "customer_data_rows": self.customers,
            "product_data_rows": self.products,
            "order_data_rows": self.order_lines,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "annual_growth_rate": self.annual_growth_rate,
            "base_monthly_seasonality": list(self.monthly_seasonality),
            "base_weekday_seasonality": list(self.weekday_seasonality),
            "random_state": self.seed,
            "data_language": self.language,
            "generated_files": list(DATASET_NAMES),
        }

    def to_quality_settings(self) -> dict[str, object]:
        """Map the parameters to the names used in settings.quality_settings."""
        return {"data_quality_level": self.data_quality_level}

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _weights_errors(name: str, weights: tuple[float, ...], length: int) -> list[str]:
    if len(weights) != length:
        return [f"{name} needs {length} values."]
    if any(weight < 0 for weight in weights) or sum(weights) <= 0:
        return [f"{name} values must be non-negative and not all zero."]
    return []


@contextmanager
def overridden_settings(values: dict[str, object], module: ModuleType = s) -> Iterator[None]:
    """Temporarily set attributes of a settings module (settings.main_settings by default) and restore them."""
    missing = object()
    previous = {name: getattr(module, name, missing) for name in values}
    try:
        for name, value in values.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in previous.items():
            if value is missing:
                delattr(module, name)
            else:
                setattr(module, name, value)


def generate(params: GenerationParams, progress: g.ProgressCallback | None = None) -> dict[str, pd.DataFrame]:
    """
    Generate all datasets for the given parameters.

    Parameters:
    params (GenerationParams): Validated parameters.
    progress (callable, optional): Called as progress(fraction, stage_name).

    Returns:
    dict: Dataset names mapped to DataFrames.

    Raises:
    ValueError: When the parameters are not valid (all problems in one message).
    """
    problems = params.errors()
    if problems:
        raise ValueError(" ".join(problems))

    with (_GENERATION_LOCK, overridden_settings(params.to_settings()),
          overridden_settings(params.to_quality_settings(), qs)):
        return g.run_generation_pipeline(progress=progress)
