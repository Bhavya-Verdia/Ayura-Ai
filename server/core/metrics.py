"""
Lightweight in-process observability metrics.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass
class LLMCallRecord:
    provider: str
    latency_ms: int
    success: bool
    prompt_chars: int
    response_chars: int
    json_mode: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MetricsRegistry:
    """Tiny process-local registry for runtime diagnostics."""

    def __init__(self, max_recent: int = 50):
        self._lock = Lock()
        self._llm_recent: deque[LLMCallRecord] = deque(maxlen=max_recent)
        self._llm_counts: dict[str, int] = defaultdict(int)
        self._llm_latency_total: dict[str, int] = defaultdict(int)

    def record_llm_call(
        self,
        provider: str,
        latency_ms: int,
        success: bool,
        prompt_chars: int,
        response_chars: int,
        json_mode: bool,
    ) -> None:
        record = LLMCallRecord(
            provider=provider,
            latency_ms=latency_ms,
            success=success,
            prompt_chars=prompt_chars,
            response_chars=response_chars,
            json_mode=json_mode,
        )
        key = f"{provider}:{'success' if success else 'error'}"
        with self._lock:
            self._llm_recent.append(record)
            self._llm_counts[key] += 1
            self._llm_latency_total[provider] += latency_ms

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            provider_totals: dict[str, int] = defaultdict(int)
            for key, count in self._llm_counts.items():
                provider, _status = key.split(":", 1)
                provider_totals[provider] += count

            avg_latency = {
                provider: round(self._llm_latency_total[provider] / total)
                for provider, total in provider_totals.items()
                if total
            }

            return {
                "llm": {
                    "counts": dict(self._llm_counts),
                    "avg_latency_ms": avg_latency,
                    "recent": [record.__dict__ for record in list(self._llm_recent)[-10:]],
                }
            }


metrics_registry = MetricsRegistry()
