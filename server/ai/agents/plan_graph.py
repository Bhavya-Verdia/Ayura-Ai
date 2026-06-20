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
from engine.dosha_analyzer import dosha_analyzer, _medical_history_vikriti_signal, _DISEASE_DOSHA_SIGNAL, _dhatu_from_conditions, _DHATU_THERAPY
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


_RASA_VIRYA_VIPAKA: dict[str, dict] = {
    "vata": {
        "favor_rasa": "Madhura (sweet), Amla (sour), Lavana (salty)",
        "avoid_rasa": "Katu (pungent), Tikta (bitter), Kashaya (astringent)",
        "virya": "Ushna (warm/hot potency) — favors digestive fire and channel lubrication",
        "vipaka": "Madhura Vipaka (sweet post-digestive) — builds Ojas, nourishes Dhatus",
        "mahabhuta": "Prithvi (earth) + Jal (water) elements — heavy, stable, moist",
        "key_foods": "Ghee, sesame oil, warm milk, root vegetables, dates, almonds, rice, wheat, mung dal (well-cooked)",
        "avoid_foods": "Raw salads, cold drinks, carbonated beverages, popcorn, crackers, dry/light foods",
        "eating_principles": "Warm, freshly cooked, oily, heavy meals. Eat at regular fixed times. No skipping meals. Largest meal at midday (Pitta kala). Small warm snacks if hungry.",
    },
    "pitta": {
        "favor_rasa": "Madhura (sweet), Tikta (bitter), Kashaya (astringent)",
        "avoid_rasa": "Katu (pungent), Amla (sour), Lavana (salty)",
        "virya": "Sheeta (cooling potency) — reduces heat, inflammation, acidity",
        "vipaka": "Madhura Vipaka — promotes cooling and rebuilding",
        "mahabhuta": "Prithvi (earth) + Jal (water) — cooling and stabilising",
        "key_foods": "Coconut, coriander, fennel, bitter gourd, leafy greens, cucumber, sweet fruits, ghee, basmati rice, mung dal",
        "avoid_foods": "Chilli, sour fermented foods, alcohol, red meat, fried food, excess salt, sour citrus, tomato",
        "eating_principles": "Cool or room-temperature meals. No eating when angry or stressed. Largest meal at midday. Avoid skipping meals — leads to acidity. No excess fasting.",
    },
    "kapha": {
        "favor_rasa": "Katu (pungent), Tikta (bitter), Kashaya (astringent)",
        "avoid_rasa": "Madhura (sweet), Amla (sour), Lavana (salty)",
        "virya": "Ushna (warm/stimulating) — kindles Agni, breaks down Ama, reduces heaviness",
        "vipaka": "Katu Vipaka (pungent post-digestive) — reduces Kapha accumulation, promotes lightness",
        "mahabhuta": "Agni (fire) + Vayu (air) elements — light, dry, mobile",
        "key_foods": "Ginger, turmeric, black pepper, light grains (millet, barley, rye), legumes, leafy greens, honey, pomegranate",
        "avoid_foods": "Dairy (especially cold), fried food, heavy sweets, excess wheat, cold drinks, refrigerated food",
        "eating_principles": "Light meals. Largest meal at midday. Skip dinner if not hungry (dinner optional). Eat only when truly hungry. Warm spiced foods always. Avoid daytime sleeping after meals.",
    },
}

_TRIKALA: dict[str, dict] = {
    "vata": {
        "peak_times": "2–6 AM and 2–6 PM",
        "meal_timing": "Breakfast by 8am (never skip — Vata aggravates when fasting). Lunch 12–1pm (largest meal). Dinner by 6:30pm (light, warm). No eating after 7pm.",
        "medicine_time": "Medicines best taken with warm water at 8am and 6pm (Vata kala — maximum absorption in Vata channels).",
        "exercise_time": "Best: 6–8am (Kapha kala — Vata is not dominant, body is stable). Avoid vigorous exercise at 2–6pm (Vata peak — risk of Vata aggravation and injury).",
        "sleep": "In bed by 10pm. Wake by 6am. Vata types need 8 hours. Abhyanga (warm oil self-massage) before shower daily.",
    },
    "pitta": {
        "peak_times": "10 AM–2 PM and 10 PM–2 AM",
        "meal_timing": "Breakfast by 7:30am (light). Lunch 12–1pm (largest meal — Pitta is strongest here, digest well). Dinner by 7pm (moderate). No late-night eating.",
        "medicine_time": "Medicines best taken at 10am or after meals at lunch (Pitta kala peak — medicines work with digestive fire).",
        "exercise_time": "Best: 6–8am (cool morning). AVOID 10am–2pm exercise in heat (Pitta peak — risk of inflammation, overheating). Evening exercise fine if cool environment.",
        "sleep": "In bed by 10pm (before Pitta night peak). Wake by 6am. Avoid late-night work — Pitta at 10pm–2am drives mental overactivity.",
    },
    "kapha": {
        "peak_times": "6–10 AM and 6–10 PM",
        "meal_timing": "Light breakfast or no breakfast (Kapha types accumulate Ama with heavy morning meal). Lunch 12–1pm (largest and only substantial meal). Light dinner by 6pm. No eating after 7pm.",
        "medicine_time": "Medicines with honey or warm ginger water at 8am (Kapha kala — kick-starts digestion). Evening dose at 6pm before Kapha accumulation.",
        "exercise_time": "BEST: 6–9am (Kapha peak — exercise during Kapha time burns accumulated Kapha). Vigorous morning exercise is ideal for Kapha. Avoid napping after lunch.",
        "sleep": "In bed by 10pm. Wake by 5–6am. Do NOT sleep past 6am — post-sunrise sleep creates Kapha Ama. No daytime sleeping.",
    },
}

