"""
Ayura AI - Chat Service
Single source of truth for all chat AI logic, shared by both the HTTP
endpoint (POST /chat/message) and the WebSocket handler (/chat/ws/{session_id}).
"""

from __future__ import annotations

import json
import re
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field

from core.logger import logger


@dataclass
class ChatResult:
    """Result of processing a single chat message."""
    response_text: str
    sources: list[dict] = field(default_factory=list)
    symptoms_logged: list[str] = field(default_factory=list)
    plans_adapting: list[str] = field(default_factory=list)


# ── Personalised health context ──────────────────────────────────────────────
# The assistant needs to actually KNOW the user's constitution and what every
# plan prescribed — but the raw plans are ~700KB, far too big for the context
# window. These builders distil each feature down to the few actionable lines an
# Ayurvedic assistant would reference, so the chat behaves like a personal health
# agent without dumping JSON.

# Per-feature plan_data is stored nested under its section key, e.g. {"gym_plan": {...}}.
_SECTION_KEYS = {
    "routine": "routine_plan", "gym": "gym_plan", "yoga": "yoga_plan",
    "diet": "diet_plan", "panchakarma": "panchakarma_plan",
    "remedies": "home_remedies", "medicines": "medicines",
}


def _section(plan_data, feature: str):
    """Unwrap the feature's inner data, tolerating both nested and flat storage."""
    if not isinstance(plan_data, dict):
        return plan_data or {}
    inner = plan_data.get(_SECTION_KEYS.get(feature, ""))
    return inner if inner is not None else plan_data


def _fmt_list(items, n: int = 6) -> str:
    vals = [str(x) for x in (items or []) if x]
    return ", ".join(vals[:n])


def summarize_user_health(user) -> str:
    """Compact constitution + current-state profile from the user document."""
    g = lambda k: getattr(user, k, None)
    parts: list[str] = []
    if g("name"):
        parts.append(f"Name: {user.name}")
    bio = [str(g(k)) for k in ("age", "gender") if g(k)]
    if bio:
        parts.append("Age/Gender: " + ", ".join(bio))
    prak = g("prakriti_classical_name") or g("dosha_constitution_type") or g("dominant_dosha")
    if prak:
        parts.append(f"Prakriti (lifelong constitution): {prak}")
    ds = g("dosha_scores")
    if isinstance(ds, dict):
        parts.append(f"Prakriti scores: Vata {ds.get('vata','?')}% / Pitta {ds.get('pitta','?')}% / Kapha {ds.get('kapha','?')}%")
    if g("vikriti_dominant"):
        vk = f"Current imbalance (Vikriti): {user.vikriti_dominant}"
        if g("vikriti_secondary"):
            vk += f" + {user.vikriti_secondary}"
        parts.append(vk)
    agni_ama = []
    if g("agni_type"):
        agni_ama.append(f"Agni: {user.agni_type}")
    if g("ama_indicator"):
        agni_ama.append(f"Ama: {user.ama_indicator}")
    if g("ojas_level"):
        agni_ama.append(f"Ojas: {user.ojas_level}")
    if agni_ama:
        parts.append(", ".join(agni_ama))
    if g("manas_prakriti"):
        parts.append(f"Manas Prakriti: {user.manas_prakriti}")
    if g("medical_history"):
        parts.append(f"Medical conditions: {_fmt_list(user.medical_history, 8)}")
    if g("allergies"):
        parts.append(f"Allergies (NEVER recommend these): {_fmt_list(user.allergies, 8)}")
    if g("current_medications"):
        parts.append(f"Current medications: {_fmt_list(user.current_medications, 8)}")
    if g("current_symptoms"):
        parts.append(f"Reported symptoms: {_fmt_list(user.current_symptoms, 8)}")
    return "\n".join(parts) if parts else "Constitution not yet assessed."


