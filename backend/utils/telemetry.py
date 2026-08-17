import uuid
import time
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager, contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource

from backend.utils.pii import sanitize_payload_for_logging

logger = logging.getLogger("capstone.telemetry")

resource = Resource.create({"service.name": "capstone-backend", "service.version": "1.0.0"})
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("capstone-tracer")


def generate_correlation_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    safe_attrs = sanitize_payload_for_logging(attributes or {})
    start_time = time.time()
    with tracer.start_as_current_span(name) as span:
        for k, v in safe_attrs.items():
            if isinstance(v, (str, bool, int, float)):
                span.set_attribute(k, v)
            else:
                span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            correlation_id = safe_attrs.get("correlation_id", "unknown")
            TraceRecorder.record(correlation_id, name, duration_ms, safe_attrs)


@asynccontextmanager
async def async_trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    safe_attrs = sanitize_payload_for_logging(attributes or {})
    start_time = time.time()
    with tracer.start_as_current_span(name) as span:
        for k, v in safe_attrs.items():
            if isinstance(v, (str, bool, int, float)):
                span.set_attribute(k, v)
            else:
                span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            correlation_id = safe_attrs.get("correlation_id", "unknown")
            TraceRecorder.record(correlation_id, name, duration_ms, safe_attrs)


class TraceRecorder:
    _traces = []

    @classmethod
    def record(cls, correlation_id: str, span_name: str, duration_ms: float, attributes: Dict[str, Any]):
        entry = {
            "correlation_id": correlation_id,
            "span_name": span_name,
            "duration_ms": round(duration_ms, 2),
            "timestamp": time.time(),
            "attributes": sanitize_payload_for_logging(attributes),
        }
        cls._traces.append(entry)
        if len(cls._traces) > 500:
            cls._traces.pop(0)

    @classmethod
    def get_traces_by_correlation_id(cls, correlation_id: str):
        return [t for t in cls._traces if t["correlation_id"] == correlation_id]

    @classmethod
    def get_recent_traces(cls, limit: int = 50):
        return cls._traces[-limit:]