_VIRUDDHA_AHARA = """
VIRUDDHA AHARA — Incompatible Combinations to NEVER recommend (Charaka Sutrasthana 26):
1. Milk + any sour/acidic food (citrus, tamarind, amla, vinegar, tomato) — Virya-Viruddha (property opposition)
2. Milk + fish, meat, or eggs — Desha/Kala Viruddha (ecological incompatibility)
3. Honey + equal quantity of ghee (Samana Matra) — Viruddha by measure; produces Ama (CS 26.86)
4. Honey heated above body temperature / honey in hot drinks — heated honey = Ama; toxic (CS 27.249)
5. Cold water immediately after hot food or hot beverages — Agni extinguishing (Kala Viruddha)
6. Curd/yogurt at night — Kapha + Ama formation; substitute with buttermilk (Takra)
7. Banana + milk — Abhishyandi (channel-blocking); causes heaviness and Ama
8. Radish (Mula) + milk — Virya Viruddha (opposite potency)
9. Nightshade vegetables (potato, tomato, brinjal) + dairy — modern Viruddha Ahara; aggravates Ama in Vata conditions
10. Fruit with main meals — fruit ferments in stomach with cooked food; eat 30min before or 2hr after meals
11. Reheated/leftover food (Paryushita Anna) — loses Prana; aggravates Ama. Prefer freshly cooked.
12. Eating before previous meal is digested — Adhyashana; most common cause of Ama formation
→ If a recommended food appears near a Viruddha pair, ADD a note to separate them by ≥2 hours.
→ Include a "viruddha_warnings" field listing any Viruddha Ahara pairs to avoid for this day's meals.
"""