def summarize_plans_for_chat(active_plans: dict) -> str:
    """Distil the user's current plans across all features into a few lines each."""
    lines: list[str] = []

    g = _section(active_plans.get("gym") or {}, "gym")
    if isinstance(g, dict) and g:
        days = [f"{d.get('day_name','?')}: {d.get('focus','')}".strip()
                for d in (g.get("weekly_schedule") or []) if isinstance(d, dict) and d.get("focus")]
        us = g.get("user_summary") or {}
        meta = [f"{k} {us[k]}" for k in ("gym_goal", "fitness_level") if us.get(k)]
        lines.append("FITNESS/GYM — " + ("; ".join(days[:7]) or "active plan")
                     + (f" ({', '.join(meta)})" if meta else ""))

    y = _section(active_plans.get("yoga") or {}, "yoga")
    if isinstance(y, dict) and y:
        sched = [d for d in (y.get("weekly_schedule") or []) if isinstance(d, dict)]
        excl = [e.get("name") for e in (y.get("pranayama_safety_exclusions") or []) if isinstance(e, dict)]
        s = f"YOGA/PRANAYAMA — active {len(sched)}-day routine" if sched else "YOGA/PRANAYAMA — active plan"
        if excl:
            s += f"; contraindicated for this user (do NOT suggest): {_fmt_list(excl, 5)}"
        lines.append(s)

    d = _section(active_plans.get("diet") or {}, "diet")
    if isinstance(d, dict) and d:
        weeks = d.get("four_week_plan") or d.get("diet_weeks") or []
        themes = [w.get("theme") or w.get("week_theme") for w in weeks if isinstance(w, dict)]
        themes = [t for t in themes if t]
        s = "DIET — " + (d.get("plan_title") or "4-week Ayurvedic plan")
        if themes:
            s += f" (progression: {_fmt_list(themes, 4)})"
        lines.append(s)
        pa = d.get("pathya_apathya") or {}
        if pa.get("pathya"):
            lines.append("  Favour: " + _fmt_list(pa["pathya"], 6))
        if pa.get("apathya"):
            lines.append("  Avoid: " + _fmt_list(pa["apathya"], 6))

    pk = _section(active_plans.get("panchakarma") or {}, "panchakarma")
    if isinstance(pk, dict) and pk:
        cd = pk.get("clinical_decisions") or {}
        approach = cd.get("shodhana_or_shamana")
        if isinstance(approach, dict):
            approach = approach.get("type")
        karma = cd.get("pradhana_karma_selected")
        if isinstance(karma, dict):
            karma = karma.get("primary")
        s = "PANCHAKARMA — " + (str(approach) if approach else "plan")
        if karma:
            s += f", {karma}"
        lines.append(s)

    rt = _section(active_plans.get("routine") or {}, "routine")
    if isinstance(rt, dict) and rt:
        dp = rt.get("dinacharya_protocol") or {}
        bits = []
        if dp.get("wake_time"):
            bits.append(f"wake {dp['wake_time']}")
        if dp.get("sleep_time"):
            bits.append(f"sleep {dp['sleep_time']}")
        if dp.get("agni_type"):
            bits.append(f"agni {dp['agni_type']}")
        lines.append("DAILY ROUTINE (Dinacharya) — " + (", ".join(bits) or "active plan"))

    rem = _section(active_plans.get("remedies") or {}, "remedies")
    if isinstance(rem, dict) and rem.get("symptoms_addressed"):
        items = []
        for sa in rem["symptoms_addressed"]:
            if not isinstance(sa, dict):
                continue
            remedy = sa.get("remedy")
            nm = remedy.get("name") if isinstance(remedy, dict) else None
            items.append(f"{sa.get('symptom_display') or sa.get('symptom_id','?')} → {nm or 'remedy'}")
        if items:
            lines.append("HOME REMEDIES — " + _fmt_list(items, 6))

    med = _section(active_plans.get("medicines") or {}, "medicines")
    if isinstance(med, dict) and med:
        forms = (med.get("primary_formulations") or []) + (med.get("supporting_formulations") or [])
        names = []
        for f in forms:
            if isinstance(f, dict) and f.get("name"):
                dose = f.get("dosage") or ""
                timing = f.get("timing") or ""
                detail = f" ({dose}{', ' + timing if timing else ''})" if dose else ""
                names.append(f["name"] + detail)
        if names:
            lines.append("AYURVEDIC MEDICINES — " + "; ".join(names[:8]))
        if med.get("chikitsa_approach"):
            lines.append(f"  Chikitsa approach: {med['chikitsa_approach']}")

    return "\n".join(lines) if lines else "No wellness plans generated yet — suggest the user generate them from the dashboard."


