import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import func.generator as g  # noqa: E402
import settings.main_settings as s  # noqa: E402
import settings.quality_settings as qs  # noqa: E402

ALL_FILES = list(g.DATASET_NAMES)


def generate(customers=300, products=400, order_lines=1200, language="en", seed=42, quality_level="none", **extra):
    """Run the full pipeline on a small volume with temporarily overridden settings (extra: main settings)."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(qs, "data_quality_level", quality_level)
        for name, value in extra.items():
            mp.setattr(s, name, value)
        mp.setattr(s, "customer_data_rows", customers)
        mp.setattr(s, "product_data_rows", products)
        mp.setattr(s, "order_data_rows", order_lines)
        mp.setattr(s, "generated_files", ALL_FILES)
        mp.setattr(s, "data_language", language)
        mp.setattr(s, "random_state", seed)
        return g.run_generation_pipeline()


@pytest.fixture(scope="session")
def small_data():
    """Small English dataset shared by the shape and consistency tests."""
    return generate()


@pytest.fixture(scope="session")
def medium_sales():
    """Larger sales dataset for seasonality checks (still a few seconds)."""
    return generate(customers=1000, products=800, order_lines=6000)["sales_data"]
