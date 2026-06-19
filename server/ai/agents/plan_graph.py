"""
Ayura AI - LangGraph Orchestration System
4-Agent pipeline: Supervisor → Fitness + Ayurveda + Nutrition + Remedy agents
"""

from typing import TypedDict, Annotated, Optional
import json
import operator
import re
from langgraph.graph import StateGraph, END

from ai.llm_client import llm_client
from ai.rag_pipeline import rag_pipeline
from ai.prompts.system_prompts import (
    SUPERVISOR_PROMPT, FITNESS_AGENT_PROMPT, AYURVEDA_AGENT_PROMPT,
    NUTRITION_AGENT_PROMPT, REMEDY_AGENT_PROMPT,
)
from engine.bmi_calculator import bmi_calculator
from engine.calorie_calculator import calorie_calculator
from engine.dosha_analyzer import dosha_analyzer
from engine.condition_filter import condition_filter
from services.seasonal_service import build_seasonal_guidance


# ─────────────────────────────────────────

# STATE DEFINITION
# ─────────────────────────────────────────
class PlanState(TypedDict):
    user_profile: dict
    ml_analysis: dict           # Tier 1 ML outputs
    rag_context: dict           # Tier 2 RAG retrieved chunks
    gym_plan: Optional[dict]    # Tier 3+4 Fitness Agent output
    yoga_plan: Optional[dict]   # Tier 3+4 Ayurveda Agent output
    diet_plan: Optional[dict]   # Tier 3+4 Nutrition Agent output
    panchakarma_plan: Optional[dict]
    home_remedies: Optional[list]
    medicines: Optional[list]
    seasonal_guidance: Optional[dict]
    daily_tip: Optional[str]
    health_risks: list
    safety_checks: dict
    model_used: Optional[str]
    errors: Annotated[list, operator.add]
    feedback: Optional[str]           # For Feature 10: Adaptive Plan Evolution
    is_adaptation: bool               # Flag for feedback loop
    adaptation_summary: Optional[str] # GenAI summary of changes made
    other_plans_context: Optional[dict] # For cross-agent awareness


STOPWORDS = {
    "a", "an", "and", "after", "all", "any", "during", "for", "if", "in",
    "into", "is", "of", "on", "only", "or", "the", "to", "under", "with",
    "without",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()

def _sanitize_prompt_input(text: str) -> str:
    text = re.sub(r'(?i)(system\s*:|assistant\s*:|<<\s*SYS\s*>>|<\|.*?\|>)', '', text)
    text = re.sub(r'(?i)(ignore\s+(all\s+)?previous\s+instructions?|forget\s+(everything|all)|jailbreak|bypass)', '', text)
    return text.strip()[:2000]


def _canonicalize_token(token: str) -> str:
    token = token.lower().strip()
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)]
    return token


def _extract_tokens(value: str) -> set[str]:
    raw_tokens = _normalize_text(value).split()
    return {
        _canonicalize_token(token)
        for token in raw_tokens
        if len(token) > 2 and token not in STOPWORDS
    }