def build_today_detail(active_plans: dict) -> str:
    """Today-specific detail (this weekday's actual workout + medicine schedule) so
    the assistant can answer 'what exactly is my workout / meds today' precisely,
    without a separate lookup round-trip."""
    today = datetime.now(timezone.utc).strftime("%A")  # e.g. "Wednesday"
    out: list[str] = []

    g = _section(active_plans.get("gym") or {}, "gym")
    if isinstance(g, dict):
        weeks = g.get("four_week_plan") or []
        day = None
        if weeks and isinstance(weeks[0], dict):
            for dd in (weeks[0].get("days") or []):
                if isinstance(dd, dict) and str(dd.get("day_name", "")).lower() == today.lower():
                    day = dd
                    break
        if isinstance(day, dict):
            is_rest = str(day.get("type", "")).lower() == "rest" or "rest" in str(day.get("focus", "")).lower()
            if is_rest:
                out.append(f"Today ({today}) is a REST & RECOVERY day in their gym plan.")
            else:
                exs = [f"{e.get('exercise_name')} ({e.get('sets')}x{e.get('reps')})"
                       for e in (day.get("main_workout") or [])
                       if isinstance(e, dict) and e.get("exercise_name")]
                if exs:
                    out.append(f"Today's workout ({day.get('focus', '')}): " + "; ".join(exs[:8]))

    med = _section(active_plans.get("medicines") or {}, "medicines")
    if isinstance(med, dict):
        forms = (med.get("primary_formulations") or []) + (med.get("supporting_formulations") or [])
        sched = [f"{f.get('name')} — {f.get('timing') or 'as directed'}"
                 for f in forms if isinstance(f, dict) and f.get("name")]
        if sched:
            out.append("Today's medicine schedule: " + "; ".join(sched[:8]))

    return (f"(Today is {today})\n" + "\n".join(out)) if out else ""


async def save_message(db, user_id: str, session_id: str, role: str, content: str, sources: list | None = None) -> None:
    """Persist a chat message and upsert the session document."""
    if db is None:
        return
    now = datetime.now(timezone.utc)
    await db.chat_messages.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "timestamp": now,
    })
    await db.chat_sessions.update_one(
        {"session_id": session_id, "user_id": user_id},
        {
            "$set": {"updated_at": now},
            "$setOnInsert": {"session_id": session_id, "user_id": user_id, "created_at": now},
            "$inc": {"message_count": 1},
        },
        upsert=True,
    )


async def fetch_active_plans(db, user_id: str) -> dict:
    """Return the most recent plan of each type using a single aggregation query."""
    pipeline = [
        {"$match": {"user_id": user_id, "plan_type": {"$in": ["routine", "gym", "yoga", "diet", "panchakarma", "remedies", "medicines"]}}},
        {"$sort": {"generated_at": -1}},
        {"$group": {"_id": "$plan_type", "plan_data": {"$first": "$plan_data"}}},
    ]
    return {doc["_id"]: doc["plan_data"] async for doc in db.plan_history.aggregate(pipeline)}


async def build_chat_context(
    db,
    user,
    session_id: str,
    safe_content: str,
    history_limit: int = 20,
    max_history_chars: int = 4000,
) -> tuple[str, list[dict]]:
    """Retrieve chat history + RAG context for the LLM prompt.

    Returns:
        (history_str, rag_docs)
    """
    from engine.condition_filter import condition_filter
    from ai.rag_pipeline import rag_pipeline

    # --- Chat History (sliding window by character budget) ---
    cursor = db.chat_messages.find(
        {"session_id": session_id, "user_id": user.id}
    ).sort("timestamp", 1).limit(history_limit)
    messages = await cursor.to_list(length=history_limit)

    # Build history respecting a token/character budget
    history_parts = []
    budget = max_history_chars
    for m in reversed(messages):
        line = f"{m['role'].upper()}: {m['content']}"
        if len(line) > budget:
            break
        history_parts.insert(0, line)
        budget -= len(line)
    history_str = "\n".join(history_parts)

    # --- Symptom → Condition mapping ---
    words = safe_content.lower().replace(",", " ").replace(".", " ").replace("?", " ").split()
    ml_conditions = condition_filter.map_symptoms_to_conditions(words)
    top_conditions = [k for k, v in ml_conditions.items() if v > 0.3]

    # --- RAG Retrieval ---
    dosha = user.dominant_dosha or "pitta"
    query = f"{safe_content} {dosha} dosha " + " ".join(top_conditions)

    docs = await rag_pipeline.query(query, "ayurveda", n_results=3, dosha_filter=dosha)
    if not docs:
        docs = await rag_pipeline.query(query, "remedy", n_results=2)
    context_text = rag_pipeline.format_context(docs, max_chars=2000)

    return history_str, docs, context_text, top_conditions, dosha


