"""
Send stdout/stderr to both the console and logs/inferno.log.
Call setup_logging() before importing modules that print during import.
"""
import sys
from pathlib import Path


def setup_logging(project_root: Path) -> None:
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "inferno.log"
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)

    class Tee:
        __slots__ = ("streams",)

        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            for s in self.streams:
                s.write(data)
                if hasattr(s, "flush"):
                    s.flush()

        def flush(self):
            for s in self.streams:
                s.flush()

        def fileno(self):
            return self.streams[0].fileno()

    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)
