"""The same seed gives the same data in every process, whatever order Python iterates sets of strings in."""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
FINGERPRINT = """
import hashlib
import func.log as l
for name in ("log_info", "log_success", "log_section", "log_metric"):
    setattr(l, name, lambda *args, **kwargs: None)
import pandas as pd
from func import service
data = service.generate(service.GenerationParams(customers=500, products=500, order_lines=1000, seed=7,
                                                 data_quality_level="medium"))
digest = hashlib.md5()
for name, frame in sorted(data.items()):
    digest.update(pd.util.hash_pandas_object(frame.astype(str), index=True).values.tobytes())
print(digest.hexdigest())
"""


def fingerprint(hash_seed):
    env = {**os.environ, "PYTHONHASHSEED": str(hash_seed), "MPLBACKEND": "Agg"}
    result = subprocess.run([sys.executable, "-c", FINGERPRINT], cwd=PROJECT_DIR, env=env, capture_output=True,
                            text=True, check=True)
    return result.stdout.strip().splitlines()[-1]


def test_same_seed_gives_identical_data_across_processes():
    assert fingerprint(1) == fingerprint(2)