def build_chat_prompt(
    user,
    safe_content: str,
    history_str: str,
    context_text: str,
    top_conditions: list[str],
    dosha: str,
    active_plans: dict,
    stream_mode: bool = False,
) -> str:
    """Build the LLM prompt for the chat message."""
    health_profile = summarize_user_health(user)
    plans_summary = summarize_plans_for_chat(active_plans)
    today_detail = build_today_detail(active_plans)

    persona = (
        "You are Ayura, the user's personal Ayurvedic health assistant and agent. You have "
        "FULL access to their constitution and every wellness plan they have generated (below). "
        "Use this context to give specific, personalised answers — reference their actual "
        "plans, dosha, Agni, conditions, prescribed medicines, diet, and routine. When they "
        "ask 'what should I eat / which exercise / which medicine', answer from THEIR plan, "
        "not generic advice. Respect their allergies and the contraindications listed. You can "
        "also take actions for them: set reminders, log symptoms, and regenerate a plan they "
        "are unhappy with (see the action tags below). Be warm, concise, and grounded in "
        "classical Ayurveda. You are not a substitute for a doctor — recommend professional "
        "care for red-flag or worsening symptoms."
    )

    today_block = f"\n=== TODAY ===\n{today_detail}\n" if today_detail else ""

    context_block = f"""=== YOUR PATIENT (full health profile) ===
{health_profile}
CURRENT CONDITIONS (ranked): {top_conditions}

=== THEIR ACTIVE WELLNESS PLANS ===
{plans_summary}
{today_block}
=== RELEVANT AYURVEDIC KNOWLEDGE (RAG) ===
{context_text}

=== RECENT CONVERSATION ===
{history_str}

=== USER MESSAGE ===
{safe_content}"""

    if stream_mode:
        return f"""{persona}

{context_block}

Respond helpfully, personally, and conversationally in plain text. DO NOT use markdown code blocks or JSON.

ACTIONS — you are an agent that can DO things, not just talk. When you tell the user you have done one of
these, you MUST append the matching tag at the very END of your message (the user never sees the tags; the
tag is what actually performs the action — without it, nothing happens):
- Logging a NEW symptom they report (e.g. "I have a headache"): <symptoms>headache</symptoms>
- Regenerating a plan they're unhappy with (e.g. "my diet is too hard", "redo my workout"): <plans>diet</plans>  (valid: gym, yoga, diet, panchakarma, remedies, medicines)
- Setting a reminder they ask for (e.g. "remind me to take Triphala at 10pm"): <reminder>Take Triphala Churna | 22:00 | medication</reminder>
  Reminder format: Title | HH:MM (24-hour) | type  — type is one of medication, exercise, meditation, checkin, general. One tag per reminder.

CRITICAL: if you say "reminder set", "I'll remind you", "I've logged that", or "regenerating your plan",
you MUST include the corresponding tag in the SAME message, or the action will silently fail. Only emit a
tag when the user actually requested that action.

Example — user: "remind me to drink warm water at 7am"
Your reply: "Done — I'll remind you to drink warm water at 7:00 AM. Warm water in the morning kindles your Agni. <reminder>Drink warm water | 07:00 | general</reminder>"
"""

    return f"""{persona}

{context_block}

Respond as their personal Ayurvedic assistant, using their profile and plans above.
If the user explicitly reports a new symptom, include it in symptoms_to_log.
If the user is unhappy with a specific plan, include the plan type in plans_to_adapt
(valid values: gym, yoga, diet, panchakarma, remedies, medicines).
If the user asks to be reminded of something, add it to reminders_to_set as
{{"title": "...", "time": "HH:MM", "reminder_type": "medication|exercise|meditation|checkin|general"}}.

OUTPUT FORMAT: Return ONLY valid JSON.
{{
    "response_text": "Your personalised conversational reply here",
    "symptoms_to_log": ["symptom1", "symptom2"],
    "plans_to_adapt": ["diet"],
    "reminders_to_set": [{{"title": "Take Triphala Churna", "time": "22:00", "reminder_type": "medication"}}]
}}
"""


