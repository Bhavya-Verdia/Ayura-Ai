"""The diet plan in the reader's language, laid over the checked English plan.

Every food-safety gate in `ahara_safety` reads English and Sanskrit in Latin script;
a meal written in Devanagari or Tamil raised no alert from any of them. Translating
the plan's source fields would therefore have switched the safety model off without
a single test failing. So a translation is never written into the plan:

  * the plan is generated, composed, scanned and repaired in English, and its
    components are food ids — that is what is checked, and what is stored;
  * this module translates only DISPLAY strings, into a separate overlay
    `{path: text}` stored beside the plan, which no gate reads and nothing feeds
    back into generation;
  * `ahara_safety.apply_script_guard` refuses any meal whose scanned fields are in a
    script the gates cannot read, so a translation that leaked into the source would
    be caught as unverified rather than passed as checked.

Each translated string is held to what can be checked without reading it: every
number in the English must appear unchanged (grams, kcal, days, doses), a portion
line keeps its item count, and it may not be empty or wildly longer. A string that
fails stays in English. The residual risk — a translator naming a food the English
does not — is why the reader can always switch back to the English plan, which is
the one that was checked, and why the screen says so.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re

logger = logging.getLogger("ayura")

LANGUAGES = {"hi": "Hindi", "kn": "Kannada", "ta": "Tamil", "sa": "Sanskrit",
             "es": "Spanish", "fr": "French", "zh": "Simplified Chinese"}

_MEAL_FIELDS = ("meal_name", "portion", "ayurvedic_note", "description")
_DRINK_FIELDS = ("name", "when", "recipe", "rationale")
_SLOTS = ("breakfast", "lunch", "snack", "dinner")
_PROSE = ("plan_title", "plan_description", "condition_coaching", "hydration_guidance",
          "fasting_guidance", "seasonal_note", "ahar_vidhi", "motivational_note",
          "fasting_notice")
_LISTS = (("pathya_apathya", "pathya"), ("pathya_apathya", "apathya"),
          ("pathya_apathya", "viruddha_ahara_warnings"), ("nutrient_targets", "notes"),
          ("energy_reconciliation", "micronutrients", "notices"))
_BATCH = 80

SYSTEM = (
    "You translate a patient's diet plan for display. Translate faithfully and "
    "naturally into the target language. Never add, remove or substitute any food, "
    "ingredient, quantity, time or instruction. Keep every number exactly as written, "
    "in Western digits (0-9), with its unit. Use the everyday local name of each food "
    "a cook in that language would recognise; keep Sanskrit Ayurvedic terms (Agni, "
    "Pitta, Pathya) in the target script. Keep the ' · ' separators in portion lines. "
    "'Vegan' means no animal food at all, dairy included: never translate it with the "
    "word for vegetarian (in Hindi use वीगन, not शाकाहारी).")

PROMPT = """Translate each value into {language}. Return only JSON, exactly {{"t": {{"<same key>": "<translation>"}}}} with every key.
{items}"""


def _get(obj, path):
    for p in path:
        if isinstance(obj, list):
            obj = obj[p] if isinstance(p, int) and p < len(obj) else None
        elif isinstance(obj, dict):
            obj = obj.get(p)
        else:
            return None
    return obj


def display_strings(plan: dict) -> dict[str, str]:
    """{dotted path: English text} for every string a reader sees."""
    out: dict[str, str] = {}

    def put(path, value):
        if isinstance(value, str) and value.strip():
            out[".".join(str(p) for p in path)] = value

    for f in _PROSE:
        put((f,), plan.get(f))
    for path in _LISTS:
        for i, v in enumerate(_get(plan, path) or []):
            put((*path, i), v)
    for i, n in enumerate(plan.get("clinical_notes") or []):
        if isinstance(n, dict):
            put(("clinical_notes", i, "topic"), n.get("topic"))
            put(("clinical_notes", i, "note"), n.get("note"))
    for i, m in enumerate(plan.get("medication_interactions") or []):
        if isinstance(m, dict):
            put(("medication_interactions", i, "medication"), m.get("medication"))
            put(("medication_interactions", i, "advice"), m.get("advice"))
    for wi, w in enumerate(plan.get("diet_weeks") or []):
        put(("diet_weeks", wi, "phase_description"), w.get("phase_description"))
        for d, day in (w.get("daily_plan") or {}).items():
            put(("diet_weeks", wi, "daily_plan", d, "theme"), day.get("theme"))
            for s in _SLOTS:
                for f in _MEAL_FIELDS:
                    put(("diet_weeks", wi, "daily_plan", d, s, f), (day.get(s) or {}).get(f))
            for f in _DRINK_FIELDS:
                put(("diet_weeks", wi, "daily_plan", d, "special_drink", f),
                    (day.get("special_drink") or {}).get(f))
    return out


def source_hash(strings: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(strings, sort_keys=True).encode()).hexdigest()[:16]


_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def faithful(english: str, translated, path: str = "") -> bool:
    """What can be verified about a translation without reading it."""
    if not isinstance(translated, str) or not translated.strip():
        return False
    if sorted(_NUM.findall(english)) != sorted(_NUM.findall(translated)):
        return False
    if path.endswith(".portion") and english.count("·") != translated.count("·"):
        return False
    return len(translated) <= 4 * len(english) + 40


async def translate_diet_plan(plan: dict, lang: str) -> dict:
    """{"lang", "source_hash", "strings": {path: text}, "kept_english": n}."""
    from ai.llm_client import llm_client

    if lang not in LANGUAGES:
        raise ValueError(f"unsupported language: {lang}")
    english = display_strings(plan)
    paths = list(english)
    sem = asyncio.Semaphore(4)

    async def batch(chunk: list[str]) -> dict[str, str]:
        keys = {f"k{i}": p for i, p in enumerate(chunk)}
        items = json.dumps({k: english[p] for k, p in keys.items()}, ensure_ascii=False)
        async with sem:
            for attempt in range(2):
                try:
                    raw = await llm_client.generate(
                        prompt=PROMPT.format(language=LANGUAGES[lang], items=items),
                        system_prompt=SYSTEM, json_mode=True, temperature=0.2,
                        max_tokens=8000)
                    got = json.loads(raw).get("t") or {}
                    return {keys[k]: v for k, v in got.items() if k in keys}
                except Exception as e:  # noqa: BLE001 — the English is the fallback
                    logger.warning(f"diet translation batch failed ({attempt + 1}): {e}")
        return {}

    results = await asyncio.gather(*(batch(paths[i:i + _BATCH])
                                     for i in range(0, len(paths), _BATCH)))
    strings: dict[str, str] = {}
    for got in results:
        for p, text in got.items():
            if faithful(english[p], text, p):
                strings[p] = text
    return {"lang": lang, "source_hash": source_hash(english), "strings": strings,
            "kept_english": len(paths) - len(strings), "total": len(paths)}
