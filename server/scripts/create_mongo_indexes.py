import asyncio
import os
import sys

# Add server to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.mongodb import init_mongodb, close_mongodb, get_mongodb
import pymongo

async def create_indexes():
    print("Connecting to MongoDB...")
    await init_mongodb()
    db = get_mongodb()
    
    print("Creating indexes for users collection...")
    await db.users.create_index([("email", pymongo.ASCENDING)], unique=True)
    
    print("Creating indexes for plan_history collection...")
    await db.plan_history.create_index([("user_id", pymongo.ASCENDING), ("generated_at", pymongo.DESCENDING)])
    await db.plan_history.create_index([("plan_type", pymongo.ASCENDING)])
    
    print("Creating indexes for chat_sessions collection...")
    await db.chat_sessions.create_index([("user_id", pymongo.ASCENDING)])
    
    print("Creating indexes for checkins collection...")
    await db.checkins.create_index([("user_id", pymongo.ASCENDING), ("week_date", pymongo.DESCENDING)])
    
    print("MongoDB indexes created successfully!")
    await close_mongodb()

if __name__ == "__main__":
    asyncio.run(create_indexes())