async def apply_chat_side_effects(
    db,
    user_id: str,
    symptoms_to_log: list[str],
    plans_to_adapt: list[str],
    feedback_text: str,
    reminders: list[dict] | None = None,
) -> list[dict]:
    """Apply symptom logging, plan adaptations, and reminder creation as side
    effects. Runs after the response has been sent. Returns the reminders created
    (so the caller can confirm them to the user)."""
    now = datetime.now(timezone.utc)
    created_reminders: list[dict] = []

    for spec in parse_reminder_specs(reminders):
        import uuid
        doc = {
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": spec["title"],
            "time": spec["time"],
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "reminder_type": spec["reminder_type"],
            "is_active": True,
            "created_at": now,
        }
        try:
            await db.reminders.insert_one(doc)
            created_reminders.append({"title": spec["title"], "time": spec["time"], "reminder_type": spec["reminder_type"]})
            await db.timeline.insert_one({
                "user_id": user_id, "event_type": "reminder_set",
                "details": f"{spec['title']} at {spec['time']}", "source": "chat", "timestamp": now,
            })
        except Exception as exc:
            logger.error("Chat reminder creation failed: %s", exc)

    if symptoms_to_log:
        await db.users.update_one(
            {"_id": user_id},
            {"$addToSet": {"current_symptoms": {"$each": symptoms_to_log}}}
        )
        for symptom in symptoms_to_log:
            await db.timeline.insert_one({
                "user_id": user_id,
                "event_type": "symptom_logged",
                "details": symptom,
                "source": "chat",
                "timestamp": now,
            })
        try:
            from services.audit_service import log_symptom_change
            await log_symptom_change(db, user_id, "added", symptoms_to_log, source="chat")
        except Exception:
            pass

    if plans_to_adapt:
        # routine is intentionally excluded — it's not regenerable via the shared
        # engine path (it integrates gym/yoga + special prefs); regenerate it from
        # the dashboard. The agent still has full read access to it in context.
        valid_plans = [p for p in plans_to_adapt if p in ["gym", "yoga", "diet", "panchakarma", "remedies", "medicines"]]
        if valid_plans:
            await _adapt_plans(db, user_id, valid_plans, feedback_text)

    return created_reminders


