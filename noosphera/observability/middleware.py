# FILE: noosphera/observability/middleware.py
from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    - Ensures/propagates a correlation/request ID from configured header (generates if absent)
    - Measures request latency
    - Emits HTTP metrics (counter + histogram) unless path == metrics_path
    - Adds response header with the request ID
    - Logs a structured access event carrying correlation_id, tenant_id, route, status, latency_ms

    Config:
      header_name: header used for request ID (e.g., "X-Request-ID")
      metrics_enabled: if True, emit Prometheus metrics
      metrics_path: path where metrics app is mounted (excluded from measurement)
      include_tenant_label: if True, include tenant id label in HTTP counter (cardinality caution)
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        header_name: str = "X-Request-ID",
        metrics_enabled: bool = True,
        metrics_path: str = "/metrics",
        include_tenant_label: bool = False,
    ) -> None:
        super().__init__(app)
        self.header_name = header_name
        self.metrics_enabled = metrics_enabled
        self.metrics_path = metrics_path
        self.include_tenant_label = include_tenant_label
        self._log = logging.getLogger("noosphera.access")

    async def dispatch(self, request: Request, call_next) -> Response:
        # Correlation / request ID
        rid: str = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.correlation_id = rid  # for DI and logging
        request.state.start_ns = time.perf_counter_ns()

        # Call downstream
        response: Response = await call_next(request)

        # Compute latency and set header
        end_ns = time.perf_counter_ns()
        latency_s = (end_ns - request.state.start_ns) / 1e9
        latency_ms = int(latency_s * 1000)
        response.headers[self.header_name] = rid

        # Resolve route template if available (fallback to concrete path)
        route = getattr(getattr(request.scope, "get", lambda *_: None)("route"), "path", None)
        route_path = route or request.url.path
        method = request.method
        code = int(getattr(response, "status_code", 0) or 0)

        # Tenant (populated by auth dependency during request execution)
        tenant = getattr(request.state, "tenant", None)
        tenant_id: Optional[str] = None
        if tenant is not None:
            tenant_id = str(getattr(tenant, "id", "") or "") or None

        # Metrics (skip self)
        if self.metrics_enabled and route_path != self.metrics_path:
            try:
                # Lazy import to avoid cycles
                from .metrics import on_request_complete

                on_request_complete(
                    route=route_path,
                    method=method,
                    code=code,
                    tenant=tenant_id,
                    latency_s=latency_s,
                    include_tenant=self.include_tenant_label,
                )
            except Exception:  # best-effort metrics
                logging.getLogger(__name__).debug("metrics emission failed", exc_info=False)

        # Access log
        self._log.info(
            "http_access",
            extra={
                "correlation_id": rid,
                "tenant_id": tenant_id,
                "method": method,
                "route": route_path,
                "path": request.url.path,
                "status": code,
                "latency_ms": latency_ms,
            },
        )
        return response