def _constraint_matches_text(text: str, constraint: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_constraint = _normalize_text(constraint)
    if not normalized_text or not normalized_constraint:
        return False
    if normalized_constraint in normalized_text:
        return True

    text_tokens = _extract_tokens(text)
    constraint_tokens = _extract_tokens(constraint)
    if not text_tokens or not constraint_tokens:
        return False

    overlap = text_tokens.intersection(constraint_tokens)
    if len(overlap) >= 2:
        return True

    if len(constraint_tokens) == 1 and overlap:
        return True

    return any(token in text_tokens for token in constraint_tokens if len(token) >= 8)


def _collect_plan_strings(value) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(_collect_plan_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(_collect_plan_strings(item))
    return strings


def _find_constraint_hits(entries: list[str], constraints: list[str]) -> list[str]:
    hits: list[str] = []
    for entry in entries:
        for constraint in constraints:
            if _constraint_matches_text(entry, constraint):
                hits.append(constraint)
    return sorted(set(hits))


def _extract_remedy_ingredients(remedies: list[dict]) -> list[str]:
    ingredients: list[str] = []
    for remedy in remedies:
        for ingredient in remedy.get("ingredients", []):
            if isinstance(ingredient, str):
                ingredients.append(ingredient)
    return ingredients


# ─────────────────────────────────────────
# TIER 1: ML ANALYSIS NODE
# ─────────────────────────────────────────
async def ml_analysis_node(state: PlanState) -> dict:
    """Run all ML models to generate structured user analysis."""
    profile = state["user_profile"]

    # BMI
    bmi_result = bmi_calculator.calculate(
        profile.get("weight_kg", 70),
        profile.get("height_cm", 170)
    ) if profile.get("weight_kg") and profile.get("height_cm") else {}

    # Dosha analysis
    dosha_result = dosha_analyzer.analyze(
        profile.get("dosha_scores") or {"vata": 33, "pitta": 33, "kapha": 34}
    )

    # Vikriti — current imbalance state (takes priority over Prakriti for plan correction)
    vikriti_dominant = profile.get("vikriti_dominant") or dosha_result.get("dominant_dosha", "pitta")
    vikriti_secondary = profile.get("vikriti_secondary")
    vikriti_scores = profile.get("vikriti_scores") or profile.get("dosha_scores") or {}
    constitution_type = profile.get("dosha_constitution_type") or dosha_result.get("constitution_type", "")
    immediate_focus = profile.get("dosha_immediate_focus") or ""
    key_signals = profile.get("dosha_key_signals") or []
    checkin_count = profile.get("checkin_count", 0)

    # Calorie calculation
    calorie_result = calorie_calculator.calculate(
        gender=profile.get("gender", "female"),
        age=profile.get("age", 30),
        weight_kg=profile.get("weight_kg", 70),
        height_cm=profile.get("height_cm", 165),
        activity_level=profile.get("activity_level", "moderate"),
        goal=profile.get("goal", "general_wellness"),
    ) if profile.get("weight_kg") else {}

    # Health risk prediction
    risk_result = condition_filter.predict_health_risks(
        bmi=bmi_result.get("bmi", 22),
        age=profile.get("age", 30),
        gender=profile.get("gender", "female"),
        dosha=dosha_result.get("dominant_dosha", "pitta"),
        activity_level=profile.get("activity_level", "moderate"),
        medical_history=profile.get("medical_history", [])
    )

    # Symptom mapping
    symptom_result = condition_filter.map_symptoms_to_conditions(
        profile.get("current_symptoms", [])
    )

    # Exercise ranking
    exercise_result = condition_filter.recommend_exercises(
        dosha=dosha_result.get("dominant_dosha", "pitta"),
        bmi_category=bmi_result.get("category", "normal"),
        fitness_level=profile.get("fitness_level", "beginner"),
        medical_history=profile.get("medical_history", []),
        goal=profile.get("goal", "general_wellness")
    )

    # Medical constraints
    constraint_result = condition_filter.get_constraints(
        profile.get("medical_history", [])
    )

    return {
        "ml_analysis": {
            "bmi": bmi_result,
            "dosha": dosha_result,
            "vikriti": {
                "dominant": vikriti_dominant,
                "secondary": vikriti_secondary,
                "scores": vikriti_scores,
                "constitution_type": constitution_type,
                "immediate_focus": immediate_focus,
                "key_signals": key_signals,
                "checkin_count": checkin_count,
            },
            "calories": calorie_result,
            "health_risks": risk_result,
            "symptom_conditions": symptom_result,
            "exercise_rankings": exercise_result[:10],
            "medical_constraints": constraint_result,
        },
        "health_risks": [
            {"condition": k, "probability": v}
            for k, v in risk_result.items()
            if v > 0.4
        ],
    }


# ─────────────────────────────────────────
# TIER 2: RAG RETRIEVAL NODE
# ─────────────────────────────────────────
async def rag_retrieval_node(state: PlanState) -> dict:
    """Retrieve relevant knowledge from ChromaDB for all plan types (parallel queries)."""
    profile = state["user_profile"]
    ml = state["ml_analysis"]
    dosha = ml.get("dosha", {}).get("dominant_dosha", "pitta")
    bmi_cat = ml.get("bmi", {}).get("category", "normal")
    symptoms = profile.get("current_symptoms", [])
    goal = profile.get("goal", "general_wellness")

    def chunk_text(docs): return rag_pipeline.format_context(docs, max_chars=3000)

    query_base = f"{dosha} dosha {bmi_cat} {goal}"
    symptom_query = " ".join(symptoms[:4]) if symptoms else ""

    async def _empty(): return []

    # Run all ChromaDB queries concurrently instead of sequentially (~6× faster)
    fitness_q, yoga_q, nutrition_q, panchakarma_q, remedies_q, medicines_q = await asyncio.gather(
        rag_pipeline.query(f"{query_base} gym workout exercise", "fitness", dosha_filter=dosha),
        rag_pipeline.query(f"{query_base} yoga asana pranayama", "ayurveda", dosha_filter=dosha),
        rag_pipeline.query(f"{query_base} diet meal plan food", "nutrition", dosha_filter=dosha),
        rag_pipeline.query(f"{dosha} panchakarma detox", "panchakarma", dosha_filter=dosha),
        rag_pipeline.query(f"{symptom_query} remedy {dosha}", "remedy") if symptom_query else _empty(),
        rag_pipeline.query(f"{symptom_query} medicine churna {dosha}", "ayurveda") if symptom_query else _empty(),
    )

    rag_context = {
        "fitness": chunk_text(fitness_q),
        "yoga": chunk_text(yoga_q),
        "nutrition": chunk_text(nutrition_q),
        "panchakarma": chunk_text(panchakarma_q),
        "remedies": chunk_text(remedies_q) if symptom_query else "",
        "medicines": chunk_text(medicines_q) if symptom_query else "",
    }

    return {"rag_context": rag_context}


# ─────────────────────────────────────────
# TIER 3+4: SPECIALIST AGENT NODES
# ─────────────────────────────────────────
async def fitness_agent_node(state: PlanState) -> dict:
    """Fitness Agent: generates personalised gym plan using ML + RAG."""
    profile = state["user_profile"]
    ml = state["ml_analysis"]
    rag = state["rag_context"].get("fitness", "")
    constraints = ml.get("medical_constraints", {}).get("gym", {})
    top_exercises = ml.get("exercise_rankings", [])[:5]
    vikriti = ml.get("vikriti", {})
    vikriti_dom = vikriti.get("dominant", ml.get("dosha", {}).get("dominant_dosha", "pitta"))
    vikriti_sec = vikriti.get("secondary")
    vikriti_focus = vikriti.get("immediate_focus", "")
    vikriti_signals = vikriti.get("key_signals", [])

    prompt = f"""
Generate a personalised weekly GYM PLAN for this user. Output ONLY valid JSON.

USER PROFILE:
- Name: {profile.get('name', 'User')}
- Gender: {profile.get('gender')} | Age: {profile.get('age')} | BMI: {ml.get('bmi', {}).get('bmi')} ({ml.get('bmi', {}).get('category')})
- Constitutional Dosha (Prakriti): {ml.get('dosha', {}).get('dominant_dosha')} | Goal: {profile.get('goal')}
- Current Imbalance (Vikriti): {vikriti_dom}{f' + {vikriti_sec}' if vikriti_sec else ''} — THIS is what the plan must correct
- Constitution Type: {vikriti.get('constitution_type', '')}
- Immediate Focus: {vikriti_focus}
- Key Signals: {vikriti_signals[:3]}
- Fitness Level: {profile.get('fitness_level')} | Activity: {profile.get('activity_level')}
- Medical History: {profile.get('medical_history', [])}
- Target Calories: {ml.get('calories', {}).get('target_calories')}
- User Rating Preferences: {profile.get('rating_preferences', {})}

TOP RECOMMENDED EXERCISES (ML ranked):
{[e['name'] for e in top_exercises]}

EXERCISES TO AVOID (Medical Safety):
{constraints.get('avoid', [])}

AYURVEDIC KNOWLEDGE (RAG):
{rag[:2000] if rag else 'Use dosha-based exercise principles'}

CRITICAL RULE: Design this plan primarily to CORRECT {vikriti_dom} Vikriti imbalance{f' and secondary {vikriti_sec} imbalance' if vikriti_sec else ''}. The Prakriti (constitution) informs the baseline, but Vikriti is what needs active correction now.

OUTPUT JSON FORMAT:
{{
  "weekly_schedule": {{"monday": {{"focus": "", "type": ""}}, ...}},
  "warmup": {{"duration": "", "exercises": []}},
  "main_exercises": [{{"name": "", "sets": 0, "reps": "", "rest": "", "modification": ""}}],
  "cooldown": {{"duration": "", "exercises": []}},
  "ayurvedic_tips": [],
  "safety_notes": []
}}
"""

    if state.get("is_adaptation") and state.get("feedback"):
        safe_feedback = _sanitize_prompt_input(state.get("feedback"))
        prompt += (
            "\n\nADAPTATION REQUIRED:\n"
            f"Current gym plan:\n{json.dumps(state.get('gym_plan') or {}, ensure_ascii=True)[:2000]}\n"
            f"User feedback: '{safe_feedback}'.\n"
            "Revise the existing gym plan to address this feedback while preserving the overall goal and safety constraints."
        )


    if state.get("other_plans_context"):
        prompt += f"\nCROSS-AGENT CONTEXT:\n{json.dumps(state['other_plans_context'])}\nAdjust your recommendations based on this context.\n"

    try:
        response = await llm_client.generate(
            prompt=prompt,
            system_prompt=FITNESS_AGENT_PROMPT,
            temperature=0.6,
            json_mode=True,
        )
        gym_plan = json.loads(response)
        return {"gym_plan": gym_plan, "model_used": llm_client.provider}
    except Exception as e:
        return {"gym_plan": {"error": str(e)}, "errors": [f"Fitness agent: {e}"]}


async def yoga_agent_node(state: PlanState) -> dict:
    """Yoga Agent: generates yoga plan."""
    profile = state["user_profile"]
    ml = state["ml_analysis"]
    dosha_analysis = ml.get("dosha", {})
    yoga_rag = state["rag_context"].get("yoga", "")
    yoga_constraints = ml.get("medical_constraints", {}).get("yoga", {})
    vikriti = ml.get("vikriti", {})
    vikriti_dom = vikriti.get("dominant", dosha_analysis.get("dominant_dosha", "pitta"))
    vikriti_sec = vikriti.get("secondary")
    vikriti_focus = vikriti.get("immediate_focus", "")
    vikriti_signals = vikriti.get("key_signals", [])

    prompt = f"""
Generate a personalised YOGA PLAN. Output ONLY valid JSON.

USER PROFILE:
- Constitutional Dosha (Prakriti): {dosha_analysis.get('dominant_dosha')} | Goal: {profile.get('goal')}
- Current Imbalance (Vikriti): {vikriti_dom}{f' + {vikriti_sec}' if vikriti_sec else ''} — THIS is what the plan must correct
- Constitution Type: {vikriti.get('constitution_type', '')}
- Immediate Focus: {vikriti_focus}
- Key Signals: {vikriti_signals[:3]}
- Medical History: {profile.get('medical_history', [])}
YOGA CONTRAINDICATIONS: {yoga_constraints.get('avoid', [])}
YOGA KNOWLEDGE (RAG): {yoga_rag[:1500] if yoga_rag else 'Use dosha yoga principles'}

CRITICAL RULE: Design this plan primarily to CORRECT {vikriti_dom} Vikriti imbalance{f' and secondary {vikriti_sec} imbalance' if vikriti_sec else ''}. The Prakriti (constitution) informs the baseline, but Vikriti is what needs active correction now.

OUTPUT JSON FORMAT:
{{
  "yoga_plan": {{
    "morning_sequence": [{{"pose": "", "duration": "", "benefit": ""}}],
    "evening_sequence": [{{"pose": "", "duration": "", "benefit": ""}}],
    "pranayama": [{{"name": "", "duration": "", "benefit": ""}}],
    "meditation": {{"type": "", "duration": "", "script": ""}}
  }}
}}
"""
    if state.get("is_adaptation") and state.get("feedback"):
        prompt += f"\n\nADAPTATION REQUIRED:\nFeedback: '{state.get('feedback')}'.\nRevise existing plan."
    if state.get("other_plans_context"):
        prompt += f"\nCROSS-AGENT CONTEXT:\n{json.dumps(state['other_plans_context'])}\n"

    try:
        response = await llm_client.generate(prompt=prompt, system_prompt=AYURVEDA_AGENT_PROMPT, temperature=0.6, json_mode=True)
        return {"yoga_plan": json.loads(response).get("yoga_plan")}
    except Exception as e:
        return {"yoga_plan": {"error": str(e)}, "errors": [f"Yoga agent: {e}"]}


async def panchakarma_agent_node(state: PlanState) -> dict:
    """Panchakarma Agent: generates detox plan."""
    profile = state["user_profile"]
    ml = state["ml_analysis"]
    dosha_analysis = ml.get("dosha", {})
    pk_rag = state["rag_context"].get("panchakarma", "")
    pk_constraints = ml.get("medical_constraints", {}).get("panchakarma", {})
    vikriti = ml.get("vikriti", {})
    vikriti_dom = vikriti.get("dominant", dosha_analysis.get("dominant_dosha", "pitta"))
    vikriti_sec = vikriti.get("secondary")
    vikriti_focus = vikriti.get("immediate_focus", "")
    vikriti_signals = vikriti.get("key_signals", [])

    prompt = f"""
Generate a personalised PANCHAKARMA PLAN. Output ONLY valid JSON.

USER PROFILE:
- Constitutional Dosha (Prakriti): {dosha_analysis.get('dominant_dosha')}
- Current Imbalance (Vikriti): {vikriti_dom}{f' + {vikriti_sec}' if vikriti_sec else ''} — THIS is what the plan must correct
- Constitution Type: {vikriti.get('constitution_type', '')}
- Immediate Focus: {vikriti_focus}
- Key Signals: {vikriti_signals[:3]}
- Medical History: {profile.get('medical_history', [])}
PANCHAKARMA CONTRAINDICATIONS: {pk_constraints.get('avoid', [])}
PANCHAKARMA KNOWLEDGE (RAG): {pk_rag[:1000] if pk_rag else 'Use dosha panchakarma principles'}

CRITICAL RULE: Design this plan primarily to CORRECT {vikriti_dom} Vikriti imbalance{f' and secondary {vikriti_sec} imbalance' if vikriti_sec else ''}. The Prakriti (constitution) informs the baseline, but Vikriti is what needs active correction now.

OUTPUT JSON FORMAT:
{{
  "panchakarma_plan": {{
    "recommended_therapy": "",
    "duration": "",
    "phases": [{{"name": "", "days": "", "instructions": ""}}],
    "home_adaptable": true,
    "contraindications_noted": []
  }}
}}
"""
    if state.get("is_adaptation") and state.get("feedback"):
        prompt += f"\n\nADAPTATION REQUIRED:\nFeedback: '{state.get('feedback')}'.\nRevise existing plan."
    if state.get("other_plans_context"):
        prompt += f"\nCROSS-AGENT CONTEXT:\n{json.dumps(state['other_plans_context'])}\n"

    try:
        response = await llm_client.generate(prompt=prompt, system_prompt=AYURVEDA_AGENT_PROMPT, temperature=0.6, json_mode=True)
        return {"panchakarma_plan": json.loads(response).get("panchakarma_plan")}
    except Exception as e:
        return {"panchakarma_plan": {"error": str(e)}, "errors": [f"PK agent: {e}"]}


async def nutrition_agent_node(state: PlanState) -> dict:
    """Nutrition Agent: generates 7-day meal plan using ML diet scores + RAG."""
    profile = state["user_profile"]
    ml = state["ml_analysis"]
    calorie_data = ml.get("calories", {})
    rag = state["rag_context"].get("nutrition", "")
    constraints = ml.get("medical_constraints", {}).get("diet", {})
    dosha = ml.get("dosha", {}).get("dominant_dosha", "pitta")
    vikriti = ml.get("vikriti", {})
    vikriti_dom = vikriti.get("dominant", dosha)
    vikriti_sec = vikriti.get("secondary")
    vikriti_focus = vikriti.get("immediate_focus", "")
    vikriti_signals = vikriti.get("key_signals", [])

    prompt = f"""
Generate a personalised 7-day DIET PLAN. Output ONLY valid JSON.

NUTRITIONAL TARGETS:
- Target Calories: {calorie_data.get('target_calories')} kcal
- Protein: {calorie_data.get('macros', {}).get('protein_g')}g | Carbs: {calorie_data.get('macros', {}).get('carbs_g')}g | Fat: {calorie_data.get('macros', {}).get('fat_g')}g
- Goal: {profile.get('goal')} | BMI Category: {ml.get('bmi', {}).get('category')}
- User Rating Preferences: {profile.get('rating_preferences', {})}

AYURVEDIC PROFILE:
- Constitutional Dosha (Prakriti): {dosha}
- Current Imbalance (Vikriti): {vikriti_dom}{f' + {vikriti_sec}' if vikriti_sec else ''} — THIS is what the diet must correct
- Constitution Type: {vikriti.get('constitution_type', '')}
- Immediate Focus: {vikriti_focus}
- Key Signals: {vikriti_signals[:3]}
- Six Tastes to FAVOR: {'sweet, bitter, astringent' if vikriti_dom == 'pitta' else 'sweet, sour, salty' if vikriti_dom == 'vata' else 'pungent, bitter, astringent'}

DIETARY RESTRICTIONS (Medical Safety):
- AVOID: {constraints.get('avoid', [])}
- PREFER: {constraints.get('prefer', [])}
- MODIFICATIONS: {constraints.get('modifications', [])}

NUTRITION KNOWLEDGE (RAG): {rag[:2000] if rag else 'Use dosha diet principles'}

CRITICAL RULE: Design this diet primarily to CORRECT {vikriti_dom} Vikriti imbalance{f' and secondary {vikriti_sec} imbalance' if vikriti_sec else ''}. The Prakriti (constitution) informs the baseline, but Vikriti is what needs active correction now.

OUTPUT JSON FORMAT:
{{
  "weekly_plan": {{
    "day1": {{"breakfast": {{"meal": "", "calories": 0}}, "lunch": {{"meal": "", "calories": 0}}, "snack": {{"meal": "", "calories": 0}}, "dinner": {{"meal": "", "calories": 0}}}},
    "day2": {{...}},
    "day3": {{...}},
    "day4": {{...}},
    "day5": {{...}},
    "day6": {{...}},
    "day7": {{...}}
  }},
  "foods_to_favor": [],
  "foods_to_avoid": [],
  "hydration_tips": [],
  "ayurvedic_eating_guidelines": [],
  "medical_modifications": []
}}
"""

    if state.get("is_adaptation") and state.get("feedback"):
        safe_feedback = _sanitize_prompt_input(state.get("feedback"))
        prompt += (
            "\n\nADAPTATION REQUIRED:\n"
            f"Current diet plan:\n{json.dumps(state.get('diet_plan') or {}, ensure_ascii=True)[:2000]}\n"
            f"User feedback: '{safe_feedback}'.\n"
            "Revise the existing diet plan to address this feedback while preserving calorie targets and safety constraints."
        )


    try:
        response = await llm_client.generate(prompt=prompt, system_prompt=NUTRITION_AGENT_PROMPT, temperature=0.6, json_mode=True)
        return {"diet_plan": json.loads(response)}
    except Exception as e:
        return {"diet_plan": {"error": str(e)}, "errors": [f"Nutrition agent: {e}"]}


async def remedy_agent_node(state: PlanState) -> dict:
    """Remedy Agent: finds safe home remedies for current symptoms."""
    profile = state["user_profile"]
    ml = state["ml_analysis"]
    symptoms = profile.get("current_symptoms", [])
    dosha = ml.get("dosha", {}).get("dominant_dosha", "pitta")
    rag = state["rag_context"].get("remedies", "")
    constraints = ml.get("medical_constraints", {}).get("remedies", {})
    vikriti = ml.get("vikriti", {})
    vikriti_dom = vikriti.get("dominant", dosha)
    vikriti_sec = vikriti.get("secondary")
    vikriti_focus = vikriti.get("immediate_focus", "")
    vikriti_signals = vikriti.get("key_signals", [])

    if not symptoms:
        return {"home_remedies": []}

    prompt = f"""
Recommend safe HOME REMEDIES for this user's symptoms. Output ONLY valid JSON.

USER SYMPTOMS: {symptoms}
AYURVEDIC CONDITIONS DETECTED (ML): {list(ml.get('symptom_conditions', {}).keys())[:3]}
CONSTITUTIONAL DOSHA (Prakriti): {dosha}
CURRENT IMBALANCE (Vikriti): {vikriti_dom}{f' + {vikriti_sec}' if vikriti_sec else ''} — remedies must target this imbalance
IMMEDIATE FOCUS: {vikriti_focus}
KEY SIGNALS: {vikriti_signals[:3]}
MEDICAL HISTORY: {profile.get('medical_history', [])}
MEDICATIONS: {profile.get('current_medications', [])}
USER RATING PREFERENCES: {profile.get('rating_preferences', {})}

HERBS/INGREDIENTS TO AVOID (Medical Safety): {constraints.get('avoid', [])}
HERB INTERACTIONS TO WARN ABOUT: {constraints.get('herb_interactions', [])}

REMEDY KNOWLEDGE (RAG): {rag[:2500] if rag else 'Use classical Ayurvedic remedies'}

CRITICAL RULE: Prioritize remedies that CORRECT {vikriti_dom} Vikriti imbalance{f' and secondary {vikriti_sec} imbalance' if vikriti_sec else ''}. The Prakriti (constitution) informs the baseline, but Vikriti is what needs active correction now.

OUTPUT JSON FORMAT (array of remedies):
[{{
  "remedy_name": "",
  "symptom_addressed": "",
  "ingredients": [],
  "preparation": "",
  "dosage": "",
  "frequency": "",
  "best_time": "",  
  "safety_rating": "safe_for_all|safe_for_most|generally_safe|consult_doctor",
  "warnings": [],
  "ayurvedic_rationale": "",
  "scientific_basis": ""
}}]
"""

    if state.get("is_adaptation") and state.get("feedback"):
        safe_feedback = _sanitize_prompt_input(state.get("feedback"))
        prompt += (
            "\n\nADAPTATION REQUIRED:\n"
            f"Current remedies:\n{json.dumps(state.get('home_remedies') or [], ensure_ascii=True)[:1800]}\n"
            f"User feedback: '{safe_feedback}'.\n"
            "Revise the remedy recommendations to address the feedback while preserving safety and contraindication checks."
        )
    if state.get("other_plans_context"):
        prompt += f"\nCROSS-AGENT CONTEXT:\n{json.dumps(state['other_plans_context'])}\n"

    try:
        response = await llm_client.generate(prompt=prompt, system_prompt=REMEDY_AGENT_PROMPT, temperature=0.5, json_mode=True)
        raw = json.loads(response)
        remedies = raw if isinstance(raw, list) else raw.get("remedies", [])
        return {"home_remedies": remedies}
    except Exception as e:
        return {"home_remedies": [], "errors": [f"Remedy agent: {e}"]}


async def medicine_agent_node(state: PlanState) -> dict:
    """Medicine Agent: recommends classical Ayurvedic medicines."""
    profile = state["user_profile"]
    ml = state["ml_analysis"]
    symptoms = profile.get("current_symptoms", [])
    dosha = ml.get("dosha", {}).get("dominant_dosha", "pitta")
    rag = state["rag_context"].get("medicines", "")
    constraints = ml.get("medical_constraints", {}).get("remedies", {})
    vikriti = ml.get("vikriti", {})
    vikriti_dom = vikriti.get("dominant", dosha)
    vikriti_sec = vikriti.get("secondary")
    vikriti_focus = vikriti.get("immediate_focus", "")
    vikriti_signals = vikriti.get("key_signals", [])

    if not symptoms:
        return {"medicines": []}

    prompt = f"""
Recommend safe AYURVEDIC MEDICINES for this user's symptoms. Output ONLY valid JSON.

USER SYMPTOMS: {symptoms}
AYURVEDIC CONDITIONS DETECTED (ML): {list(ml.get('symptom_conditions', {}).keys())[:3]}
CONSTITUTIONAL DOSHA (Prakriti): {dosha}
CURRENT IMBALANCE (Vikriti): {vikriti_dom}{f' + {vikriti_sec}' if vikriti_sec else ''} — medicines must target this imbalance
IMMEDIATE FOCUS: {vikriti_focus}
KEY SIGNALS: {vikriti_signals[:3]}
MEDICAL HISTORY: {profile.get('medical_history', [])}
MEDICATIONS: {profile.get('current_medications', [])}

HERBS/INGREDIENTS TO AVOID (Medical Safety): {constraints.get('avoid', [])}
HERB INTERACTIONS TO WARN ABOUT: {constraints.get('herb_interactions', [])}

MEDICINE KNOWLEDGE (RAG): {rag[:2500] if rag else 'Use classical Ayurvedic formulations'}

CRITICAL RULE: Prioritize medicines that CORRECT {vikriti_dom} Vikriti imbalance{f' and secondary {vikriti_sec} imbalance' if vikriti_sec else ''}. The Prakriti (constitution) informs the baseline, but Vikriti is what needs active correction now.

OUTPUT JSON FORMAT (array of medicines):
[{{
  "medicine_name": "",
  "type": "Churna|Vati|Asava|Taila",
  "symptom_addressed": "",
  "dosage": "",
  "anupana": "what to take it with (e.g., warm water, honey)",
  "safety_rating": "safe_for_all|safe_for_most|generally_safe|consult_doctor",
  "warnings": []
}}]
"""
    if state.get("other_plans_context"):
        prompt += f"\nCROSS-AGENT CONTEXT:\n{json.dumps(state['other_plans_context'])}\n"

    try:
        response = await llm_client.generate(prompt=prompt, system_prompt=REMEDY_AGENT_PROMPT, temperature=0.5, json_mode=True)
        raw = json.loads(response)
        medicines = raw if isinstance(raw, list) else raw.get("medicines", [])
        return {"medicines": medicines}
    except Exception as e:
        return {"medicines": [], "errors": [f"Medicine agent: {e}"]}


async def daily_tip_node(state: PlanState) -> dict:
    """Generate a daily tip using RAG + GenAI."""
    profile = state["user_profile"]
    dosha = state["ml_analysis"].get("vikriti", {}).get("dominant") or state["ml_analysis"].get("dosha", {}).get("dominant_dosha", "pitta")

    from datetime import date
    import random
    categories = ["diet", "lifestyle", "yoga", "seasonal", "remedy"]
    category = categories[date.today().day % len(categories)]

    docs = await rag_pipeline.query(f"{dosha} daily wellness tip {category}", "ayurveda", n_results=1, dosha_filter=dosha)
    raw_tip = docs[0]["content"] if docs else f"Drink warm water with ginger to kindle your digestive fire."

    try:
        tip = await llm_client.generate(
            prompt=f"Rephrase this Ayurvedic wellness tip in 2-3 friendly, actionable sentences for a {dosha} type:\n\n{raw_tip}",
            temperature=0.8,
            max_tokens=200,
        )
        return {"daily_tip": tip.strip()}
    except Exception as e:
        import logging as _logging
        _logging.getLogger("ayura.agents").warning("daily_tip_node failed: %s", e)
        return {"daily_tip": raw_tip}


async def seasonal_guidance_node(state: PlanState) -> dict:
    """Generate synchronized seasonal guidance for the holistic plan."""
    dosha = (
        state.get("ml_analysis", {}).get("vikriti", {}).get("dominant")
        or state.get("ml_analysis", {}).get("dosha", {}).get("dominant_dosha")
        or state.get("user_profile", {}).get("dominant_dosha")
        or "pitta"
    )
    try:
        guidance = await build_seasonal_guidance(dosha)
        return {"seasonal_guidance": guidance}
    except Exception as e:
        return {
            "seasonal_guidance": {
                "error": str(e),
                "season": "Unknown",
                "english_name": "Unknown",
                "risk_level": "low",
                "primary_concern": dosha,
                "recommendations": {
                    "diet_adjustments": [],
                    "lifestyle_changes": [],
                    "avoid": [],
                },
            },
            "errors": [f"Seasonal guidance: {e}"],
        }


async def supervisor_node(state: PlanState) -> dict:
    """Supervisor: validates all agent outputs and checks for conflicts."""
    profile = state["user_profile"]
    medical_history = profile.get("medical_history", [])
    medications = profile.get("current_medications", [])
    ml = state.get("ml_analysis", {})
    constraints = ml.get("medical_constraints", {})
    errors = state.get("errors", [])
    safety_warnings: list[str] = []

    gym_hits = _find_constraint_hits(
        _collect_plan_strings(state.get("gym_plan") or {}),
        constraints.get("gym", {}).get("avoid", []),
    )
    if gym_hits:
        safety_warnings.append(
            f"Gym plan contains contraindicated items: {', '.join(gym_hits)}."
        )

    yoga_hits = _find_constraint_hits(
        _collect_plan_strings(state.get("yoga_plan") or {}),
        constraints.get("yoga", {}).get("avoid", []),
    )
    if yoga_hits:
        safety_warnings.append(
            f"Yoga plan contains contraindicated items: {', '.join(yoga_hits)}."
        )

    diet_hits = _find_constraint_hits(
        _collect_plan_strings(state.get("diet_plan") or {}),
        constraints.get("diet", {}).get("avoid", []),
    )
    if diet_hits:
        safety_warnings.append(
            f"Diet plan contains contraindicated items: {', '.join(diet_hits)}."
        )

    panchakarma_hits = _find_constraint_hits(
        _collect_plan_strings(state.get("panchakarma_plan") or {}),
        constraints.get("panchakarma", {}).get("avoid", []),
    )
    if panchakarma_hits:
        safety_warnings.append(
            "Panchakarma plan contains contraindicated items: "
            f"{', '.join(panchakarma_hits)}."
        )

    remedies = (state.get("home_remedies") or []) + (state.get("medicines") or [])
    remedy_hits = _find_constraint_hits(
        _collect_plan_strings(remedies),
        constraints.get("remedies", {}).get("avoid", []),
    )
    if remedy_hits:
        safety_warnings.append(
            f"Remedies/Medicines contain contraindicated items: {', '.join(remedy_hits)}."
        )

    herb_interaction_result = condition_filter.check_drug_herb_interactions(
        medications,
        _extract_remedy_ingredients(state.get("home_remedies") or []),
    )
    herb_interactions = herb_interaction_result["warnings"]
    if herb_interactions:
        summaries = [
            f"{warning['herb']} with {warning['medication_category']}"
            for warning in herb_interactions
        ]
        safety_warnings.append(
            "Potential drug-herb interactions detected: "
            f"{', '.join(sorted(set(summaries)))}."
        )

    safety_checks = {
        "medical_history_applied": bool(medical_history),
        "agents_completed": [
            k for k in ["gym_plan", "yoga_plan", "diet_plan", "panchakarma_plan", "home_remedies", "medicines"]
            if state.get(k) is not None
        ],
        "warnings": safety_warnings
    }

    # Redact unsafe plans if warnings are critical
    if safety_warnings:
        redaction_message = "This plan section has been redacted due to medical safety constraints."
        
        if gym_hits:
            state["gym_plan"] = {"error": redaction_message, "safety_violation": True}
        if yoga_hits:
            state["yoga_plan"] = {"error": redaction_message, "safety_violation": True}
        if diet_hits:
            state["diet_plan"] = {"error": redaction_message, "safety_violation": True}
        if panchakarma_hits:
            state["panchakarma_plan"] = {"error": redaction_message, "safety_violation": True}
        if remedy_hits or herb_interactions:
            state["home_remedies"] = [{"error": redaction_message, "safety_violation": True}]
            state["medicines"] = [{"error": redaction_message, "safety_violation": True}]

    return {"safety_checks": safety_checks, "adaptation_summary": state.get("adaptation_summary")}


# ─────────────────────────────────────────
# GRAPH DEFINITION
# ─────────────────────────────────────────
def build_plan_graph() -> StateGraph:
    graph = StateGraph(PlanState)

    graph.add_node("ml_analysis_node", ml_analysis_node)
    graph.add_node("rag_retrieval_node", rag_retrieval_node)
    graph.add_node("fitness_agent_node", fitness_agent_node)
    graph.add_node("yoga_agent_node", yoga_agent_node)
    graph.add_node("panchakarma_agent_node", panchakarma_agent_node)
    graph.add_node("nutrition_agent_node", nutrition_agent_node)
    graph.add_node("remedy_agent_node", remedy_agent_node)
    graph.add_node("medicine_agent_node", medicine_agent_node)
    graph.add_node("daily_tip_node", daily_tip_node)
    graph.add_node("seasonal_guidance_node", seasonal_guidance_node)
    graph.add_node("supervisor_node", supervisor_node)

    graph.set_entry_point("ml_analysis_node")
    graph.add_edge("ml_analysis_node", "rag_retrieval_node")

    # Parallel specialist agents after RAG
    graph.add_edge("rag_retrieval_node", "fitness_agent_node")
    graph.add_edge("rag_retrieval_node", "yoga_agent_node")
    graph.add_edge("rag_retrieval_node", "panchakarma_agent_node")
    graph.add_edge("rag_retrieval_node", "nutrition_agent_node")
    graph.add_edge("rag_retrieval_node", "remedy_agent_node")
    graph.add_edge("rag_retrieval_node", "medicine_agent_node")
    graph.add_edge("rag_retrieval_node", "daily_tip_node")
    graph.add_edge("rag_retrieval_node", "seasonal_guidance_node")

    # All agents report to supervisor
    graph.add_edge("fitness_agent_node", "supervisor_node")
    graph.add_edge("yoga_agent_node", "supervisor_node")
    graph.add_edge("panchakarma_agent_node", "supervisor_node")
    graph.add_edge("nutrition_agent_node", "supervisor_node")
    graph.add_edge("remedy_agent_node", "supervisor_node")
    graph.add_edge("medicine_agent_node", "supervisor_node")
    graph.add_edge("daily_tip_node", "supervisor_node")
    graph.add_edge("seasonal_guidance_node", "supervisor_node")
    graph.add_edge("supervisor_node", END)

    return graph.compile()


# Compiled graph singleton (kept for holistic generation if needed)
plan_graph = build_plan_graph()


async def generate_single_plan(plan_type: str, user_profile: dict, other_plans_context: dict = None, feedback: str = None) -> dict:
    """Generate a single plan type independently using the required nodes."""
    state: PlanState = {
        "user_profile": user_profile,
        "ml_analysis": {},
        "rag_context": {},
        "gym_plan": None,
        "yoga_plan": None,
        "diet_plan": None,
        "panchakarma_plan": None,
        "home_remedies": None,
        "medicines": None,
        "seasonal_guidance": None,
        "daily_tip": None,
        "health_risks": [],
        "safety_checks": {},
        "model_used": None,
        "errors": [],
        "feedback": feedback,
        "is_adaptation": bool(feedback),
        "adaptation_summary": None,
        "other_plans_context": other_plans_context,
    }

    # Step 1: Run ML Analysis
    ml_res = await ml_analysis_node(state)
    state.update(ml_res)

    # Step 2: Run RAG
    rag_res = await rag_retrieval_node(state)
    state.update(rag_res)

    # Step 3: Run Target Agent
    if plan_type == "gym":
        agent_res = await fitness_agent_node(state)
    elif plan_type == "yoga":
        agent_res = await yoga_agent_node(state)
    elif plan_type == "diet":
        agent_res = await nutrition_agent_node(state)
    elif plan_type == "panchakarma":
        agent_res = await panchakarma_agent_node(state)
    elif plan_type == "remedies":
        agent_res = await remedy_agent_node(state)
    elif plan_type == "medicines":
        agent_res = await medicine_agent_node(state)
    else:
        raise ValueError(f"Unknown plan type: {plan_type}")
    
    state.update(agent_res)

    # Step 4: Run Supervisor for safety verification
    safety_res = await supervisor_node(state)
    state.update(safety_res)

    return state


async def generate_holistic_plan(user_profile: dict) -> dict:
    """Main entry point: run the full 4-tier plan generation pipeline."""
    initial_state: PlanState = {
        "user_profile": user_profile,
        "ml_analysis": {},
        "rag_context": {},
        "gym_plan": None,
        "yoga_plan": None,
        "diet_plan": None,
        "panchakarma_plan": None,
        "home_remedies": None,
        "medicines": None,
        "seasonal_guidance": None,
        "daily_tip": None,
        "health_risks": [],
        "safety_checks": {},
        "model_used": None,
        "errors": [],
        "feedback": None,
        "is_adaptation": False,
        "adaptation_summary": None,
        "other_plans_context": None,
    }

    final_state = await plan_graph.ainvoke(initial_state)
    return final_state


async def adapt_plan(current_state: dict, feedback: str) -> dict:
    """Feature 10: Run the graph in adaptation mode with user feedback."""
    current_state["feedback"] = feedback
    current_state["is_adaptation"] = True
    current_state["adaptation_summary"] = None
    
    final_state = await plan_graph.ainvoke(current_state)
    return final_state