def _build_disease_block(disease_context: dict, vikriti_dom: str, agent: str, all_medical_history: list[str] | None = None) -> str:
    """Build a disease-aware context block for agent prompts.

    This tells each agent WHY the Vikriti is imbalanced (the specific disease causing
    the channel disruption) and what that means for their domain.

    For conditions with hardcoded hints: explicit domain-specific guidance.
    For all other mapped conditions: classical Ayurvedic name + Srotas + dosha direction.
    For user-typed unlisted conditions: passed as plain text so the LLM can apply its own knowledge.
    """
    detail = disease_context.get("detail", [])
    unlisted = []
    if all_medical_history:
        mapped_ids = {d["id"] for d in detail}
        unlisted = [c for c in all_medical_history if c not in mapped_ids]

    if not detail and not unlisted:
        return ""

    _pacify_guidance = {
        "vata": "PACIFY Vata: warm, oily, grounding; regular routine; Abhyanga (warm sesame oil massage); avoid cold/raw/dry",
        "pitta": "PACIFY Pitta: cooling, sweet, bitter, astringent; avoid spicy/sour/hot; promote moderation",
        "kapha": "PACIFY Kapha: light, dry, pungent, bitter; promote movement; avoid heavy/sweet/oily foods",
    }

    _agent_guidance: dict[str, dict[str, str]] = {
        "fitness": {
            "ankylosing_spondylitis":  "NO high-impact / axial-loading exercise. Prefer swimming, gentle walking, aqua therapy. Avoid spinal compression.",
            "rheumatoid_arthritis":    "Avoid high-resistance training during flare. Prefer range-of-motion, aqua exercise, gentle walking.",
            "osteoarthritis":          "Avoid high-impact cardio. Prefer low-impact: cycling, swimming, water aerobics.",
            "sciatica":                "Avoid heavy deadlifts, squats with load. Prefer McKenzie protocol, core stabilisation.",
            "osteoporosis":            "Avoid high-impact, twisting, forward-bending. Prefer weight-bearing walking, resistance bands.",
            "fibromyalgia":            "Keep intensity LOW (RPE ≤ 5). Prefer walking, swimming, gentle yoga. No HIIT.",
            "heart_disease":           "Keep HR ≤ 70% max. No sudden high-intensity bursts. Prefer walking, light cycling.",
            "hypertension":            "Avoid Valsalva maneuver (heavy lifting). Prefer aerobic: brisk walking, cycling.",
            "asthma":                  "Avoid cold/dry air exercise. Prefer warm-environment cardio. Keep inhaler accessible.",
            "copd":                    "Very low intensity only. Pursed-lip breathing during exercise. No high-altitude training.",
            "epilepsy":                "Avoid aquatic solo exercise, heights, heavy machinery. Supervision required.",
            "parkinson":               "Focus on balance, gait, dual-task training. Prefer Tai Chi, treadmill with support.",
            "multiple_sclerosis":      "Avoid overheating (Uhthoff's). Cool environment. Prefer aqua, seated exercise.",
            "lupus":                   "Avoid peak sun-hour outdoor exercise. Sun protection mandatory. Keep intensity moderate.",
        },
        "yoga": {
            "ankylosing_spondylitis":  "AVOID deep spinal twists (Ardha Matsyendrasana), backbends, Halasana. FAVOR Cat-Cow (Marjaryasana-Bitilasana), Balasana, gentle Shavasana, Supta Baddha Konasana.",
            "rheumatoid_arthritis":    "Avoid weight-bearing on inflamed joints. Prefer chair yoga, restorative poses, Yoga Nidra.",
            "sciatica":                "AVOID forward folds, Paschimottanasana. FAVOR Supta Kapotasana, Viparita Karani, Setu Bandha.",
            "osteoporosis":            "AVOID forward flexion (Uttanasana), twisting. FAVOR Tadasana, Virabhadrasana, Vrikshasana.",
            "hypertension":            "Avoid inversions (Sirsasana, Sarvangasana). Prefer gentle pranayama (Chandra Bhedana, Bhramari).",
            "asthma":                  "Prioritise Pranayama: Anulom Vilom, Bhramari. AVOID Kapalabhati in acute phase.",
            "heart_disease":           "Avoid Kapalabhati, Bhastrika. Prefer Yoga Nidra, gentle Hatha, Savasana.",
            "epilepsy":                "Avoid inverted poses. Prefer grounding poses: Balasana, Shavasana, seated forward bends.",
            "multiple_sclerosis":      "Keep session short (20 min max). Cool room. Prefer chair yoga, restorative.",
            "fibromyalgia":            "Restorative yoga only. No power yoga. Prioritize Yoga Nidra and gentle stretching.",
        },
        "nutrition": {
            "ankylosing_spondylitis":  "FAVOR: ghee, sesame oil, warm milk with Ashwagandha, root vegetables (sweet potato, beets), Dashamula tea, bone broth. AVOID: cold/raw foods, carbonated drinks, nightshades (tomato, potato), excessive caffeine.",
            "rheumatoid_arthritis":    "FAVOR: anti-inflammatory: turmeric-ghee, ginger tea, omega-3 rich foods. AVOID: nightshades, processed sugar, red meat, gluten if sensitive.",
            "psoriasis":               "AVOID: nightshades, processed sugar, alcohol, red meat. FAVOR: bitter vegetables, turmeric, coriander, cooling foods.",
            "diabetes_type2":          "Low glycemic index. No refined sugar/flour. FAVOR: bitter gourd, fenugreek, cinnamon, barley.",
            "hypertension":            "Low sodium. AVOID pickled/processed foods. FAVOR: watermelon, garlic, pomegranate.",
            "ibs":                     "Follow Agni-appropriate diet. Small frequent meals. AVOID raw salads, cold foods, carbonated drinks.",
            "acid_reflux":             "AVOID spicy/sour/fermented. No citrus. FAVOR: coconut water, cold milk, coriander, fennel.",
            "hypothyroidism":          "AVOID raw cruciferous (broccoli, cabbage). FAVOR: iodine-rich foods, selenium foods, warm cooked meals.",
            "pcos":                    "Low GI, anti-inflammatory. AVOID dairy excess, sugar. FAVOR: fenugreek, cinnamon, flaxseed.",
            "gout":                    "LOW purine diet. AVOID red meat, organ meats, alcohol, shellfish, fructose. FAVOR: cherries, celery, hydration.",
            "kidney_stones":           "High fluid intake (3L/day). AVOID oxalate-rich foods (spinach, beets, nuts). FAVOR: lemon water, pomegranate.",
            "fatty_liver":             "AVOID alcohol, refined sugar, processed foods. FAVOR: bitter vegetables, turmeric, garlic, fibrous foods.",
        },
        "remedy": {
            "ankylosing_spondylitis":  "Classical remedies: Mahayogaraj Guggulu (Asthi-Majja Vata), Dashamoolarishta, Bala Taila Abhyanga (warm oil on spine), Ashwagandha churna with warm milk, Rasna Saptak Kwath.",
            "rheumatoid_arthritis":    "Amavata protocol: Shunthi (ginger), Guduchi, Triphala, Yogaraj Guggulu. Avoid heavy Kapha foods.",
            "gout":                    "Vatarakta protocol: Triphala Guggulu, Neem, Giloy/Guduchi, Manjistha, Punarnavadi Guggulu.",
            "psoriasis":               "Kushtha protocol: Manjistha, Neem, Triphala, Tikta Ghrita, Arogyavardhini Vati.",
            "diabetes_type2":          "Prameha protocol: Vijaysar, Karela (bitter gourd), Fenugreek, Jamun seed, Chandraprabha Vati.",
            "hypothyroidism":          "Kanchanar Guggulu (Galaganda), Ashwagandha, Brahmi, Triphala.",
            "pcos":                    "Shatavari, Ashoka, Lodhra, Raja Pravartini Vati, Kumari (Aloe vera).",
            "asthma":                  "Sitopaladi Churna, Talisadi Churna, Vasarishta, Kantakari, Tulsi-Ginger tea.",
            "migraine":                "Shirashoolari Vajra Rasa, Pathyadi Kwath, Brahmi Ghrita, Sirodhara with Ksheerabala Taila.",
            "sciatica":                "Gridhrasi: Mahanarayana Taila, Dashmool Kashayam, Vatari Guggulu, Kati Basti.",
            "fibromyalgia":            "Bala Ashwagandha Taila Abhyanga, Mamsapachaka Vati, Dashamoolarishta.",
            "anxiety":                 "Ashwagandha, Brahmi, Jatamansi, Shankhpushpi, Saraswatarishta.",
            "depression":              "Brahmi Ghrita, Ashwagandha, Shatavari, Unmadnashak Ghan Vati.",
            "insomnia":                "Jatamansi, Brahmi, Ashwagandha, warm milk with Nutmeg before bed.",
        },
        "medicine": {
            "ankylosing_spondylitis":  "Mahayogaraj Guggulu 2 tabs BD after meals with warm water. Dashamoolarishta 20ml BD. Bala Taila for Abhyanga. If severe: Panchakarma — Kati Basti with Dashmoola Taila.",
            "rheumatoid_arthritis":    "Yogaraj Guggulu or Simhanada Guggulu. Guduchi Satva. Triphala Churna for Ama digestion.",
            "gout":                    "Triphala Guggulu, Neem capsules, Giloy Satva, Chandraprabha Vati for uric acid.",
            "psoriasis":               "Arogyavardhini Vati, Gandak Rasayan, Tikta Ghrita internally, Neem-turmeric externally.",
            "diabetes_type2":          "Chandraprabha Vati, Shilajitvadi Vati, Vijaysar wood cup water.",
            "hypothyroidism":          "Kanchanar Guggulu 2 tabs TDS. Ashwagandha 500mg BD.",
            "pcos":                    "Raja Pravartini Vati, Shatavari Kalpa, Pushyanug Churna.",
            "asthma":                  "Vasarishta 20ml BD, Sitopaladi Churna 3g BD with honey.",
            "anxiety":                 "Saraswatarishta 20ml BD, Brahmi Vati 1 tab TDS.",
            "depression":              "Unmadnashak Ghan Vati, Brahmi Ghrita 5ml with warm milk.",
            "insomnia":                "Sarpagandha Vati (if BP normal), Jatamansi Churna 3g with warm milk at bedtime.",
        },
    }

    lines = ["\nDIAGNOSED CONDITIONS — Classical Ayurvedic Etiology (HIGH CLINICAL WEIGHT):"]

    for d in detail:
        cid = d["id"]
        s2 = d.get("secondary_dosha")
        lines.append(
            f"• {cid.replace('_', ' ').title()}: {d['classical_name']} — Channel: {d['srotas']}"
            + (f" | Also involves {s2.title()}" if s2 else "")
        )
        agent_hint = _agent_guidance.get(agent, {}).get(cid)
        if agent_hint:
            lines.append(f"  [SPECIFIC GUIDANCE] {agent_hint}")
        else:
            # Instruct LLM to apply its own knowledge for this condition + Srotas
            lines.append(
                f"  [Apply classical Nidana-Samprapti reasoning for {d['classical_name']}."
                f" Use your Ayurvedic knowledge to give {agent}-specific guidance for this {d['srotas']} disorder.]"
            )
        kriya_kala = d.get("kriya_kala")
        if kriya_kala:
            _kk_treatment = {
                "sanchaya": "Early accumulation — Nidana Parivarjana (remove cause) is primary. Gentle Dipana-Pachana.",
                "prakopa":  "Aggravation — Shamana (pacification) therapy. Light Langhana if needed.",
                "prasara":  "Spreading — Shamana + beginning Shodhana preparation (Purvakarma: Snehana + Swedana).",
                "sthana":   "Localisation — Shodhana (purification) therapy indicated. Panchakarma appropriate.",
                "vyakti":   "Manifestation — Full Shodhana + Rasayana (rejuvenation) after purification.",
                "bheda":    "Chronicity/complication — Palliation (Upashaya), Rasayana, long-term Shamana. Panchakarma with caution.",
            }
            lines.append(f"  [KRIYA KALA: {kriya_kala.title()} stage — {_kk_treatment.get(kriya_kala, '')}]")

    if unlisted:
        lines.append(
            "\nADDITIONAL DIAGNOSED CONDITIONS (not in classical mapping — use your medical + Ayurvedic knowledge):"
        )
        for u in unlisted:
            lines.append(f"• {u.replace('_', ' ').title()}")
        lines.append(
            f"  [Apply appropriate Ayurvedic {agent} protocol for these conditions."
            " Identify which dosha/Srotas is involved and adjust recommendations accordingly.]"
        )

    primary_doshas = {d["primary_dosha"] for d in detail}
    for pd in primary_doshas:
        lines.append(f"\n⚠ TREATMENT DIRECTION: {_pacify_guidance.get(pd, '')}")

    lines.append(
        f"\n→ The Vikriti shows {vikriti_dom.upper()} dominant BECAUSE OF these diagnosed conditions."
        " ALL recommendations must PACIFY this dosha — NOT amplify it."
    )
    lines.append(
        "→ For any condition without specific guidance shown above, apply classical Ayurvedic"
        " Nidana-Samprapti reasoning using the disease name and affected Srotas as your guide."
        " A trained Vaidya would know the appropriate protocol — reason accordingly."
    )

    # Dhatu involvement block
    dhatu_list = disease_context.get("dhatu_context") or []
    if not dhatu_list and detail:
        dhatu_list = _dhatu_from_conditions([d["id"] for d in detail])
    if dhatu_list:
        lines.append("\nDHATU (TISSUE) INVOLVEMENT — Classical Samprapti:")
        for dh in dhatu_list:
            lines.append(f"• {dh['name']}")
            if agent in ("nutrition", "remedy", "medicine"):
                lines.append(f"  → Therapy: {dh['kshaya_therapy']}")
                lines.append(f"  → Rasayana: {dh['rasayana']}")
            elif agent in ("fitness", "yoga", "panchakarma"):
                lines.append(f"  → {dh['kshaya_therapy']}")

    return "\n".join(lines)


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

    # Disease-dosha context: classical names + dosha signal for each diagnosed condition
    med_conditions = profile.get("medical_history") or []
    _med_sig, disease_notes = _medical_history_vikriti_signal(med_conditions)
    disease_stages = profile.get("disease_stages") or {}
    # Build per-condition detail for agent prompts
    disease_detail: list[dict] = []
    for cond in med_conditions:
        key = cond.lower().strip().replace(" ", "_").replace("-", "_")
        mapping = _DISEASE_DOSHA_SIGNAL.get(key)
        if mapping:
            entry: dict = {
                "id": cond,
                "classical_name": mapping["c"],
                "srotas": mapping["s"],
                "primary_dosha": mapping["p"],
                "secondary_dosha": mapping.get("s2"),
            }
            stage_info = disease_stages.get(cond)
            if stage_info:
                entry["kriya_kala"] = stage_info.get("kriya_kala", "vyakti")
                entry["duration"] = stage_info.get("duration", "unknown")
                entry["trajectory"] = stage_info.get("trajectory", "stable")
            disease_detail.append(entry)

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
            "disease_context": {
                "detail": disease_detail,
                "notes": disease_notes,
                "dosha_signal": _med_sig,
                "dhatu_context": _dhatu_from_conditions(med_conditions),
            },
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
    disease_block = _build_disease_block(ml.get("disease_context", {}), vikriti_dom, "fitness", profile.get("medical_history") or [])
    trikala = _TRIKALA.get(vikriti_dom, _TRIKALA["vata"])

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
- Target Calories: {ml.get('calories', {}).get('target_calories')}
- User Rating Preferences: {profile.get('rating_preferences', {})}
- Optimal Exercise Time (Trikala): {trikala['exercise_time']}
- Sleep Protocol (Trikala): {trikala['sleep']}
{disease_block}

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
    disease_block = _build_disease_block(ml.get("disease_context", {}), vikriti_dom, "yoga", profile.get("medical_history") or [])

    prompt = f"""
Generate a personalised YOGA PLAN. Output ONLY valid JSON.

USER PROFILE:
- Constitutional Dosha (Prakriti): {dosha_analysis.get('dominant_dosha')} | Goal: {profile.get('goal')}
- Current Imbalance (Vikriti): {vikriti_dom}{f' + {vikriti_sec}' if vikriti_sec else ''} — THIS is what the plan must correct
- Constitution Type: {vikriti.get('constitution_type', '')}
- Immediate Focus: {vikriti_focus}
- Key Signals: {vikriti_signals[:3]}
{disease_block}
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
    """Panchakarma Agent: generates clinically grounded detox plan using protocol KB."""
    from services.panchakarma_engine import (
        _current_ritu, _determine_shodhana_or_shamana, _select_pradhana_karma,
        _select_aushadha, _samsarjana_krama, pk_protocols,
    )

    profile        = state["user_profile"]
    ml             = state["ml_analysis"]
    dosha_analysis = ml.get("dosha", {})
    pk_rag         = state["rag_context"].get("panchakarma", "")
    pk_constraints = ml.get("medical_constraints", {}).get("panchakarma", {})
    vikriti        = ml.get("vikriti", {})
    vikriti_dom    = vikriti.get("dominant", dosha_analysis.get("dominant_dosha", "pitta"))
    vikriti_sec    = vikriti.get("secondary")
    disease_block  = _build_disease_block(
        ml.get("disease_context", {}), vikriti_dom, "panchakarma",
        profile.get("medical_history") or []
    )

    # Read actual PK prefs from feature_preferences (set by /plans/ route)
    _feat_prefs = profile.get("feature_preferences") or {}
    setting     = "clinic" if _feat_prefs.get("setting") in ("clinic", "both") else "home"
    pk_prefs    = {**_feat_prefs, "setting": setting}
    eligibility = _determine_shodhana_or_shamana(profile, pk_prefs, pk_protocols)
    pradhana    = _select_pradhana_karma(vikriti_dom, vikriti_sec, setting, pk_protocols)
    ritu        = _current_ritu()
    ritu_ctx    = pk_protocols.get("ritu_shodhana_calendar", {}).get(ritu, {})
    koshtha = profile.get("koshtha") or (profile.get("feature_preferences") or {}).get("koshtha") or "sama"
    aushadha    = _select_aushadha(
        vikriti_dom, profile.get("medical_history") or [],
        pradhana["primary"], setting, pk_protocols, koshtha
    )
    samsarjana_stages = _samsarjana_krama(pradhana["primary"], pk_protocols)[:4]

    aushadha_lines = []
    for k, v in aushadha.items():
        name = v.get("name") if isinstance(v, dict) else v
        use  = v.get("use", "") if isinstance(v, dict) else ""
        if name:
            aushadha_lines.append(f"  \u2022 {k.replace('_',' ').title()}: {name}{(' \u2014 ' + use) if use else ''}")
    aushadha_block = "\n".join(aushadha_lines) or "  Standard dosha-specific oils and herbs"

    sk_lines = [
        f"  Stage {s.get('stage')}: {s.get('food')} \u2014 {(s.get('recipe') or '')[:80]}"
        for s in samsarjana_stages if s.get("food")
    ]
    sk_block = "\n".join(sk_lines) or "  Progressive Kitchari re-entry"

    ritu_warning_line = ""
    if any(pradhana["primary"] in a for a in ritu_ctx.get("avoid", [])):
        ritu_warning_line = f"\u26a0 RITU WARNING: {pradhana['primary'].title()} is not ideal in {ritu_ctx.get('ritu_name','')}. Consider {ritu_ctx.get('primary_shodhana','').title()} instead."

    prompt = f"""
