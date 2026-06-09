import asyncio
import os
import sys

# Add server to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from database.sql import SessionLocal
from models.user import User
from core.logger import logger

async def send_weekly_digest():
    """Simulate sending a weekly digest to all users."""
    logger.info("Starting weekly digest script...")
    
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        for user in users:
            # Simulate email dispatch
            logger.info(f"[EMAIL] Sending weekly summary to {user.email}")
            logger.info(f"   Hello {user.name}, your current streak is {user.current_streak} days!")
            if user.bmi:
                logger.info(f"   Your last recorded BMI: {user.bmi} ({user.bmi_category})")
            
        logger.info(f"Successfully processed {len(users)} users.")

if __name__ == "__main__":
    asyncio.run(send_weekly_digest())
