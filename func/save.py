"""Save generated tables as CSV (semicolon-separated) or Parquet files."""
from pathlib import Path

import pandas as pd

import settings.main_settings as s
from func import log

SAVING_FORMATS = ("csv", "parquet")


def save_table(data: pd.DataFrame, name: str, path: Path, saving_format: str | None = None) -> None:
    """
    Save one table in the given format (settings.main_settings.saving_format by default).

    Raises:
    ValueError: When the format is not csv or parquet.
    """
    saving_format = saving_format or s.saving_format
    if saving_format == "csv":
        data.to_csv(path, sep=";", index=False)
    elif saving_format == "parquet":
        data.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported saving_format: {saving_format}. Use one of {list(SAVING_FORMATS)}.")
    log.log_success(f"Saved {name} ({len(data):,} rows) to {path.parent.name}/{path.name}")


def save_generated_outputs(generated_data: dict[str, pd.DataFrame], saving_paths: dict[str, Path]) -> None:
    """Save every generated table to its path."""
    for name, frame in generated_data.items():
        save_table(frame, name, saving_paths[name])
