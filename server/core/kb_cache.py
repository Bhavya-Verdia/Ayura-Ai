import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_KB_DOCS = 5000
_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"


def _load_json_file(filename: str) -> list[dict]:
    path = _DATA_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


class KnowledgeBaseCache:
    def __init__(self):
        self.gym_exercises: list[dict] = []
        self.yoga_poses: list[dict] = []
        self.pranayama: list[dict] = []
        self.condition_protocols: list[dict] = []
        self.diet_foods: list[dict] = []
        self.panchakarma_protocols: list[dict] = []
        self.ayurvedic_remedies: list[dict] = []
        self.ayurvedic_medicines: list[dict] = []
        self.loaded: bool = False

    async def load(self, db):
        self.gym_exercises = await db.kb_gym_exercises.find({}, {"_id": 0}).limit(MAX_KB_DOCS).to_list(MAX_KB_DOCS)
        self.yoga_poses = await db.kb_yoga_poses.find({}, {"_id": 0}).limit(MAX_KB_DOCS).to_list(MAX_KB_DOCS)
        self.pranayama = await db.kb_pranayama.find({}, {"_id": 0}).limit(MAX_KB_DOCS).to_list(MAX_KB_DOCS)
        self.diet_foods = await db.kb_diet_foods.find({}, {"_id": 0}).limit(MAX_KB_DOCS).to_list(MAX_KB_DOCS)
        self.panchakarma_protocols = await db.kb_panchakarma_therapies.find({}, {"_id": 0}).limit(MAX_KB_DOCS).to_list(MAX_KB_DOCS)
        self.ayurvedic_remedies = await db.kb_ayurvedic_remedies.find({}, {"_id": 0}).limit(MAX_KB_DOCS).to_list(MAX_KB_DOCS)
        self.ayurvedic_medicines = await db.kb_ayurvedic_medicines.find({}, {"_id": 0}).limit(MAX_KB_DOCS).to_list(MAX_KB_DOCS)

        # Condition protocols always come from the local JSON file (no MongoDB collection)
        self.condition_protocols = _load_json_file("condition_protocols.json")

        self.loaded = True
        logger.info(
            "KB Cache loaded: %d exercises, %d poses, %d pranayama, %d foods, "
            "%d PK protocols, %d remedies, %d medicines, %d condition protocols",
            len(self.gym_exercises), len(self.yoga_poses), len(self.pranayama),
            len(self.diet_foods), len(self.panchakarma_protocols),
            len(self.ayurvedic_remedies), len(self.ayurvedic_medicines),
            len(self.condition_protocols),
        )


kb_cache = KnowledgeBaseCache()
