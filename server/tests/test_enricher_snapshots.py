"""
Enricher schema snapshot tests.

These tests verify that when an enricher receives a valid LLM response, all
required output fields are present in the merged plan and the raw engine fields
are preserved.  No real API calls are made — llm_client.generate is mocked.

If a field disappears from an enricher's output (e.g., due to a prompt change
that breaks the JSON schema), these tests catch it before it reaches production.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch


# ─── Shared mock profiles ─────────────────────────────────────────────────────

_USER_PROFILE = {
    "age": 35, "gender": "female",
    "dominant_dosha": "pitta", "vikriti_dominant": "pitta",
    "secondary_dosha": "vata", "vikriti_secondary": "vata",
    "medical_history": ["acidity"], "current_medications": [],
    "allergies": [], "injuries_or_limitations": [],
    "current_symptoms": ["bloating"], "stress_level": "moderate",
    "sleep_quality": "good", "agni_type": "tikshna",
    "pregnancy_or_nursing": False, "current_season": "sharad",
}


# ─── Yoga enricher snapshot ───────────────────────────────────────────────────

_YOGA_VALID_RESPONSE = {
    "plan_title": "Pitta-Balancing Yoga Plan",
    "plan_description": "A cooling flow to pacify elevated Pitta.",
    "daily_intention": {k: "Be present" for k in ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")},
    "breathing_guidance": "Slow, cooling ujjayi breath.",
    "lifestyle_sync": "Practice at dawn before Pitta peaks.",
    "progression_plan": {"week_1": "Foundation", "week_2": "Deepen", "week_3": "Refine", "week_4": "Restore"},
    "motivational_note": "You are making progress.",
}

_YOGA_REQUIRED_FIELDS = {
    "plan_title", "plan_description", "daily_intention",
    "breathing_guidance", "lifestyle_sync", "progression_plan",
    "motivational_note", "enriched", "enrichment_model",
}


@pytest.mark.asyncio
async def test_yoga_enricher_snapshot_all_fields_present():
    from services.yoga_plan_enricher import enrich_yoga_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "snap-yoga", "condition_protocols": []}

    with patch("services.yoga_plan_enricher.llm_client") as mock_llm, \
         patch("services.yoga_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=json.dumps(_YOGA_VALID_RESPONSE))
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""

        result = await enrich_yoga_plan(raw_plan, _USER_PROFILE, {"yoga_goal": "stress_relief"})

    assert result["enriched"] is True
    missing = _YOGA_REQUIRED_FIELDS - set(result.keys())
    assert not missing, f"Yoga enricher missing fields: {missing}"
    # Verify raw plan fields are preserved
    assert result["plan_id"] == "snap-yoga"


@pytest.mark.asyncio
async def test_yoga_enricher_snapshot_field_types():
    from services.yoga_plan_enricher import enrich_yoga_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "snap-yoga-types"}

    with patch("services.yoga_plan_enricher.llm_client") as mock_llm, \
         patch("services.yoga_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=json.dumps(_YOGA_VALID_RESPONSE))
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""

        result = await enrich_yoga_plan(raw_plan, _USER_PROFILE, {})

    assert isinstance(result["plan_title"], str) and result["plan_title"]
    assert isinstance(result["daily_intention"], dict)
    assert isinstance(result["progression_plan"], dict)
    assert len(result["progression_plan"]) == 4


# ─── Gym enricher snapshot ────────────────────────────────────────────────────

_GYM_VALID_RESPONSE = {
    "plan_title": "Pitta Strength Plan",
    "plan_description": "Moderate intensity with cooling recovery.",
    "weekly_focus_notes": {k: "Focus on form" for k in ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")},
    "nutrition_sync": {"pre_workout_meal": "Banana", "post_workout_meal": "Dal rice", "hydration": "Cool water"},
    "recovery_protocol": {"sleep": "8 hours", "active_recovery": "Walk", "signs_of_overtraining": ["Fatigue"]},
    "progression_plan": {"week_1": "Learn form", "week_2": "Add weight", "week_3": "Volume", "week_4": "Deload"},
    "vyayama_vidhi": {
        "ardhashakti_guideline": "Stop when forehead and nose sweat together with mouth-breathing onset.",
        "atiyoga_warning_signs": ["Breathlessness", "Dizziness", "Excessive thirst"],
        "pre_workout_ritual": "Cool water 30 min before; avoid exercising in anger.",
        "post_workout_ritual": "10-min rest, cool shower, coconut water.",
        "seasonal_adjustment": "Reduce intensity by 50% in Grishma (summer).",
        "dosha_intensity_principle": "Pitta — moderate intensity; avoid overheating and competitive mindset.",
        "vyayama_contraindications": ["Fever", "Acute indigestion", "High anger or emotional agitation"],
    },
    "ayurvedic_lifestyle_sync": "Train in early morning before Pitta peaks.",
    "classical_transparency_note": "Classical Vyayama in Charaka Sutrasthana Ch.7 specified Malla Yuddha, Danda exercises, and swimming — not gym equipment. This plan applies Ardhashakti and dosha-intensity principles to modern exercises in the spirit of that tradition.",
    "motivational_note": "Consistency builds strength.",
}

_GYM_REQUIRED_FIELDS = {
    "plan_title", "plan_description", "weekly_focus_notes",
    "nutrition_sync", "recovery_protocol", "progression_plan",
    "vyayama_vidhi", "ayurvedic_lifestyle_sync", "classical_transparency_note", "motivational_note", "enriched",
}


@pytest.mark.asyncio
async def test_gym_enricher_snapshot_all_fields_present():
    from services.gym_plan_enricher import enrich_gym_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "snap-gym"}

    with patch("services.gym_plan_enricher.llm_client") as mock_llm, \
         patch("services.gym_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=json.dumps(_GYM_VALID_RESPONSE))
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""

        result = await enrich_gym_plan(raw_plan, _USER_PROFILE, {"gym_goal": "strength"})

    assert result["enriched"] is True
    missing = _GYM_REQUIRED_FIELDS - set(result.keys())
    assert not missing, f"Gym enricher missing fields: {missing}"
    assert result["plan_id"] == "snap-gym"
    assert isinstance(result["nutrition_sync"], dict)
    assert isinstance(result["recovery_protocol"], dict)


# ─── Remedy enricher snapshot ─────────────────────────────────────────────────

_REMEDY_VALID_RESPONSE = {
    "personalized_intro": "Your Pitta causes inflammation that drives bloating.",
    "remedy_rationale": {"bloating": "Fennel seeds cool Pitta and relieve Apana Vata."},
    "synergy_note": "The remedies together calm Pitta and regulate Apana.",
    "recovery_timeline": "Day 1-3: mild relief. Day 7: significant improvement.",
    "prevention_tips": ["Avoid spicy food", "Eat at consistent times", "Chew slowly"],
    "when_to_escalate": "If symptoms worsen after 3 days, see a doctor.",
}

_REMEDY_REQUIRED_FIELDS = {
    "personalized_intro", "synergy_note", "recovery_timeline",
    "prevention_tips", "when_to_escalate", "enriched",
}


@pytest.mark.asyncio
async def test_remedy_enricher_snapshot_all_fields_present():
    from services.remedy_enricher import enrich_remedies_plan

    raw_plan = {
        "plan_id": "snap-remedy",
        "symptoms_addressed": [{
            "symptom_id": "bloating",
            "symptom_display": "Bloating",
            "severity": "mild",
            "remedy": {"name": "Fennel seed tea"},
        }],
    }

    with patch("services.remedy_enricher.llm_client") as mock_llm, \
         patch("services.remedy_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=json.dumps(_REMEDY_VALID_RESPONSE))
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""

        result = await enrich_remedies_plan(raw_plan, _USER_PROFILE)

    assert result["enriched"] is True
    missing = _REMEDY_REQUIRED_FIELDS - set(result.keys())
    assert not missing, f"Remedy enricher missing fields: {missing}"
    assert isinstance(result["prevention_tips"], list) and len(result["prevention_tips"]) >= 1


# ─── Panchakarma enricher snapshot ───────────────────────────────────────────

_PK_VALID_RESPONSE = {
    "plan_title": "Pitta Virechana Protocol",
    "plan_description": "Classical purgation to clear Pitta from Rakta and Pittashaya.",
    "shodhana_rationale": "Virechana is prescribed for Pitta Vikriti.",
    "ritu_guidance": "Sharad is the ideal season for Virechana.",
    "purvakarma_coaching": {
        "why": "Snehana softens Ama for expulsion.",
        "daily_tip": "You may feel heaviness during oleation.",
        "oil_rationale": "Tikta Ghrita is used for its bitter Pitta-clearing Virya.",
    },
    "daily_guidance": {"Day 1": "Rest and light diet.", "Day 2": "Snehana begins."},
    "pradhana_karma_coaching": {
        "what_to_expect": "Loose stools and lightness.",
        "samyak_yoga_signs": "Pitta-coloured stool, relief from symptoms.",
        "atiyoga_warning": "Excessive purging — stop and take ORS.",
        "emotional_release": "Anger and irritability may surface.",
    },
    "samsarjana_coaching": "The post-PK diet rebuilds Agni gradually.",
    "aushadha_guidance": "Tikta Ghrita is taken on empty stomach with warm water.",
    "dietary_rules": "Avoid sour, spicy, heavy food throughout.",
    "rasayana_plan": "Chyawanprash 1 tsp in warm milk after meals for 30 days.",
    "motivational_note": "This cleanse will restore your Pitta balance.",
}

_PK_REQUIRED_FIELDS = {
    "plan_title", "plan_description", "shodhana_rationale",
    "purvakarma_coaching", "pradhana_karma_coaching",
    "samsarjana_coaching", "dietary_rules", "motivational_note", "enriched",
}


@pytest.mark.asyncio
async def test_panchakarma_enricher_snapshot_all_fields_present():
    from services.panchakarma_enricher import enrich_panchakarma_plan

    raw_plan = {
        "plan_id": "snap-pk",
        "daily_schedule": [],
        "clinical_decisions": {
            "pradhana_karma_selected": {"primary": "Virechana", "reason": "Pitta Vikriti"},
            "vikriti_dominant": "pitta",
            "ritu_context": {"ritu": "sharad", "ritu_name": "Sharad (Autumn)"},
            "shodhana_or_shamana": {"type": "Shodhana", "reasons": ["High Pitta"], "bala": "pravara"},
            "unmapped_conditions": [],
        },
        "aushadha": {},
        "snehana_protocol": {},
        "samsarjana_krama": [],
        "phase_breakdown": {},
    }

    with patch("services.panchakarma_enricher.llm_client") as mock_llm, \
         patch("services.panchakarma_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=json.dumps(_PK_VALID_RESPONSE))
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""

        result = await enrich_panchakarma_plan(raw_plan, _USER_PROFILE, {"setting": "home"})

    assert result["enriched"] is True
    missing = _PK_REQUIRED_FIELDS - set(result.keys())
    assert not missing, f"Panchakarma enricher missing fields: {missing}"
    assert result["plan_id"] == "snap-pk"
    assert isinstance(result["purvakarma_coaching"], dict)


# ─── Routine enricher snapshot ────────────────────────────────────────────────

_ROUTINE_VALID_RESPONSE = {
    "plan_title": "Pitta Dinacharya for Sharad Season",
    "plan_description": "A cooling morning routine to pacify Pitta.",
    "dosha_coaching": "Wake before Pitta hour to avoid the midday surge.",
    "agni_coaching": "Tikshna Agni: never skip breakfast.",
    "seasonal_rationale": "Sharad Ritucharya calls for cooling practices.",
    "morning_ritual_rationale": {
        "why_tongue_scraping": "Removes overnight Ama accumulation.",
        "why_oil_pulling": "Protects oral Pitta from morning inflammation.",
        "why_abhyanga": "Coconut oil cools Pitta before the active day.",
    },
    "sleep_coaching": "Sleep by 10 PM before Pitta governs the night cycle.",
    "integration_note": "No integration requested.",
    "weekly_theme": {k: "Stay cool and consistent" for k in ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")},
    "motivational_note": "Each morning ritual is medicine for your Pitta.",
}

_ROUTINE_REQUIRED_FIELDS = {
    "plan_title", "plan_description", "dosha_coaching", "agni_coaching",
    "seasonal_rationale", "morning_ritual_rationale", "sleep_coaching",
    "weekly_theme", "motivational_note", "enriched",
}


@pytest.mark.asyncio
async def test_routine_enricher_snapshot_all_fields_present():
    from services.routine_enricher import enrich_routine_plan

    raw_plan = {
        "plan_id": "snap-routine",
        "wake_time": "5:30 AM",
        "sleep_time": "10:00 PM",
        "morning_rituals": [{"name": "Tongue Scraping"}],
        "meal_schedule": {"breakfast": {"time": "7:30 AM"}, "lunch": {"time": "12:30 PM"}},
    }

    with patch("services.routine_enricher.llm_client") as mock_llm, \
         patch("services.routine_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=json.dumps(_ROUTINE_VALID_RESPONSE))
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""

        result = await enrich_routine_plan(raw_plan, _USER_PROFILE, {"routine": {}})

    assert result["enriched"] is True
    missing = _ROUTINE_REQUIRED_FIELDS - set(result.keys())
    assert not missing, f"Routine enricher missing fields: {missing}"
    assert result["plan_id"] == "snap-routine"
    assert isinstance(result["morning_ritual_rationale"], dict)
    assert isinstance(result["weekly_theme"], dict) and len(result["weekly_theme"]) == 7


# ─── Cross-enricher: raw plan fields always preserved ─────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("enricher_fn,raw_plan,module,prefs", [
    (
        "enrich_yoga_plan",
        {"weekly_schedule": [], "plan_id": "preserve-yoga", "custom_field": "keep_me"},
        "services.yoga_plan_enricher",
        {"yoga_goal": "flexibility"},
    ),
    (
        "enrich_gym_plan",
        {"weekly_schedule": [], "plan_id": "preserve-gym", "custom_field": "keep_me"},
        "services.gym_plan_enricher",
        {"gym_goal": "strength"},
    ),
])
async def test_enricher_preserves_raw_plan_fields(enricher_fn, raw_plan, module, prefs):
    import importlib
    mod = importlib.import_module(module)
    fn = getattr(mod, enricher_fn)

    dummy_response = {
        "plan_title": "Test", "plan_description": "Test",
        "daily_intention": {}, "weekly_focus_notes": {},
        "breathing_guidance": "", "lifestyle_sync": "",
        "progression_plan": {}, "motivational_note": "Keep going.",
        "nutrition_sync": {}, "recovery_protocol": {},
        "ayurvedic_lifestyle_sync": "",
    }

    with patch(f"{module}.llm_client") as mock_llm, \
         patch(f"{module}.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=json.dumps(dummy_response))
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""

        result = await fn(raw_plan, _USER_PROFILE, prefs)

    assert result["plan_id"] == raw_plan["plan_id"]
    assert result["custom_field"] == "keep_me"
