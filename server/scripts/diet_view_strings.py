"""The diet screen's own strings, read out of `DietView.jsx`.

`t('diet.key', 'English default', {...})` is the only way a string reaches that
screen, so the JSX is the source of truth for the English: this reads every call,
plus the slot and day names built from tables, and `--write` puts them in
`client/src/locales/en.json` under `diet`. `tests/test_diet_view_i18n.py` uses the
same reader to hold every locale to the same keys and placeholders.

    python scripts/diet_view_strings.py            # print the extracted strings
    python scripts/diet_view_strings.py --write    # update en.json's `diet` section
"""
import json
import re
import sys
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[2] / "client"
JSX = CLIENT / "src" / "components" / "planViews" / "DietView.jsx"
LOCALES = CLIENT / "src" / "locales"

_CALL = re.compile(r"""t\(\s*'diet\.([A-Za-z0-9_]+)'\s*,\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")""")
# i18next picks `<key>_one` / `<key>_other` from `count`; English needs both.
_PLURAL = re.compile(r"""t\(\s*'diet\.([A-Za-z0-9_]+)'[^)]*\{\s*count:""")
_TABLE = re.compile(r"const (SLOT_LABEL|DIET_DAY_LABELS|DIET_DAY_FULL)\s*=\s*([\[{][^\]}]*[\]}])")
_PLURAL_ONE = {
    "mealsLogged": "{{count}} meal logged",
    "resizedComputed": "Portions on {{count}} day were resized so the day meets your targets; the dishes are unchanged.",
    "resizedLegacy": "Portions on {{count}} day were resized to meet this target — the meals and their Ayurvedic reasoning are unchanged.",
    "proteinShortDays": "Protein is below your {{floor}} g floor on {{count}} day",
    "keptEnglish": "{{count}} line that could not be verified is left in English.",
}


def placeholders(text: str) -> set:
    return set(re.findall(r"\{\{\s*(\w+)\s*\}\}", text))


def extract() -> dict:
    src = JSX.read_text()
    src = src[: src.index("// ── RemedyView")]
    out = {}
    for m in _CALL.finditer(src):
        key, a, b = m.group(1), m.group(2), m.group(3)
        text = (a if a is not None else b).replace("\\'", "'").replace('\\"', '"')
        if key in out and out[key] != text:
            raise ValueError(f"diet.{key} has two different defaults")
        out[key] = text
    for key in sorted(set(_PLURAL.findall(src))):
        out[f"{key}_other"] = out.pop(key)
        out[f"{key}_one"] = _PLURAL_ONE[key]
    tables = {n: v for n, v in _TABLE.findall(src)}
    for k, v in re.findall(r"(\w+): '([^']+)'", tables["SLOT_LABEL"]):
        out[f"slot_{k}"] = v
    for d in re.findall(r"'(\w+)'", tables["DIET_DAY_LABELS"]):
        out[f"day_{d}"] = d
    for d in re.findall(r"'(\w+)'", tables["DIET_DAY_FULL"]):
        out[f"dayFull_{d}"] = d
    # The meal-log buttons name their key in the table that defines them.
    for label, key in re.findall(r"label: '([^']+)', i18n: 'diet\.(\w+)'", src):
        out[key] = label
    return dict(sorted(out.items()))


def write() -> None:
    path = LOCALES / "en.json"
    data = json.loads(path.read_text())
    data["diet"] = extract()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    if "--write" in sys.argv:
        write()
        print(f"wrote {len(extract())} diet strings to en.json")
    else:
        print(json.dumps(extract(), ensure_ascii=False, indent=1))
