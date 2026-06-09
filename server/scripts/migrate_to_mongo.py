import json
import asyncio
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config import settings

import certifi

async def migrate_data():
    client = AsyncIOMotorClient(settings.MONGO_URL, tlsCAFile=certifi.where())
    db = client[settings.MONGO_DB]
    
    files_to_collections = {
        "diet_foods.json": "kb_diet_foods",
        "gym_exercises.json": "kb_gym_exercises",
        "yoga_poses.json": "kb_yoga_poses",
        "pranayama.json": "kb_pranayama",
        "panchakarma_therapies.json": "kb_panchakarma_therapies",
        "ayurvedic_remedies.json": "kb_ayurvedic_remedies"
    }
    
    for filename, col_name in files_to_collections.items():
        filepath = BASE_DIR / "data" / "knowledge_base" / filename
        if not filepath.exists():
            print(f"Skipping {filename} - file not found.")
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not data:
            print(f"Skipping {filename} - empty.")
            continue
            
        # Drop existing collection so we don't duplicate
        await db[col_name].drop()
        
        # Insert all documents
        # Pydantic/Motor expects _id to be present or it generates one.
        # Our JSON files have "id". We can let Mongo generate _id and keep "id" as the string ID.
        result = await db[col_name].insert_many(data)
        print(f"Migrated {len(result.inserted_ids)} records from {filename} into {col_name}")
        
    client.close()

if __name__ == "__main__":
    print("Starting MongoDB Migration for Knowledge Base...")
    asyncio.run(migrate_data())
    print("Migration Complete.")
