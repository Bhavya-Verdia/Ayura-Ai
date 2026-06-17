from core.logger import logger

from datetime import datetime, timezone
import asyncio
import time
import uuid
from collections import defaultdict
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Cookie
from pydantic import BaseModel, Field

from schemas.plan_schema import ChatMessage, ChatResponse
from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb
from services.safety_service import detect_red_flags

from services.chat_service import (
    save_message,
    fetch_active_plans,
    build_chat_context,
    build_chat_prompt,
    apply_chat_side_effects,
    extract_xml_tags
)
from ai.llm_client import llm_client
import re

router = APIRouter()

_ws_rate: dict[str, list[float]] = defaultdict(list)
_WS_LIMIT = 10
_WS_WINDOW = 60

def _check_ws_rate(user_id: str) -> bool:
    now = time.monotonic()
    _ws_rate[user_id] = [t for t in _ws_rate[user_id] if now - t < _WS_WINDOW]
    if len(_ws_rate[user_id]) >= _WS_LIMIT:
        return False
    _ws_rate[user_id].append(now)
    return True

def _sanitize_prompt_input(text: str) -> str:
    text = re.sub(r'(?i)(system\s*:|assistant\s*:|<<\s*SYS\s*>>|<\|.*?\|>)', '', text)
    text = re.sub(r'```[\s\S]*?```', '[code removed]', text)
    text = re.sub(r'(?i)(ignore\s+(all\s+)?previous\s+instructions?|forget\s+(everything|all)|jailbreak|bypass)', '', text)
    return text.strip()[:2000]

class ChatLLMResponse(BaseModel):
    response_text: str = Field(default="I'm here to help.")
    symptoms_to_log: list[str] = Field(default_factory=list)
    plans_to_adapt: list[str] = Field(default_factory=list)

@router.post("/message", response_model=ChatResponse)
async def send_message(msg: ChatMessage, user: UserDocument = Depends(get_current_user)):
    db = get_mongodb()
    session_id = msg.session_id or str(uuid.uuid4())
    safe_content = _sanitize_prompt_input(msg.content)
    await save_message(db, user.id, session_id, "user", safe_content)

    red_flags = await detect_red_flags(msg.content, user.current_symptoms or [])
    if red_flags["has_red_flags"]:
        response_text = red_flags["message"]
        sources = [{"source": "Ayura AI safety triage", "red_flags": red_flags["matches"]}]
        await save_message(db, user.id, session_id, "ai", response_text, sources)
        return ChatResponse(response=response_text, sources=sources, session_id=session_id)

    # Context gathering
    active_plans = await fetch_active_plans(db, user.id)
    history_str, docs, context_text, top_conditions, dosha = await build_chat_context(
        db, user, session_id, safe_content
    )

    prompt = build_chat_prompt(
        user, safe_content, history_str, context_text, top_conditions, dosha, active_plans, stream_mode=False
    )

    try:
        response = await llm_client.generate(prompt=prompt, system_prompt="You are an Ayurvedic AI. Reply in JSON.", json_mode=True)
        resp_data = ChatLLMResponse.model_validate_json(response)
        response_text = resp_data.response_text
        symptoms_to_log = resp_data.symptoms_to_log
        plans_to_adapt = resp_data.plans_to_adapt
    except Exception as e:
        logger.error(f"LLM Chat Error: {e}")
        response_text = "I'm having trouble processing that right now."
        symptoms_to_log = []
        plans_to_adapt = []

    # Handle Function Execution
    await apply_chat_side_effects(db, user.id, symptoms_to_log, plans_to_adapt, safe_content)

    sources = [{"source": d.get("metadata", {}).get("source", "Knowledge Base")} for d in docs]
    await save_message(db, user.id, session_id, "ai", response_text, sources)

    return ChatResponse(response=response_text, sources=sources, session_id=session_id)

