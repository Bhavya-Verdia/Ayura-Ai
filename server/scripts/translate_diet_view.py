"""Translate the diet screen's own strings (en.json `diet`) into the app's other locales.

The plan's content is translated per plan, at read time (`services/diet_translate`);
these are the screen's labels and fixed sentences, translated once and committed.
Every translation keeps the English's `{{placeholders}}` exactly, or it is asked for
again; one that still fails is left out, and i18next shows the English for it.

    python scripts/translate_diet_view.py            # strings a locale lacks, all seven locales
    python scripts/translate_diet_view.py hi ta      # some
    python scripts/translate_diet_view.py --all hi   # every string again

By default only the strings a locale lacks are translated, and the rest are kept:
several were corrected by hand after the first run (the Sanskrit "Ate it" meant "not
eaten"), and translating everything again would undo them. Read what it writes.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.diet_view_strings import LOCALES, placeholders  # noqa: E402

LANGS = {"hi": "Hindi", "kn": "Kannada", "ta": "Tamil", "sa": "Sanskrit",
         "es": "Spanish", "fr": "French", "zh": "Simplified Chinese"}

SYSTEM = (
    "You translate the interface of an Ayurvedic diet app. Translate each value "
    "faithfully and naturally, as the app would read to a patient. Keep every "
    "{{placeholder}} exactly as written, untranslated. Keep units (kcal, g, mg, µg, L) "
    "and the '·' and '—' marks. Write Ayurvedic terms (Pathya, Apathya, Viruddha Ahara, "
    "Agni, Dosha, Dinacharya, Ahar Vidhi, Phalahar, Charaka Sutrasthana) in the target "
    "script, not translated into modern words. Keys ending _one are the singular form "
    "and _other the plural of the same sentence. 'Vegan' means no animal food including "
    "dairy; never use the word for vegetarian. The five meal labels (breakfast, lunch, "
    "snack, dinner, daily drink) must be five different words. The log buttons are what "
    "the patient taps: 'Ate it' means the meal WAS eaten, 'Skipped' that it was not — "
    "check the polarity of each. Return only JSON.")

# Ayurvedic terms in each Indian script. The model kept them in Latin letters inside
# Devanagari sentences when only told "the target script".
GLOSSARY = {
    "hi": "Pathya=पथ्य, Apathya=अपथ्य, Viruddha Ahara=विरुद्ध आहार, Agni=अग्नि, Dosha=दोष, "
          "Dinacharya=दिनचर्या, Ahar Vidhi=आहार विधि, Phalahar=फलाहार, Charaka Sutrasthana=चरक सूत्रस्थान, "
          "breakfast=नाश्ता, snack=अल्पाहार, Fib=फ़ाइबर, Vitamin=विटामिन",
    "sa": "Pathya=पथ्यम्, Apathya=अपथ्यम्, Viruddha Ahara=विरुद्धाहारः, Agni=अग्निः, Dosha=दोषः, "
          "Dinacharya=दिनचर्या, Ahar Vidhi=आहारविधिः, Phalahar=फलाहारः, Charaka Sutrasthana=चरकसूत्रस्थानम्, "
          "Ate it=भुक्तम्, Skipped=त्यक्तम्, breakfast=प्रातराशः, snack=अल्पाहारः",
    "kn": "Pathya=ಪಥ್ಯ, Apathya=ಅಪಥ್ಯ, Viruddha Ahara=ವಿರುದ್ಧ ಆಹಾರ, Agni=ಅಗ್ನಿ, Dosha=ದೋಷ, "
          "Dinacharya=ದಿನಚರ್ಯ, Ahar Vidhi=ಆಹಾರ ವಿಧಿ, Phalahar=ಫಲಾಹಾರ, Charaka Sutrasthana=ಚರಕ ಸೂತ್ರಸ್ಥಾನ",
    "ta": "Pathya=பத்தியம், Apathya=அபத்தியம், Viruddha Ahara=விருத்த ஆகாரம், Agni=அக்னி, Dosha=தோஷம், "
          "Dinacharya=தினசரியா, Ahar Vidhi=ஆகார விதி, Phalahar=பலாகாரம், Charaka Sutrasthana=சரக சூத்திரஸ்தானம்",
}

PROMPT = """Translate every value into {language}. Return only JSON: {{"t": {{"<same key>": "<translation>"}}}}.{glossary}
{items}"""


def ok(en: str, tr) -> bool:
    return (isinstance(tr, str) and tr.strip() != ""
            and placeholders(en) == placeholders(tr)
            and en.count("·") == tr.count("·"))


async def translate(lang: str, english: dict) -> dict:
    from ai.llm_client import llm_client

    out: dict = {}
    todo = dict(english)
    for _ in range(3):
        if not todo:
            break
        items = list(todo.items())
        for i in range(0, len(items), 70):
            chunk = dict(items[i:i + 70])
            try:
                raw = await llm_client.generate(
                    prompt=PROMPT.format(language=LANGS[lang],
                                         glossary=(f"\nUse these words: {GLOSSARY[lang]}."
                                                   if lang in GLOSSARY else ""),
                                         items=json.dumps(chunk, ensure_ascii=False, indent=1)),
                    system_prompt=SYSTEM, json_mode=True, temperature=0.2, max_tokens=8000)
                got = json.loads(raw).get("t") or {}
            except Exception as e:  # noqa: BLE001 — retried below
                print(f"  {lang}: batch failed: {e}")
                continue
            for k, v in got.items():
                if k in chunk and ok(chunk[k], v):
                    out[k] = v.strip()
        todo = {k: v for k, v in english.items() if k not in out}
    if todo:
        print(f"  {lang}: left in English: {sorted(todo)}")
    return dict(sorted(out.items()))


async def main(langs, everything=False):
    english = json.loads((LOCALES / "en.json").read_text())["diet"]
    for lang in langs:
        path = LOCALES / f"{lang}.json"
        data = json.loads(path.read_text())
        have = {} if everything else {k: v for k, v in (data.get("diet") or {}).items()
                                      if k in english}
        todo = {k: v for k, v in english.items() if k not in have}
        data["diet"] = dict(sorted({**have, **(await translate(lang, todo) if todo else {})}.items()))
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f"{lang}: {len(data['diet'])}/{len(english)} ({len(todo)} translated)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--all"]
    asyncio.run(main(args or list(LANGS), everything="--all" in sys.argv))
