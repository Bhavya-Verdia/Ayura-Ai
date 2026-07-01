from core.logger import logger

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
    extract_xml_tags,
    get_session_summary,
    maybe_update_session_summary,
)
from ai.llm_client import llm_client
import re

router = APIRouter()

# Keep strong references to fire-and-forget background tasks so the event loop
# doesn't garbage-collect them mid-flight (a real hazard on Python 3.11+).
_bg_tasks: set = set()

def _spawn_bg(coro) -> None:
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

_ws_rate: dict[str, list[float]] = defaultdict(list)
_WS_LIMIT = 10
_WS_WINDOW = 60

async def _check_ws_rate(user_id: str) -> bool:
    """Rate-limit WebSocket messages per user.

    Prefers Redis (shared across all gunicorn workers — correct cross-process
    enforcement). Falls back to per-worker in-memory dict when Redis is absent.
    Without Redis, each worker tracks its own counter, so the effective limit
    per user is _WS_LIMIT × worker_count — acceptable as a degraded fallback.
    """
    from core.cache import cache_manager
    try:
        if cache_manager.redis_client:
            key = f"ws_rate:{user_id}"
            count = await cache_manager.redis_client.incr(key)
            if count == 1:
                await cache_manager.redis_client.expire(key, _WS_WINDOW)
            return count <= _WS_LIMIT
    except Exception:
        pass
    # In-memory fallback
    now = time.monotonic()
    _ws_rate[user_id] = [t for t in _ws_rate[user_id] if now - t < _WS_WINDOW]
    if len(_ws_rate[user_id]) >= _WS_LIMIT:
        return False
    _ws_rate[user_id].append(now)
    return True

async def _fetch_recent_history(db, session_id: str, user_id: str) -> list[dict]:
    """Recent messages as a list, for the agent's conversation memory."""
    try:
        cur = db.chat_messages.find(
            {"session_id": session_id, "user_id": user_id}
        ).sort("timestamp", 1).limit(10)
        return [{"role": m.get("role"), "content": m.get("content")}
                for m in await cur.to_list(10)]
    except Exception:
        return []

# Chat-template / role control tokens that are never legitimate user content and
# could be used to break out of the prompt. We strip THESE, but deliberately leave
# ordinary language and pasted code intact — the agent's system-prompt SAFETY RULES
# and the provider content filter are the real injection defense, and deleting words
# corrupts genuine messages (e.g. "help me forget everything stressful") or destroys
# a symptom log pasted in a code block.
_CONTROL_TOKENS = re.compile(r'<\|[^|]*\|>|<<\s*/?SYS\s*>>|\[/?INST\]', re.IGNORECASE)
_ROLE_PREFIX = re.compile(r'(?im)^\s*(system|assistant)\s*:\s*')

def _sanitize_prompt_input(text: str) -> str:
    text = _CONTROL_TOKENS.sub('', text or '')
    text = _ROLE_PREFIX.sub('', text)
    return text.strip()[:2000]

