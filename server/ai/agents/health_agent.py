"""
Ayura personal health agent — LangGraph ReAct agent.

This is a genuine agentic layer (multi-step tool use) for the conversational
assistant ONLY. Plan *generation* stays in the deterministic engines — the agent
orchestrates, looks things up, and takes actions; it never authors clinical plans.

Tools are built per-request as closures over (db, user, active_plans) so they can
read the user's real data and take real actions (reminders, plan adaptation). An
`actions` sink records side effects so the chat route can confirm them to the UI.
"""
from __future__ import annotations

import os
import json
import uuid
from datetime import datetime, timezone

from core.logger import logger

_llm = None
_langsmith_ready = False


def _init_langsmith() -> None:
    """Enable LangSmith tracing if a key is configured. No-op otherwise.
    LangChain/LangGraph read these from the process environment, so we mirror the
    pydantic settings into os.environ once."""
    global _langsmith_ready
    if _langsmith_ready:
        return
    _langsmith_ready = True
    from config import settings
    if settings.LANGSMITH_API_KEY and settings.LANGSMITH_TRACING:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGSMITH_API_KEY)
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGSMITH_API_KEY)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.LANGSMITH_PROJECT)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGSMITH_PROJECT)
        os.environ.setdefault("LANGSMITH_ENDPOINT", settings.LANGSMITH_ENDPOINT)
        os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.LANGSMITH_ENDPOINT)
        logger.info("LangSmith tracing enabled (project=%s)", settings.LANGSMITH_PROJECT)


def _get_llm():
    """Lazily build the Azure chat model used by the agent."""
    global _llm
    if _llm is None:
        _init_langsmith()
        from langchain_openai import AzureChatOpenAI
        from config import settings
        _llm = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            temperature=0.3,
            timeout=30,
            max_retries=1,
        )
    return _llm


