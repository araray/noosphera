from __future__ import annotations

import json
import logging
import sys
from typing import Any, Mapping


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def setup_logging(level: str, json: bool) -> None:
    """
    Minimal logging bootstrap. Honors level and a simple JSON mode for now.
    Uvicorn's own loggers inherit these settings.
    """
    lvl = getattr(logging, str(level).upper(), logging.INFO)

    # Clear existing handlers to avoid duplicates in reloaders.
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(fmt="%(asctime)s %(levelname)s %(name)s: %(message)s")
        )

    root.setLevel(lvl)
    root.addHandler(handler)

    # Align uvicorn loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(lvl)