class ChatLLMResponse(BaseModel):
    response_text: str = Field(default="I'm here to help.")
    symptoms_to_log: list[str] = Field(default_factory=list)
    plans_to_adapt: list[str] = Field(default_factory=list)
    reminders_to_set: list[dict] = Field(default_factory=list)

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

    # Context gathering — these reads are independent, so run them concurrently.
    _t0 = time.perf_counter()
    active_plans, chat_ctx, history_list, history_summary = await asyncio.gather(
        fetch_active_plans(db, user.id),
        build_chat_context(db, user, session_id, safe_content),
        _fetch_recent_history(db, session_id, user.id),
        get_session_summary(db, session_id, user.id),
    )
    _ctx_ms = round((time.perf_counter() - _t0) * 1000)
    history_str, docs, context_text, top_conditions, dosha = chat_ctx
    sources = [{"source": d.get("metadata", {}).get("source", "Knowledge Base")} for d in docs]

    response_text = ""
    used_agent = False
    _t_gen = time.perf_counter()

    # ── PRIMARY: LangGraph ReAct agent (multi-step tools) ──
    try:
        from ai.agents.health_agent import run_health_agent
        response_text, agent_actions = await run_health_agent(
            db, user, active_plans, safe_content, history_list,
            knowledge=context_text, history_summary=history_summary,
        )
        if response_text:
            used_agent = True
            plans_adapting = [p for p in agent_actions.get("plans_adapting", [])
                              if p in ("gym", "yoga", "diet", "panchakarma", "remedies", "medicines")]
            if plans_adapting:
                await apply_chat_side_effects(db, user.id, [], plans_adapting, safe_content)
    except Exception as e:
        logger.warning("HTTP health agent failed (%s) — falling back to direct chat.", e)
        used_agent = False

    # ── FALLBACK: direct JSON path + tag-based tools ──
    if not used_agent:
        prompt = build_chat_prompt(
            user, safe_content, history_str, context_text, top_conditions, dosha, active_plans, stream_mode=False
        )
        try:
            response = await llm_client.generate(prompt=prompt, system_prompt="You are Ayura, the user's personal Ayurvedic health assistant who knows their full constitution and plans. Reply in JSON.", json_mode=True)
            resp_data = ChatLLMResponse.model_validate_json(response)
            response_text = resp_data.response_text
            await apply_chat_side_effects(
                db, user.id, resp_data.symptoms_to_log, resp_data.plans_to_adapt,
                safe_content, reminders=resp_data.reminders_to_set,
            )
        except Exception as e:
            logger.error(f"LLM Chat Error: {e}")
            response_text = "I'm having trouble processing that right now."

    await save_message(db, user.id, session_id, "ai", response_text, sources)
    logger.info("chat.http timing user=%s ctx=%dms gen=%dms agent=%s",
                user.id, _ctx_ms, round((time.perf_counter() - _t_gen) * 1000), used_agent)
    # Refresh the long-session rolling summary off the reply path (best-effort).
    _spawn_bg(maybe_update_session_summary(db, session_id, user.id))
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
    cursor = db.chat_messages.find({"session_id": session_id, "user_id": user.id}, {"_id": 0}).sort("timestamp", 1).limit(200)
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

            if not await _check_ws_rate(user.id):
                await websocket.send_json({"type": "error", "message": "Rate limit exceeded. Please wait before sending another message."})
                continue

            safe_content = _sanitize_prompt_input(data)

            # Refresh the user doc: a WS session is long-lived, and the profile,
            # medications, or vikriti_history can change mid-session (e.g. after an
            # in-chat plan adaptation). Tools read from `user`, so keep it current.
            try:
                fresh = await db.users.find_one({"_id": user.id})
                if fresh:
                    user = UserDocument(**fresh)
            except Exception:
                pass  # keep the last-known-good user on any refresh error

            # Send initial state
            await websocket.send_json({"type": "status", "message": "Analyzing..."})
            await save_message(db, user.id, session_id, "user", safe_content)

            # Run red-flag detection on the RAW message (like the HTTP path) so input
            # sanitization can never strip a term that signals a medical emergency.
            red_flags = await detect_red_flags(data, user.current_symptoms or [])
            if red_flags["has_red_flags"]:
                sources = [{"source": "Ayura AI safety triage", "red_flags": red_flags["matches"]}]
                await websocket.send_json({"type": "chunk", "content": red_flags["message"]})
                await websocket.send_json({"type": "done", "sources": sources})
                await save_message(db, user.id, session_id, "ai", red_flags["message"], sources)
                continue

            # These reads are independent, so run them concurrently.
            _t0 = time.perf_counter()
            active_plans, chat_ctx, history_list, history_summary = await asyncio.gather(
                fetch_active_plans(db, user.id),
                build_chat_context(db, user, session_id, safe_content),
                _fetch_recent_history(db, session_id, user.id),
                get_session_summary(db, session_id, user.id),
            )
            _ctx_ms = round((time.perf_counter() - _t0) * 1000)
            history_str, docs, context_text, top_conditions, dosha = chat_ctx

            sources = [{"source": d.get("metadata", {}).get("source", "Knowledge Base")} for d in docs]
            full_response = ""
            agent_actions: dict = {}
            used_agent = False
            _tool_count = 0
            _t_gen = time.perf_counter()

            # ── PRIMARY: LangGraph ReAct agent (multi-step tools) ──
            try:
                from ai.agents.health_agent import stream_health_agent
                async for kind, payload in stream_health_agent(
                    db, user, active_plans, safe_content, history_list,
                    knowledge=context_text, history_summary=history_summary,
                ):
                    if kind == "status":
                        _tool_count += 1
                        await websocket.send_json({"type": "status", "message": payload})
                    elif kind == "token":
                        full_response += payload
                        await websocket.send_json({"type": "chunk", "content": payload})
                    elif kind == "done":
                        full_response = payload.get("text") or full_response
                        agent_actions = payload.get("actions") or {}
                used_agent = bool(full_response)
            except Exception as agent_err:
                logger.warning("Health agent failed (%s) — falling back to direct chat.", agent_err)
                used_agent = False

            # ── FALLBACK: direct streaming + tag-based tools ──
            if not used_agent:
                await websocket.send_json({"type": "status", "message": "Generating..."})
                prompt = build_chat_prompt(
                    user, safe_content, history_str, context_text, top_conditions, dosha, active_plans, stream_mode=True
                )
                full_response = ""

                async def _do_stream() -> str:
                    collected = ""
                    async for chunk in llm_client.generate_stream(
                        prompt=prompt,
                        system_prompt="You are Ayura, the user's personal Ayurvedic health assistant who knows their full constitution and plans. Reply in plain text, do NOT use markdown code blocks.",
                        max_tokens=1000,
                    ):
                        collected += chunk
                        await websocket.send_json({"type": "chunk", "content": chunk})
                    return collected

                try:
                    full_response = await asyncio.wait_for(_do_stream(), timeout=90.0)
                except asyncio.TimeoutError:
                    logger.warning("Chat stream timed out for session %s", session_id)
                    await websocket.send_json({"type": "chunk", "content": "\n(Response timed out — please try again.)"})
                except Exception as e:
                    logger.error("Stream error: %s", e)
                    await websocket.send_json({"type": "chunk", "content": "\n(Error streaming response)"})

                response_text, symptoms_to_log, plans_to_adapt, reminders = extract_xml_tags(full_response)
                valid_plans = [p for p in plans_to_adapt if p in
                               ("gym", "yoga", "diet", "panchakarma", "remedies", "medicines")]
                # tag path: reminders not yet created — create them here
                created = await apply_chat_side_effects(db, user.id, symptoms_to_log, [], safe_content, reminders=reminders)
                agent_actions = {"reminders_set": created, "plans_adapting": valid_plans}
                full_response = response_text

            # ── Confirm actions → done → save → slow plan regen ──
            reminders_set = agent_actions.get("reminders_set", [])
            plans_adapting = [p for p in agent_actions.get("plans_adapting", [])
                              if p in ("gym", "yoga", "diet", "panchakarma", "remedies", "medicines")]
            if reminders_set or plans_adapting:
                await websocket.send_json({
                    "type": "actions",
                    "reminders_set": reminders_set,
                    "plans_adapting": plans_adapting,
                })

            await websocket.send_json({"type": "done", "sources": sources})
            await save_message(db, user.id, session_id, "ai", full_response, sources)
            logger.info("chat.ws timing user=%s ctx=%dms gen=%dms agent=%s tools=%d",
                        user.id, _ctx_ms, round((time.perf_counter() - _t_gen) * 1000),
                        used_agent, _tool_count)
            # Refresh the long-session rolling summary off the reply path (best-effort).
            _spawn_bg(maybe_update_session_summary(db, session_id, user.id))

            # Plan regeneration is slow (engine + LLM enricher) — run after the reply.
            # (Agent reminders are already created by the set_reminder tool; only
            # plan adaptation is executed here, for both paths.)
            if plans_adapting:
                await apply_chat_side_effects(db, user.id, [], plans_adapting, safe_content)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {session_id}")
