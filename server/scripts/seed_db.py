"""
Ayura AI - Database Seeding Script
Seeds MongoDB with knowledge base JSONs.
Run: python scripts/seed_db.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/ayura")
DB_NAME = os.getenv("MONGO_DB", "ayura")
KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge"


async def seed_collection(db, collection_name: str, json_file: str, key: str):
    data = json.loads((KNOWLEDGE_DIR / json_file).read_text(encoding="utf-8"))
    
    if isinstance(data, list):
        docs = data
    else:
        docs = data.get(key, [])
        
    if not docs:
        print(f"  ⚠️  No documents found in {json_file}[{key}]")
        return

    col = db[collection_name]
    await col.delete_many({})  # Clear existing
    await col.insert_many(docs)
    print(f"  ✅ {collection_name}: {len(docs)} documents seeded")


async def seed_all():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("\n🌱 Seeding MongoDB knowledge base...")
    await seed_collection(db, "gym_routines", "gym_routines.json", "routines")
    await seed_collection(db, "yoga_plans", "yoga_plans.json", "plans")
    await seed_collection(db, "diet_plans", "diet_plans.json", "plans")
    await seed_collection(db, "panchakarma_plans", "panchakarma_plans.json", "protocols")
    await seed_collection(db, "home_remedies", "home_remedies.json", "remedies")
    await seed_collection(db, "ritucharya_seasonal", "ritucharya_seasonal.json", "seasons")
    await seed_collection(db, "drug_herb_interactions", "drug_herb_interactions.json", "interactions")

    # Seed dosha profiles
    dosha_data = json.loads((KNOWLEDGE_DIR / "dosha_profiles.json").read_text(encoding="utf-8"))
    await db["dosha_profiles"].delete_many({})
    await db["dosha_profiles"].insert_many([
        {"dosha": k, **v} for k, v in dosha_data.get("doshas", {}).items()
    ])
    await db["dosha_quiz_questions"].delete_many({})
    await db["dosha_quiz_questions"].insert_many(dosha_data.get("doshaQuizQuestions", []))
    print(f"  ✅ dosha_profiles: 3 documents seeded")
    print(f"  ✅ dosha_quiz_questions: {len(dosha_data.get('doshaQuizQuestions', []))} questions seeded")

    client.close()
    print("\n🎉 MongoDB seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_all())