Generate a clinically grounded personalised PANCHAKARMA PLAN. Output ONLY valid JSON.

VIKRITI (CURRENT IMBALANCE): {vikriti_dom.upper()}{f' + {vikriti_sec.upper()}' if vikriti_sec else ''} — ALL therapy must PACIFY this dosha
Prakriti (baseline): {dosha_analysis.get('dominant_dosha', 'unknown')}
Ama: {profile.get('ama_indicator','none')} | Agni: {profile.get('agni_type','unknown')} | Ojas: {profile.get('ojas_level','medium')} | Koshtha: {koshtha}
{disease_block}

CLINICAL DECISIONS (from Protocol KB):
SHODHANA vs SHAMANA: {eligibility['type'].upper()} — {"; ".join(eligibility.get('reasons',['patient assessed'])[:2])}
{f"AMA CORRECTION FIRST: {', '.join(eligibility.get('ama_correction_herbs',[]))} for {eligibility.get('ama_correction_duration','3-7 days')}" if eligibility.get('ama_correction_needed') else ''}

PRADHANA KARMA: {pradhana['primary'].upper()}
Reason: {pradhana['reason']}
{f"Sequence: {pradhana.get('sequence','')}" if pradhana.get('sequence') else ''}

RITU: {ritu_ctx.get('ritu_name', ritu.title())} — {ritu_ctx.get('dosha_state','')}
Ideal this season: {ritu_ctx.get('primary_shodhana','').upper() or 'Any'}
{ritu_warning_line}