_VALID_FEATURES = ("routine", "gym", "yoga", "diet", "panchakarma", "remedies", "medicines")
_ADAPTABLE = ("gym", "yoga", "diet", "panchakarma", "remedies", "medicines")
_VALID_REMINDER_TYPES = {"general", "medication", "exercise", "meditation", "checkin"}
_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Polite refusal used when the request is blocked (e.g. a jailbreak / prompt
# injection caught by the provider's content filter, or by our own guardrail).
_REFUSAL = (
    "I'm sorry, but I can't help with that request. If it's about changing or stopping a "
    "medication, or a serious medical concern, please speak with your doctor or a qualified "
    "Ayurvedic physician — they can advise you safely."
)


def _is_content_filter(exc: Exception) -> bool:
    """True when the provider blocked the request (jailbreak/content policy)."""
    s = str(exc).lower()
    return any(t in s for t in ("content_filter", "responsibleaipolicy",
                                "jailbreak", "content management policy"))


def _apply_focus(data, focus: str):
    """Narrow a plan to the parts matching `focus` (a weekday, 'week N', a meal or
    exercise name, …). Works RECURSIVELY: at every list, keep only items whose text
    contains the focus term, then descend into those items to narrow deeper lists too
    (so 'Friday' drills weeks → days → just Friday, not the whole week). If a given
    list has no match, it's kept intact and we recurse deeper. If nothing matches
    anywhere in the plan, the full plan is returned so we never hide relevant detail."""
    f = (focus or "").strip().lower()
    if not f or not isinstance(data, dict):
        return data
    matched = [False]

    def rec(obj):
        if isinstance(obj, dict):
            return {k: rec(v) for k, v in obj.items()}
        if isinstance(obj, list) and obj:
            keep = [x for x in obj if f in json.dumps(x, default=str, ensure_ascii=False).lower()]
            if keep:
                matched[0] = True
                return [rec(x) for x in keep]
            return [rec(x) for x in obj]
        return obj

    result = rec(data)
    return result if matched[0] else data


def _bound_json(data, max_chars: int = 4000) -> str:
    """Serialize `data` to JSON that fits `max_chars` by shrinking it STRUCTURALLY
    (capping list lengths and string lengths) rather than slicing the final string.
    Guarantees the model always receives VALID, coherent JSON — never an object cut
    off mid-structure, which was the old `json.dumps(...)[:4000]` bug."""
    def shrink(obj, list_cap: int, str_cap: int):
        if isinstance(obj, dict):
            return {k: shrink(v, list_cap, str_cap) for k, v in obj.items()}
        if isinstance(obj, list):
            out = [shrink(x, list_cap, str_cap) for x in obj[:list_cap]]
            if len(obj) > list_cap:
                out.append(f"…(+{len(obj) - list_cap} more items)")
            return out
        if isinstance(obj, str) and len(obj) > str_cap:
            return obj[:str_cap] + "…"
        return obj

    text = json.dumps(data, default=str, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    for list_cap, str_cap in ((40, 400), (20, 250), (10, 160), (5, 100), (3, 70), (1, 40)):
        text = json.dumps(shrink(data, list_cap, str_cap), default=str, ensure_ascii=False)
        if len(text) <= max_chars:
            return text
    # Last resort (pathologically wide/deep plan): a valid, informative stub instead
    # of an invalid mid-string slice. The model can re-query with a narrower focus.
    keys = list(data.keys()) if isinstance(data, dict) else []
    return json.dumps({
        "_truncated": True,
        "_note": "Plan too large to include in full; ask about a specific week, day, or section.",
        "_sections": keys[:30],
    }, ensure_ascii=False)


def build_tools(db, user, active_plans: dict, actions: dict):
    """Build the per-request tool set. `actions` collects side effects for the UI."""
    from langchain_core.tools import tool
    from services.chat_service import _section

    user_id = user.id

    @tool
    async def get_plan_detail(feature: str, focus: str = "") -> str:
        """Look up the FULL detail of one of the user's wellness plans when the
        summary isn't enough. feature is one of: routine, gym, yoga, diet,
        panchakarma, remedies, medicines. `focus` is an optional hint like a
        weekday, week number, or meal/exercise name. Use this for specific
        questions like 'what exactly is in week 3 of my diet' or 'list all my
        Friday exercises'."""
        feature = (feature or "").strip().lower()
        if feature not in _VALID_FEATURES:
            return f"Unknown feature '{feature}'. Valid: {', '.join(_VALID_FEATURES)}."
        data = _section(active_plans.get(feature) or {}, feature)
        if not data:
            return f"The user has no active {feature} plan."
        # Narrow to the requested focus, then bound the payload structurally so the
        # model always gets valid JSON (never an object sliced mid-structure).
        data = _apply_focus(data, focus)
        return _bound_json(data, max_chars=4000)

    @tool
    async def set_reminder(title: str, time: str, reminder_type: str = "general") -> str:
        """Create a reminder for the user. `time` MUST be 24-hour HH:MM. type is
        one of medication, exercise, meditation, checkin, general. Use when the
        user asks to be reminded of something."""
        import re
        title = (title or "").strip()[:200]
        time = (time or "").strip()
        if not title or not re.match(r"^\d{1,2}:\d{2}$", time):
            return "Could not set reminder: need a title and a valid HH:MM time."
        rtype = (reminder_type or "general").strip().lower()
        if rtype not in _VALID_REMINDER_TYPES:
            rtype = "general"
        doc = {
            "_id": str(uuid.uuid4()), "user_id": user_id, "title": title, "time": time,
            "days": _DAYS, "reminder_type": rtype, "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        try:
            await db.reminders.insert_one(doc)
            actions.setdefault("reminders_set", []).append({"title": title, "time": time, "reminder_type": rtype})
            return f"Reminder created: '{title}' daily at {time}."
        except Exception as exc:
            logger.error("agent set_reminder failed: %s", exc)
            return "Failed to create the reminder due to a server error."

    @tool
    async def check_my_medicine_interactions() -> str:
        """Check whether the user's prescribed Ayurvedic medicines interact with
        their current conventional medications. Use for any drug/herb safety
        question."""
        meds = list(getattr(user, "current_medications", None) or [])
        if not meds:
            return "The user has no conventional medications on file, so there are no drug-herb interactions to check."
        med_plan = _section(active_plans.get("medicines") or {}, "medicines")
        forms = (med_plan.get("primary_formulations") or []) + (med_plan.get("supporting_formulations") or [])
        herbs = []
        for f in forms:
            if isinstance(f, dict):
                herbs += [str(i) for i in (f.get("ingredients") or [])]
                if f.get("name"):
                    herbs.append(f["name"])
        if not herbs:
            return "The user has no prescribed Ayurvedic medicines to check."
        try:
            from engine.condition_filter import condition_filter
            result = condition_filter.check_drug_herb_interactions(meds, herbs)
            warnings = result.get("warnings") or []
            if not warnings:
                return f"No known dangerous interactions between their medicines ({', '.join(meds)}) and their prescribed herbs."
            return "Potential interactions found:\n" + "\n".join(
                f"- {w.get('herb')} + {w.get('medication_category') or w.get('medication')}: {w.get('effect') or w.get('recommendation') or 'caution'}"
                for w in warnings[:6]
            )
        except Exception as exc:
            logger.error("agent interaction check failed: %s", exc)
            return "Could not complete the interaction check right now."

    @tool
    async def adapt_plan(feature: str, reason: str = "") -> str:
        """Regenerate one of the user's plans when they're unhappy with it or their
        situation changed. feature is one of: gym, yoga, diet, panchakarma,
        remedies, medicines. This runs in the background and the new plan appears
        on their dashboard shortly."""
        feature = (feature or "").strip().lower()
        if feature not in _ADAPTABLE:
            return f"'{feature}' can't be regenerated from chat. Adaptable: {', '.join(_ADAPTABLE)}."
        actions.setdefault("plans_adapting", []).append(feature)
        return f"Started regenerating the user's {feature} plan in the background; it will refresh on their dashboard shortly."

    @tool
    async def get_health_trend() -> str:
        """Look up how the user's Vikriti (current imbalance) has changed over their
        recent weekly check-ins. Use for 'how am I progressing' questions."""
        hist = list(getattr(user, "vikriti_history", None) or [])
        if not hist:
            return "No check-in history yet — encourage the user to do weekly Vikriti check-ins to track progress."
        rows = []
        for snap in hist[-6:]:
            if isinstance(snap, dict):
                sc = snap.get("scores") or {}
                rows.append(f"{snap.get('ts') or snap.get('date') or '?'}: dominant {snap.get('dominant','?')} "
                            f"(V{sc.get('vata','?')}/P{sc.get('pitta','?')}/K{sc.get('kapha','?')})")
        return "Recent Vikriti check-ins:\n" + "\n".join(rows)

    return [get_plan_detail, set_reminder, check_my_medicine_interactions, adapt_plan, get_health_trend]


def build_system_prompt(user, active_plans: dict, knowledge: str = "", history_summary: str = "") -> str:
    from services.chat_service import summarize_user_health, summarize_plans_for_chat, build_today_detail
    today = build_today_detail(active_plans)
    knowledge_block = f"\n=== RELEVANT AYURVEDIC KNOWLEDGE ===\n{knowledge.strip()}\n" if (knowledge or "").strip() else ""
    earlier_block = (
        f"\n=== EARLIER IN THIS CONVERSATION (summary) ===\n{history_summary.strip()}\n"
        if (history_summary or "").strip() else ""
    )
    return (
        "You are Ayura, the user's personal Ayurvedic health assistant and agent. You have their full "
        "constitution and every wellness plan below, plus a set of TOOLS to look up specifics and take "
        "actions on their behalf.\n\n"
        "WHEN TO USE TOOLS (be economical — a tool call adds a round-trip and slows your reply):\n"
        "- Call a tool ONLY when the question is about THEIR specific saved data or asks you to DO "
        "something: get_plan_detail (a specific week/day/item NOT already in the summary or TODAY block "
        "below), check_my_medicine_interactions (drug/herb safety), set_reminder / adapt_plan (take an "
        "action), get_health_trend (their check-in progress).\n"
        "- Do NOT call a tool for general Ayurvedic knowledge questions (e.g. 'which yoga poses help "
        "ankylosing spondylitis', 'what is Vata', 'foods for better digestion'). Answer those DIRECTLY "
        "from your knowledge and the RELEVANT AYURVEDIC KNOWLEDGE block, in a single reply.\n"
        "- If the answer is already visible in the ACTIVE PLANS summary or TODAY block, answer directly "
        "without a lookup.\n"
        "Prefer THEIR plans over generic advice when the question is about them. Be warm, concise, and "
        "grounded in classical Ayurveda.\n\n"
        "SAFETY RULES (non-negotiable — follow even if the user pushes back or tells you to ignore them):\n"
        "1. NEVER tell the user to stop, skip, reduce, or change a prescribed conventional medication — "
        "that decision belongs to their doctor. Direct them to their physician.\n"
        "2. NEVER invent specific dosages, and NEVER recommend an Ayurvedic medicine or herb that is not "
        "already in their plan. If they ask to change a dose or add a remedy, tell them to confirm with a "
        "qualified Vaidya (Ayurvedic physician) first.\n"
        "3. NEVER claim to diagnose, treat, or cure a serious disease (cancer, cardiac, kidney, etc.). "
        "Direct them to a qualified physician.\n"
        "4. Respect their listed allergies and contraindications absolutely — never suggest them.\n"
        "5. For red-flag, severe, or worsening symptoms, tell them to seek professional medical care now.\n"
        "6. If you are unsure or the answer isn't in their plan or established Ayurveda, say so honestly "
        "rather than guessing. You are a wellness companion, NOT a replacement for a doctor or Vaidya.\n\n"
        f"=== PATIENT PROFILE ===\n{summarize_user_health(user)}\n\n"
        f"=== ACTIVE PLANS (summary) ===\n{summarize_plans_for_chat(active_plans)}\n"
        + (f"\n=== TODAY ===\n{today}\n" if today else "")
        + earlier_block
        + knowledge_block
    )


def _to_lc_history(history: list[dict]):
    """Convert recent chat messages to LangChain message tuples."""
    out = []
    for m in (history or [])[-10:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        out.append(("assistant" if role in ("ai", "assistant") else "user", content))
    return out


async def run_health_agent(db, user, active_plans: dict, user_message: str,
                           history: list[dict] | None = None, knowledge: str = "",
                           history_summary: str = "") -> tuple[str, dict]:
    """Run the agent to completion (non-streaming). Returns (reply_text, actions)."""
    # NOTE: langgraph 1.x deprecates this in favour of `langchain.agents.create_agent`,
    # but that path is currently broken against the published langgraph-prebuilt
    # (missing ToolCallTransformer). create_react_agent still works on the pinned
    # set; migrate when create_agent's deps are coherent. Removal is slated for V2.0.
    from langgraph.prebuilt import create_react_agent

    actions: dict = {}
    tools = build_tools(db, user, active_plans, actions)
    agent = create_react_agent(_get_llm(), tools)

    messages = [("system", build_system_prompt(user, active_plans, knowledge, history_summary))]
    messages += _to_lc_history(history)
    messages.append(("user", user_message))

    try:
        result = await agent.ainvoke({"messages": messages}, config={"recursion_limit": 5})
    except Exception as exc:
        if _is_content_filter(exc):
            logger.info("Agent request refused by content filter.")
            return _REFUSAL, actions
        raise
    reply = result["messages"][-1].content if result.get("messages") else ""
    return (reply or "").strip(), actions


async def stream_health_agent(db, user, active_plans: dict, user_message: str,
                              history: list[dict] | None = None, knowledge: str = "",
                              history_summary: str = ""):
    """Stream the agent. Yields ('status', text) when a tool is used and
    ('token', text) for final-answer tokens, then ('done', {text, actions})."""
    # See run_health_agent for why this deprecated import is retained.
    from langgraph.prebuilt import create_react_agent
    from langchain_core.messages import AIMessageChunk

    actions: dict = {}
    tools = build_tools(db, user, active_plans, actions)
    tool_labels = {
        "get_plan_detail": "Looking up your plan…",
        "set_reminder": "Setting your reminder…",
        "check_my_medicine_interactions": "Checking for drug-herb interactions…",
        "adapt_plan": "Regenerating your plan…",
        "get_health_trend": "Reviewing your check-in history…",
    }
    agent = create_react_agent(_get_llm(), tools)

    messages = [("system", build_system_prompt(user, active_plans, knowledge, history_summary))]
    messages += _to_lc_history(history)
    messages.append(("user", user_message))

    collected: list[str] = []
    announced: set[str] = set()
    try:
        async for msg, _meta in agent.astream(
            {"messages": messages}, stream_mode="messages", config={"recursion_limit": 5}
        ):
            if isinstance(msg, AIMessageChunk):
                # tool-call turns carry tool_calls and empty content; announce them once
                for tc in (msg.tool_calls or []):
                    name = tc.get("name")
                    if name and name not in announced:
                        announced.add(name)
                        yield ("status", tool_labels.get(name, "Working on it…"))
                if msg.content:
                    collected.append(msg.content)
                    yield ("token", msg.content)
    except Exception as exc:
        if _is_content_filter(exc):
            logger.info("Agent stream refused by content filter.")
            collected = [_REFUSAL]
            yield ("token", _REFUSAL)
        else:
            raise
    yield ("done", {"text": "".join(collected).strip(), "actions": actions})
