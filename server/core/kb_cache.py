"""Startup check that the bundled knowledge base is present and readable.

Every plan engine reads its own JSON file from `data/knowledge_base/` at import.
That file is the contract. This used to load seven `kb_*` Mongo collections and
hand them to the engines in preference to the files. Nothing in the repo ever
wrote six of them and all seven were empty in production (issue #59), so the
Mongo path never ran, and a hand-loaded collection would silently have outranked
the authored, test-guarded files.

What is left is the readiness signal: `/api/ready` reports 503 until `load` has
confirmed every file the engines import parses to a non-empty list.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"

# The files the plan engines read, keyed by the engine that reads them.
ENGINE_FILES = {
    "gym": ("gym_exercises.json",),
    "yoga": ("yoga_poses.json", "pranayama.json", "condition_protocols.json"),
    "diet": ("diet_foods.json",),
    "panchakarma": ("panchakarma_therapies.json", "panchakarma_protocols.json"),
    "remedies": ("home_remedies.json", "ayurvedic_medicines.json"),
}


def _count(filename: str) -> int:
    data = json.loads((_DATA_DIR / filename).read_text(encoding="utf-8"))
    return len(data)


class KnowledgeBaseCache:
    def __init__(self):
        self.loaded: bool = False

    async def load(self, db=None):
        counts = {}
        for files in ENGINE_FILES.values():
            for filename in files:
                try:
                    counts[filename] = _count(filename)
                except Exception:
                    logger.exception("Knowledge base file %s could not be read", filename)
                    counts[filename] = 0
        missing = [f for f, n in counts.items() if not n]
        if missing:
            # Not ready: the engine for this file would build plans from nothing.
            logger.error("Knowledge base incomplete, not ready: %s", ", ".join(missing))
            return
        self.loaded = True
        logger.info("Knowledge base: engines read the bundled files (%s)",
                    ", ".join(f"{f} {n}" for f, n in counts.items()))


kb_cache = KnowledgeBaseCache()