@router.get("/sessions")
async def get_chat_sessions(user: UserDocument = Depends(get_current_user)):
    db = get_mongodb()
    if db is None:
        return []
    pipeline = [
        {"$match": {"user_id": user.id}},
        {"$sort": {"updated_at": -1}},
        {"$limit": 50},
        {"$lookup": {
            "from": "chat_messages",
            "let": {"sid": "$session_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$session_id", "$$sid"]},
                    {"$eq": ["$role", "user"]},
                ]}}},
                {"$sort": {"timestamp": 1}},
                {"$limit": 1},
            ],
            "as": "first_msgs",
        }},
        {"$project": {
            "session_id": 1, "message_count": 1, "updated_at": 1,
            "first_msg": {"$arrayElemAt": ["$first_msgs", 0]},
        }},
    ]
    docs = await db.chat_sessions.aggregate(pipeline).to_list(length=50)
    return [
        {
            "session_id": s["session_id"],
            "preview": (s["first_msg"]["content"][:80] + "...") if s.get("first_msg") else "New chat",
            "message_count": s.get("message_count", 0),
            "updated_at": s["updated_at"].isoformat() if s.get("updated_at") else None,
        }
        for s in docs
    ]

@router.get("/sessions/{session_id}")
async def get_session_messages(session_id: str, user: UserDocument = Depends(get_current_user)):
    db = get_mongodb()
    if db is None: return []
    cursor = db.chat_messages.find({"session_id": session_id, "user_id": user.id}, {"_id": 0}).sort("timestamp", 1)
    messages = []
    async for doc in cursor:
        messages.append({
            "role": doc["role"], "content": doc["content"], "sources": doc.get("sources", []),
            "timestamp": doc.get("timestamp", "").isoformat() if doc.get("timestamp") else None,
        })
    return messages


@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str, ayura_access: str = Cookie(None)):
    await websocket.accept()

    final_token = ayura_access
    if not final_token:
        await websocket.close(code=1008)
        return
        
    from services.auth_service import get_current_user_id
    try:
        user_id = get_current_user_id(final_token)
    except Exception:
        await websocket.close(code=1008)
        return
        
    db = get_mongodb()
    user_dict = await db.users.find_one({"_id": user_id})
    if not user_dict:
        await websocket.close(code=1008)
        return
        
    from schemas.user_schema import UserDocument
    user = UserDocument(**user_dict)
    
    try:
        while True:
            data = await websocket.receive_text()

            if not _check_ws_rate(user.id):
                await websocket.send_json({"type": "error", "message": "Rate limit exceeded. Please wait before sending another message."})
                continue

            safe_content = _sanitize_prompt_input(data)

            # Send initial state
            await websocket.send_json({"type": "status", "message": "Analyzing..."})
            await save_message(db, user.id, session_id, "user", safe_content)
            
            red_flags = await detect_red_flags(safe_content, user.current_symptoms or [])
            if red_flags["has_red_flags"]:
                sources = [{"source": "Ayura AI safety triage", "red_flags": red_flags["matches"]}]
                await websocket.send_json({"type": "chunk", "content": red_flags["message"]})
                await websocket.send_json({"type": "done", "sources": sources})
                await save_message(db, user.id, session_id, "ai", red_flags["message"], sources)
                continue
                
            active_plans = await fetch_active_plans(db, user.id)
            history_str, docs, context_text, top_conditions, dosha = await build_chat_context(
                db, user, session_id, safe_content
            )

            prompt = build_chat_prompt(
                user, safe_content, history_str, context_text, top_conditions, dosha, active_plans, stream_mode=True
            )

            await websocket.send_json({"type": "status", "message": "Generating..."})
            full_response = ""
            
            try:
                async for chunk in llm_client.generate_stream(prompt=prompt, system_prompt="You are an Ayurvedic AI. Reply in plain text, do NOT use markdown code blocks.", max_tokens=1000):
                    full_response += chunk
                    await websocket.send_json({"type": "chunk", "content": chunk})
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await websocket.send_json({"type": "chunk", "content": "\n(Error streaming response)"})
            
            # Post-process for tags
            response_text, symptoms_to_log, plans_to_adapt = extract_xml_tags(full_response)
            sources = [{"source": d.get("metadata", {}).get("source", "Knowledge Base")} for d in docs]
            
            await websocket.send_json({"type": "done", "sources": sources})
            await save_message(db, user.id, session_id, "ai", response_text, sources)
            
            await apply_chat_side_effects(db, user.id, symptoms_to_log, plans_to_adapt, safe_content)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {session_id}")
