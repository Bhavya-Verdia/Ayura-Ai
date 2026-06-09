"""
Ayura AI - Chroma telemetry shim
Disables product telemetry calls to avoid noisy runtime logging in local dev.
"""

from chromadb.config import System
from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from overrides import override


class NullTelemetry(ProductTelemetryClient):
    """No-op telemetry client used for local development stability."""

    def __init__(self, system: System):
        super().__init__(system)

    @override
    def capture(self, event: ProductTelemetryEvent) -> None:
        return None