async def _adapt_plans(db, user_id: str, plan_types: list[str], feedback: str) -> None:
    """Background task: regenerate the specified plans using the deterministic engine + enricher path."""
    from routes.plans import _generate_feature_via_engine, PLAN_DATA_KEYS
    from schemas.user_schema import UserDocument, PlanHistoryDocument
    from engine.seasonal import get_current_season
    import uuid

    user_dict = await db.users.find_one({"_id": user_id})
    if not user_dict:
        return

    user = UserDocument(**user_dict)
    season_info = get_current_season()
    user_profile = {
        "_user_id": user.id,
        "name": user.name, "gender": user.gender, "age": user.age,
        "height_cm": user.height_cm, "weight_kg": user.weight_kg,
        "bmi": user.bmi, "bmi_category": user.bmi_category,
        "dosha_scores": user.dosha_scores, "dominant_dosha": user.dominant_dosha,
        "secondary_dosha": user.secondary_dosha,
        "vikriti_dominant": user.vikriti_dominant,
        "vikriti_secondary": user.vikriti_secondary,
        "medical_history": user.medical_history or [],
        "current_symptoms": user.current_symptoms or [],
        "current_medications": user.current_medications or [],
        "allergies": user.allergies or [],
        "injuries_or_limitations": user.injuries_or_limitations or [],
        "fitness_level": user.fitness_level or "beginner",
        "activity_level": user.activity_level or "moderate",
        "pregnancy_or_nursing": user.pregnancy_or_nursing or False,
        "goal": user.goal,
        "current_season": season_info.name.lower(),
        "rating_preferences": {},
    }

    for plan_type in plan_types:
        try:
            enriched = await asyncio.wait_for(
                _generate_feature_via_engine(db, user_id, plan_type, user_profile),
                timeout=90,
            )
            plan_data_key = PLAN_DATA_KEYS.get(plan_type, f"{plan_type}_plan")
            model_used = enriched.get("enrichment_model") if isinstance(enriched, dict) else None
            full_plan_data = {
                "user_summary": {"name": user.name, "dominant_dosha": user.dominant_dosha},
                plan_data_key: enriched,
                "health_risks": [],
                "safety_checks": {"generation_mode": "engine_backed", "adaptation_feedback": feedback[:200]},
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generation_method": "agentic",
                "model_used": model_used or "engine+enricher",
            }
            plan_id = str(uuid.uuid4())
            history = PlanHistoryDocument(
                _id=plan_id, user_id=user_id, plan_type=plan_type,
                generation_method="agentic", model_used=full_plan_data.get("model_used"),
                plan_data=full_plan_data, generated_at=datetime.now(timezone.utc)
            )
            await db.plan_history.insert_one(history.model_dump(by_alias=True))
            logger.info("Adapted %s plan for user %s (via chat, engine path)", plan_type, user_id)
        except Exception as exc:
            logger.error("Chat adaptation failed for %s: %s", plan_type, exc)


_VALID_REMINDER_TYPES = {"general", "medication", "exercise", "meditation", "checkin"}


def parse_reminder_specs(raw: list) -> list[dict]:
    """Validate/normalise reminder specs from either the JSON or tag path.
    Each spec needs a non-empty title and an HH:MM time; type defaults to general."""
    out: list[dict] = []
    for r in raw or []:
        if not isinstance(r, dict):
            continue
        title = str(r.get("title", "")).strip()[:200]
        time = str(r.get("time", "")).strip()
        if not title or not re.match(r"^\d{1,2}:\d{2}$", time):
            continue
        rtype = str(r.get("reminder_type", "general")).strip().lower()
        out.append({
            "title": title,
            "time": time,
            "reminder_type": rtype if rtype in _VALID_REMINDER_TYPES else "general",
        })
    return out[:5]  # cap to avoid abuse


def extract_xml_tags(text: str) -> tuple[str, list[str], list[str], list[dict]]:
    """Extract <symptoms>, <plans>, and <reminder> action tags from streaming text.

    Returns:
        (cleaned_text, symptoms_list, plans_list, reminders_list)
    """
    symptoms: list[str] = []
    plans: list[str] = []
    reminders: list[dict] = []

    sym_match = re.search(r"<symptoms>(.*?)</symptoms>", text, re.IGNORECASE | re.DOTALL)
    if sym_match:
        symptoms = [s.strip() for s in sym_match.group(1).split(",") if s.strip()]
        text = re.sub(r"<symptoms>.*?</symptoms>", "", text, flags=re.IGNORECASE | re.DOTALL)

    plan_match = re.search(r"<plans>(.*?)</plans>", text, re.IGNORECASE | re.DOTALL)
    if plan_match:
        plans = [p.strip().lower() for p in plan_match.group(1).split(",") if p.strip()]
        text = re.sub(r"<plans>.*?</plans>", "", text, flags=re.IGNORECASE | re.DOTALL)

    raw_reminders = []
    for m in re.finditer(r"<reminder>(.*?)</reminder>", text, re.IGNORECASE | re.DOTALL):
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) >= 2:
            raw_reminders.append({
                "title": parts[0],
                "time": parts[1],
                "reminder_type": parts[2] if len(parts) > 2 else "general",
            })
    reminders = parse_reminder_specs(raw_reminders)
    text = re.sub(r"<reminder>.*?</reminder>", "", text, flags=re.IGNORECASE | re.DOTALL)

    return text.strip(), symptoms, plans, reminders
