from __future__ import annotations

import json
import logging
import sys
from typing import Any, Mapping

try:
    # FastAPI/Starlette types not required at import time
    from starlette.requests import Request  # type: ignore
except Exception:  # pragma: no cover
    Request = Any  # type: ignore


_EXCLUDE_STD_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "asctime",
}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        # include structured extras
        for k, v in record.__dict__.items():
            if k not in _EXCLUDE_STD_KEYS and not k.startswith("_"):
                if k == "exc_info":
                    continue
                payload[k] = v
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


def request_logger(request: Request, base_logger: str = "noosphera") -> logging.LoggerAdapter:
    """
    Return a LoggerAdapter bound with correlation_id and tenant_id (if available).
    """
    cid = getattr(request.state, "correlation_id", None)
    tenant = getattr(request.state, "tenant", None)
    tid = str(getattr(tenant, "id", "") or "") or None
    return logging.LoggerAdapter(logging.getLogger(base_logger), {"correlation_id": cid, "tenant_id": tid})
