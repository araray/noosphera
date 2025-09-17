# FILE: noosphera/observability/metrics.py
from __future__ import annotations

from typing import Optional

from prometheus_client import Counter, Histogram, make_asgi_app

# Core HTTP metrics (prefixed for clarity)
HTTP_REQUESTS = Counter(
    "noosphera_http_requests_total",
    "Total HTTP requests",
    labelnames=["route", "method", "code", "tenant"],
)

HTTP_LATENCY = Histogram(
    "noosphera_http_request_latency_seconds",
    "HTTP request latency (seconds)",
    labelnames=["route", "method"],
)

# LLM metrics (Phase 1 seeds; to be emitted by provider/chat layers in later steps)
LLM_TOKENS = Counter(
    "noosphera_llm_tokens_total",
    "LLM tokens by direction",
    labelnames=["provider", "model", "direction"],  # direction: in|out|total
)


def make_metrics_app():
    """
    Return an ASGI app that serves Prometheus metrics at the mount path.
    """
    return make_asgi_app()


def on_request_complete(
    *,
    route: str,
    method: str,
    code: int,
    tenant: Optional[str],
    latency_s: float,
    include_tenant: bool,
) -> None:
    """
    Emit HTTP counter + latency histogram. Tenant label is gated to control cardinality.
    """
    tenant_label = (tenant or "unknown") if include_tenant else "disabled"
    HTTP_REQUESTS.labels(route=route, method=method, code=str(code), tenant=tenant_label).inc()
    HTTP_LATENCY.labels(route=route, method=method).observe(latency_s)