AUSHADHA:
{aushadha_block}

SAMSARJANA KRAMA (post-PK dietary re-entry):
{sk_block}

CONTRAINDICATIONS: {pk_constraints.get('avoid', [])}
RAG KNOWLEDGE: {pk_rag[:600] if pk_rag else 'Apply classical PK principles per Charaka Siddhi Sthana'}

OUTPUT JSON FORMAT:
{{
  "panchakarma_plan": {{
    "recommended_therapy": "{pradhana['primary']}",
    "shodhana_or_shamana": "{eligibility['type']}",
    "clinical_rationale": "2-3 sentences: why this Pradhana Karma for this Vikriti, referencing Charaka/AH",
    "ritu_note": "1 sentence on seasonal alignment",
    "duration": "",
    "phases": [
      {{"name": "Purvakarma", "days": "", "instructions": "oil type, dose schedule, signs to watch"}},
      {{"name": "Pradhana Karma ({pradhana['primary'].title()})", "days": "", "instructions": "procedure, aushadha, dose, timing, Samyak Yoga signs, Atiyoga warning"}},
      {{"name": "Paschat Karma", "days": "", "instructions": "Samsarjana Krama stages + Rasayana with specific herbs and doses"}}
    ],
    "aushadha_summary": {{"abhyanga_oil": "", "internal_snehana": "", "pradhana_medicine": "", "rasayana": ""}},
    "samsarjana_stages": ["Stage 1: ...", "Stage 2: ..."],
    "pathya": [],
    "apathya": [],
    "home_adaptable": {"true" if setting == "home" else "false"},
    "contraindications_noted": []
  }}
}}
"""
    if state.get("is_adaptation") and state.get("feedback"):
        prompt += f"\n\nADAPTATION REQUIRED: Feedback: '{state.get('feedback')}'."
    if state.get("other_plans_context"):
        prompt += f"\nCROSS-AGENT CONTEXT:\n{json.dumps(state['other_plans_context'])}\n"

    try:
        response = await llm_client.generate(
            prompt=prompt, system_prompt=AYURVEDA_AGENT_PROMPT, temperature=0.6, json_mode=True
        )
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
    disease_block = _build_disease_block(ml.get("disease_context", {}), vikriti_dom, "nutrition", profile.get("medical_history") or [])
    rvp = _RASA_VIRYA_VIPAKA.get(vikriti_dom, _RASA_VIRYA_VIPAKA["vata"])
    trikala = _TRIKALA.get(vikriti_dom, _TRIKALA["vata"])
    ojas_level = profile.get("ojas_level") or "medium"
    _ojas_nutrition = {
        "low":    "Prioritise Ojas-building foods: ghee, warm milk, dates, almonds, saffron, Amalaki, well-cooked whole foods. No raw, cold, or processed foods.",
        "medium": "Support Ojas with Sattvic diet — fresh, well-cooked, seasonal. Moderate use of ghee and warm milk.",
        "high":   "Maintain Ojas with Rasayana additions — seasonal fruit, ghee, Amalaki.",
    }.get(ojas_level, "")
    satmya = profile.get("satmya")
    _satmya_note = {
        "less_than_1y": "User has been in current diet pattern less than 1 year — gradual transition advised. Do not make abrupt dietary changes. 30-day phased approach.",
        "1_to_5y":      "User has 1–5 years of current Satmya — moderate adaptation capacity. Changes can be implemented over 2–4 weeks.",
        "over_5y":      "User has 5+ years of Satmya in current pattern — strong habituation. Changes must be very gradual (3-month plan). Respect Satmya even if diet is suboptimal.",
    }.get(satmya, "")

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
{f'- Satmya (Habitual Pattern): {_satmya_note}' if _satmya_note else ''}

CLASSICAL DRAVYAGUNA PRINCIPLES (Rasa-Virya-Vipaka) for {vikriti_dom.title()} Pacification:
- Rasa to FAVOR: {rvp['favor_rasa']}
- Rasa to AVOID: {rvp['avoid_rasa']}
- Virya (potency): {rvp['virya']}
- Vipaka (post-digestive effect): {rvp['vipaka']}
- Mahabhuta: {rvp['mahabhuta']}
- Key Foods: {rvp['key_foods']}
- Foods to AVOID: {rvp['avoid_foods']}
- Eating Principles (Ahara Vidhi Visheshayatana): {rvp['eating_principles']}

TRIKALA — DOSHIC DAILY CLOCK (Charaka Samhita Sutrasthana 30):
- {vikriti_dom.title()} peak times: {trikala['peak_times']}
- Meal Timing: {trikala['meal_timing']}
- Optimal Medicine/Supplement Time: {trikala['medicine_time']}
{disease_block}

DIETARY RESTRICTIONS (Medical Safety):
- AVOID: {constraints.get('avoid', [])}
- PREFER: {constraints.get('prefer', [])}
- MODIFICATIONS: {constraints.get('modifications', [])}

NUTRITION KNOWLEDGE (RAG): {rag[:2000] if rag else 'Use dosha diet principles'}

OJAS STATUS ({ojas_level.upper()}): {_ojas_nutrition}
{_VIRUDDHA_AHARA}
CRITICAL RULE: Design this diet primarily to CORRECT {vikriti_dom} Vikriti imbalance{f' and secondary {vikriti_sec} imbalance' if vikriti_sec else ''}. The Prakriti (constitution) informs the baseline, but Vikriti is what needs active correction now.
Include a 'classical_rationale' field in each meal entry explaining the Rasa-Virya-Vipaka reasoning for that meal.
Each day must include a "viruddha_warnings" field (list any Viruddha Ahara pairs to avoid, or empty list).

OUTPUT JSON FORMAT:
{{
  "weekly_plan": {{
    "day1": {{"breakfast": {{"meal": "", "calories": 0, "classical_rationale": ""}}, "lunch": {{"meal": "", "calories": 0, "classical_rationale": ""}}, "snack": {{"meal": "", "calories": 0, "classical_rationale": ""}}, "dinner": {{"meal": "", "calories": 0, "classical_rationale": ""}}, "viruddha_warnings": []}},
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
    disease_block = _build_disease_block(ml.get("disease_context", {}), vikriti_dom, "remedy", profile.get("medical_history") or [])
    ojas_level = profile.get("ojas_level") or "medium"
    _ojas_remedy = {
        "low":    "RASAYANA IS PRIMARY — Chyawanprash 1 tsp twice daily, Ashwagandha 500mg with warm milk at night, Shatavari (if female). No fasting. No vigorous exercise. Prioritise sleep.",
        "medium": "Support Ojas with Chyawanprash, Guduchi Satva, Amalaki. Address Ama first.",
        "high":   "Maintain Ojas with seasonal Rasayana. Current immunity is strong.",
    }.get(ojas_level, "")

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
MEDICATIONS: {profile.get('current_medications', [])}
USER RATING PREFERENCES: {profile.get('rating_preferences', {})}
{disease_block}

HERBS/INGREDIENTS TO AVOID (Medical Safety): {constraints.get('avoid', [])}
HERB INTERACTIONS TO WARN ABOUT: {constraints.get('herb_interactions', [])}

REMEDY KNOWLEDGE (RAG): {rag[:2500] if rag else 'Use classical Ayurvedic remedies'}

OJAS STATUS: {ojas_level.upper()} — {_ojas_remedy}

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
    disease_block = _build_disease_block(ml.get("disease_context", {}), vikriti_dom, "medicine", profile.get("medical_history") or [])

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
MEDICATIONS: {profile.get('current_medications', [])}
{disease_block}

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
    trikala = _TRIKALA.get(dosha, _TRIKALA["vata"])

    try:
        tip = await llm_client.generate(
            prompt=(
                f"Write a practical 2-sentence Ayurvedic daily wellness tip for a {dosha} dominant person.\n"
                f"Context: {dosha.title()} peaks at {trikala['peak_times']}. "
                f"Today's focus: {category}.\n"
                f"Reference from: {raw_tip}\n"
                "The tip should be specific, actionable, and mention optimal timing if relevant."
            ),
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

