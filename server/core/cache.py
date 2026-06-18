import json
import logging
import hashlib
from typing import Optional, Any
from config import settings
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.CACHE_ENABLED

    async def connect(self):
        if not self.redis_client:
            if not settings.REDIS_URL:
                logger.info("Redis URL not configured. Caching disabled.")
                return
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL, 
                    encoding="utf-8", 
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Connected to Redis for caching.")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_client = None

    def _generate_key(self, prefix: str, data: dict) -> str:
        # Create a stable string representation of the data
        # Sort keys to ensure consistent hash
        data_str = json.dumps(data, sort_keys=True)
        h = hashlib.sha256(data_str.encode()).hexdigest()
        return f"ayura:cache:{prefix}:{h}"

    async def get_plan(self, prefix: str, params: dict) -> Optional[dict]:
        if not self.enabled:
            return None
            
        if not self.redis_client:
            await self.connect()
        
        if not self.redis_client:
            return None
            
        key = self._generate_key(prefix, params)
        try:
            cached = await self.redis_client.get(key)
            if cached:
                logger.info(f"Cache hit for {key}")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None

    async def set_plan(self, prefix: str, params: dict, result: dict, expire: int = 86400):
        if not self.enabled:
            return
            
        if not self.redis_client:
            await self.connect()
            
        if not self.redis_client:
            return
            
        key = self._generate_key(prefix, params)
        try:
            await self.redis_client.set(key, json.dumps(result), ex=expire)
            logger.info(f"Cached result for {key}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
            logger.info("Redis connection closed.")

cache_manager = CacheManager()
