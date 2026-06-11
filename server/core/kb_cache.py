class KnowledgeBaseCache:
    def __init__(self):
        self.gym_exercises: list[dict] = []
        self.yoga_poses: list[dict] = []
        self.pranayama: list[dict] = []
        self.diet_foods: list[dict] = []
        self.panchakarma_protocols: list[dict] = []
        self.ayurvedic_remedies: list[dict] = []
        self.ayurvedic_medicines: list[dict] = []
        self.loaded: bool = False

    async def load(self, db):
        self.gym_exercises = await db.kb_gym_exercises.find({}, {"_id": 0}).to_list(None)
        self.yoga_poses = await db.kb_yoga_poses.find({}, {"_id": 0}).to_list(None)
        self.pranayama = await db.kb_pranayama.find({}, {"_id": 0}).to_list(None)
        self.diet_foods = await db.kb_diet_foods.find({}, {"_id": 0}).to_list(None)
        self.panchakarma_protocols = await db.kb_panchakarma_therapies.find({}, {"_id": 0}).to_list(None)
        self.ayurvedic_remedies = await db.kb_ayurvedic_remedies.find({}, {"_id": 0}).to_list(None)
        self.ayurvedic_medicines = await db.kb_ayurvedic_medicines.find({}, {"_id": 0}).to_list(None)
        self.loaded = True
        print(f"KB Cache loaded:\n"
              f"  {len(self.gym_exercises)} exercises\n"
              f"  {len(self.yoga_poses)} poses\n"
              f"  {len(self.pranayama)} pranayama\n"
              f"  {len(self.diet_foods)} foods\n"
              f"  {len(self.panchakarma_protocols)} PK protocols\n"
              f"  {len(self.ayurvedic_remedies)} remedies\n"
              f"  {len(self.ayurvedic_medicines)} medicines")

kb_cache = KnowledgeBaseCache()
