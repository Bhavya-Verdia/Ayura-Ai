import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket
from core.logger import logger
from config import settings
import redis.asyncio as redis

class ConnectionManager:
    def __init__(self):
        # active_connections[user_id] = [WebSocket, ...]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # session_connections[session_id] = [WebSocket, ...]
        self.session_connections: Dict[str, List[WebSocket]] = {}
        
        self.redis = None
        self.pubsub = None
        if settings.REDIS_URL:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            logger.info("WebSocket Manager initialized with Redis Pub/Sub")

    async def _redis_listener(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    if channel.startswith("user:"):
                        user_id = channel.split(":")[1]
                        await self._local_send_personal_message(data, user_id)
                    elif channel.startswith("session:"):
                        session_id = channel.split(":")[1]
                        await self._local_broadcast_to_session(data, session_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def connect(self, websocket: WebSocket, user_id: str = None, session_id: str = None):
        await websocket.accept()
        
        # Subscribe to channels if first connection for this entity
        if self.redis:
            if not self.pubsub.subscribed:
                asyncio.create_task(self._redis_listener())
            
            if user_id and user_id not in self.active_connections:
                await self.pubsub.subscribe(f"user:{user_id}")
            if session_id and session_id not in self.session_connections:
                await self.pubsub.subscribe(f"session:{session_id}")

        if user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
        
        if session_id:
            if session_id not in self.session_connections:
                self.session_connections[session_id] = []
            self.session_connections[session_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str = None, session_id: str = None):
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if self.redis:
                    await self.pubsub.unsubscribe(f"user:{user_id}")
        
        if session_id and session_id in self.session_connections:
            self.session_connections[session_id].remove(websocket)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
                if self.redis:
                    await self.pubsub.unsubscribe(f"session:{session_id}")

    async def _local_send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def _local_broadcast_to_session(self, message: dict, session_id: str):
        if session_id in self.session_connections:
            for connection in self.session_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def send_personal_message(self, message: dict, user_id: str):
        if self.redis:
            await self.redis.publish(f"user:{user_id}", json.dumps(message))
        else:
            await self._local_send_personal_message(message, user_id)

    async def broadcast_to_session(self, message: dict, session_id: str):
        if self.redis:
            await self.redis.publish(f"session:{session_id}", json.dumps(message))
        else:
            await self._local_broadcast_to_session(message, session_id)

manager = ConnectionManager()
