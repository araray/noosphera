# FILE: noosphera/observability/tracing.py
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class _TracingCfgProto:
    enabled: bool
    otlp_endpoint: Optional[str]
    sample_ratio: float


def setup_tracing(tracing_settings: _TracingCfgProto) -> None:
    """
    Phase-1 stub: If enabled, attempt to initialize OpenTelemetry if available.
    Otherwise, no-op. Keeps a stable seam for future tracing without forcing a dep.
    """
    if not getattr(tracing_settings, "enabled", False):
        logger.debug("Tracing disabled")
        return

    try:
        # Optional imports; do not fail hard in Phase 1
        from opentelemetry import trace  # type: ignore
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # type: ignore
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased  # type: ignore

        # Configure provider with sampling
        sampler = TraceIdRatioBased(float(getattr(tracing_settings, "sample_ratio", 0.01)))
        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "noosphera"}), sampler=sampler)
        trace.set_tracer_provider(provider)

        # Optional OTLP exporter
        endpoint = getattr(tracing_settings, "otlp_endpoint", None) or ""
        exporter = OTLPSpanExporter(endpoint=endpoint) if endpoint else None
        if exporter:
            provider.add_span_processor(BatchSpanProcessor(exporter))

        logger.info("Tracing initialized (enabled=%s, otlp=%s)", True, bool(exporter))
    except Exception as exc:
        logger.warning("Tracing requested but not fully initialized: %s", exc)
