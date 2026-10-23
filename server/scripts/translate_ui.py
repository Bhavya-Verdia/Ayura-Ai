"""Translate the app's screen strings (en.json `ui`) into the other seven languages.

`client/scripts/i18n-strings.mjs` writes en.json's `ui` section from the `tr()` calls in
the source; this fills hi, kn, ta, sa, es, fr and zh. Every translation keeps the
English's `{{placeholders}}` exactly or it is asked for again; one that still fails is
left out, and the screen shows the English for it.

    python scripts/translate_ui.py              # strings a locale lacks, all seven
    python scripts/translate_ui.py hi ta        # some
    python scripts/translate_ui.py --all hi     # every string again

Only missing strings are translated by default, so a hand correction survives a rerun
(the diet screen's first Sanskrit "Ate it" meant "not eaten"). Read what it writes.
"""
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.translate_diet_view import GLOSSARY, LANGS  # noqa: E402

LOCALES = Path(__file__).resolve().parents[2] / "client" / "src" / "locales"

SYSTEM = (
    "You translate the interface of an Ayurvedic wellness app (buttons, labels, headings, "
    "help text and messages) for patients. Translate each value faithfully and naturally, "
    "short where the English is short: a button stays a button-length phrase. Numbered tags such as <0>…</0> and <1/> mark bold text or links: keep each one, around the words that translate the words it wrapped, and move it wherever the sentence needs it. Keep every "
    "{{placeholder}} exactly as written, untranslated. Keep units (kg, cm, kcal, g, mg, min, "
    "%), numbers, emoji and the marks · — → ← × ✦ ↻ exactly. Keep brand names (Ayura AI, "
    "Google, GitHub, WhatsApp) in Latin letters. Write Ayurvedic terms (Dosha, Vata, Pitta, "
    "Kapha, Prakriti, Vikriti, Agni, Ama, Ojas, Pathya, Apathya, Panchakarma, Dinacharya, "
    "Ritucharya, Koshtha, Shodhana, Shamana, Rasayana, Vaidya, Pranayama, asana names) in "
    "the target language's script, not translated into modern words. Use the everyday "
    "name a patient knows for a disease. 'Vegan' means no animal food including dairy and "
    "'vegetarian' includes dairy; never swap them. In an Indian-script language write no "
    "English word in Latin letters (only Ayura, Google, GitHub, WhatsApp, units and "
    "acronyms stay Latin): write wellness, insight, feed, healing in the language itself. Keep the polarity of every choice exactly "
    "('Ate it' is eaten, 'Skipped' is not eaten; 'Getting worse' is worse). Return only JSON.")

PROMPT = """Translate every value into {language}. Return only JSON: {{"t": {{"<same key>": "<translation>"}}}}.{glossary}
{items}"""

_PH = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_TAG = re.compile(r"</?\d+/?>")
_MARKS = "·→←×✦↻"


def placeholders(text: str) -> set:
    return set(_PH.findall(text))


def flatten(tree: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in tree.items():
        if isinstance(v, dict):
            out.update(flatten(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def nest(flat: dict) -> dict:
    tree: dict = {}
    for key in sorted(flat):
        node = tree
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = flat[key]
    return tree


# Latin words an Indian-script string may keep: names, units, acronyms. Anything else
# ("wellness", "healing", "feed", "Pitta") is an untranslated word in the sentence.
_KEEP_LATIN = re.compile(
    r"Ayura(?: AI)?|Google|GitHub|WhatsApp|FODMAPs?|HbA1c|eGFR|kcal|Ctrl|Shift|Enter|Esc|"
    r"\{\{\s*\w+\s*\}\}|\b[A-Z0-9]{2,6}s?\b|\b(?:kg|cm|mg|ml|min|g|L)\b")
_INDIC = {"hi", "kn", "ta", "sa"}


def ok(en: str, tr, lang: str = "") -> bool:
    if not (isinstance(tr, str) and tr.strip() != ""
            and placeholders(en) == placeholders(tr)
            and all(en.count(m) == tr.count(m) for m in _MARKS)
            and len(tr) <= 4 * len(en) + 40
            # <Trans> markup: the same numbered tags, each still opened and closed.
            and sorted(_TAG.findall(en)) == sorted(_TAG.findall(tr))):
        return False
    if lang in _INDIC and re.search(r"[A-Za-z]{3,}", _KEEP_LATIN.sub(" ", tr)):
        return False
    return True


async def translate(lang: str, english: dict) -> dict:
    from ai.llm_client import llm_client

    sem = asyncio.Semaphore(6)
    out: dict = {}

    async def batch(chunk: dict, strict: bool = True) -> dict:
        async with sem:
            try:
                raw = await llm_client.generate(
                    prompt=PROMPT.format(
                        language=LANGS[lang],
                        glossary=(f"\nUse these words: {GLOSSARY[lang]}." if lang in GLOSSARY else ""),
                        items=json.dumps(chunk, ensure_ascii=False, indent=0)),
                    system_prompt=SYSTEM, json_mode=True, temperature=0.2, max_tokens=8000)
                got = json.loads(raw).get("t") or {}
                return {k: v for k, v in got.items() if k in chunk and ok(chunk[k], v, lang if strict else '')}
            except Exception as e:  # noqa: BLE001 — retried below, then left English
                print(f"  {lang}: batch failed ({e})")
                return {}

    todo = dict(english)
    for attempt in range(3):
        if not todo:
            break
        items = list(todo.items())
        # The last pass lets a Latin word stand: an email address, a drug name or an
        # acronym the model would not write any other way, and a Hindi sentence with
        # one English word reads better than the whole sentence left in English.
        results = await asyncio.gather(*(batch(dict(items[i:i + 60]), strict=attempt < 2)
                                         for i in range(0, len(items), 60)))
        for r in results:
            out.update(r)
        todo = {k: v for k, v in todo.items() if k not in out}
        print(f"  {lang}: pass {attempt + 1}, {len(out)} done, {len(todo)} left")
    return out


async def main(langs, redo_all):
    en = flatten(json.loads((LOCALES / "en-ui.json").read_text())["ui"])

    async def one(lang):
        path = LOCALES / f"{lang}.json"
        data = json.loads(path.read_text())
        have = flatten(data.get("ui") or {})
        # A translation is kept only while the English it was made from is unchanged.
        # A key can keep its name while its text moves (a numbered key, a reworded
        # sentence), and a check on placeholders alone kept the old translation.
        made_from = sources.get(lang, {})
        have = {k: v for k, v in have.items()
                if k in en and made_from.get(k) == en[k] and ok(en[k], v)}
        need = en if redo_all else {k: v for k, v in en.items() if k not in have}
        print(f"{lang}: {len(need)} to translate")
        got = await translate(lang, need) if need else {}
        data["ui"] = nest({**have, **got})
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        sources[lang] = {k: en[k] for k in {**have, **got}}
        print(f"{lang}: {len({**have, **got})}/{len(en)} strings")

    sources_path = LOCALES / "ui-sources.json"
    sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
    await asyncio.gather(*(one(lang) for lang in langs))
    sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    asyncio.run(main(args or list(LANGS), "--all" in sys.argv))
