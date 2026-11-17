"""
Generation runs kept in server memory. A run starts in a background thread, reports its progress for the polling
callback and keeps its DataFrames and serialized exports, so the browser only ever holds a short run id.
"""
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from func import export, service

MAX_RUNS = 4  # finished runs kept in memory; older ones are dropped

_RUNS = OrderedDict()
_LOCK = threading.Lock()


@dataclass
class Run:
    params: service.GenerationParams
    fraction: float = 0.0
    stage: str = ""
    datasets: dict | None = None
    error: str | None = None
    seconds: float = 0.0
    exports: dict = field(default_factory=dict)

    @property
    def done(self):
        return self.datasets is not None or self.error is not None


def start(params, background=True):
    """Start a run and return its id. With background=False the run finishes before returning (tests)."""
    run_id = uuid.uuid4().hex
    run = Run(params)
    with _LOCK:
        _RUNS[run_id] = run
        while len(_RUNS) > MAX_RUNS:
            _RUNS.popitem(last=False)
    worker = threading.Thread(target=_work, args=(run,), daemon=True)
    worker.start()
    if not background:
        worker.join()
    return run_id


def _work(run):
    def on_progress(fraction, stage):
        run.fraction, run.stage = fraction, stage

    started = time.perf_counter()
    try:
        run.datasets = service.generate(run.params, progress=on_progress)
    except Exception as error:  # shown to the user instead of a silent failure
        run.error = str(error)
    run.seconds = time.perf_counter() - started


def get(run_id):
    with _LOCK:
        return _RUNS.get(run_id) if run_id else None


def exports_for(run, file_format):
    """Serialize each table and the ZIP once per run and format."""
    if file_format not in run.exports:
        tables = {name: export.dataframe_to_bytes(data, file_format) for name, data in run.datasets.items()}
        zipped = export.files_to_zip({export.file_name(name, file_format): content for name, content in tables.items()})
        run.exports[file_format] = {"tables": tables, "zip": zipped}
    return run.exports[file_format]
