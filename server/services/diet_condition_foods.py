"""
The authored food library's per-condition Pathya and Apathya, made usable by the
LLM-primary diet path.

`diet_foods.json` carries 370 (condition, food) Apathya claims and 338 Pathya claims,
authored row by row in `scripts/diet_library/`. Exactly one thing read the Apathya
side: `diet_plan_engine`, which is the **fallback**. On the LLM-primary path — the one
every user actually gets — the condition floor is `ahara_safety._CONDITION_APATHYA_TERMS`,
a separately hand-written list, and measuring the two against each other gives 333 of
370 exclusions unenforced there and all 338 Pathya claims unenforced anywhere. An
acidity patient could be served green tea, lemon water, curd, dry ginger and black
pepper — every one of them authored as Apathya for acidity — because the scan table
does not name them. The fallback was clinically stricter than the primary path.

This module turns the rows into two things the primary path can use: named foods for
the brief, so the model is told before it writes, and scan terms for
`apply_condition_food_safety`, so the instruction is checked afterwards.

## Deriving a scan term from a food name is where this goes wrong

The failure mode is a term that matches more than the food it came from. The library
is built to distinguish `ginger_fresh` from `ginger_dry` and `banana` (ripe) from
`raw_banana`, because they have opposite indications — and a term "ginger" or "banana"
throws that distinction away. It has already happened: the condition scan flagged a
*ripe* banana for constipation, where the library contraindicates only the unripe one.

So a surface form is only used where it is **unambiguous within the library itself**,
and ambiguity is resolved per condition rather than globally:

* A term matching several foods is usable for a condition only when **every** food it
  matches agrees about that condition. "banana" matches both banana rows and they
  disagree about constipation, so no term is emitted — the ripe-banana false positive
  cannot be recreated. "cow's ghee" matches two rows that agree on all three of their
  conditions, so it stays.
* This is what keeps the same-food-entered-twice rows honest. `kidney_beans` and
  `rajma` are the same bean in two categories and disagree about whether it is Pathya
  in diabetes; `chana_dal`/`chhole` and `lentils_brown`/`masoor_dal` disagree too.
  Until a Vaidya rules on those (they are in the review packet), the conservative
  reading is the one that acts: no shared term speaks for a condition its own rows
  cannot agree on.

Nothing here is derived from Apathya *prose*. `_food_headword` on a phrase like "new
rice" yields `rice` and flags every khichdi — that lesson is recorded in
`ahara_safety` and is not relitigated here.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_FOODS_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / "diet_foods.json"

# A surface form shorter than this matches too much of ordinary meal prose.
_MIN_TERM_LEN = 3

# A parenthetical is usually the English translation of the Sanskrit head — 'Shunthi
# (Dry Ginger)' — but sometimes it is a variant instead: 'Tofu (Firm)'. Taking that
# half as a name yields the term "firm", which fired against a hypothyroid patient on
# a meal that merely described a texture. A surface that is nothing but a modifier is
# not a food name.
_MODIFIER_ONLY = frozenset({
    "firm", "soft", "raw", "dry", "fresh", "whole", "sweet", "green", "cooked",
    "roasted", "ripe", "unripe", "plain", "hard", "light", "tender", "split",
    "sprouted", "fermented", "powder", "seed", "seeds", "leaf", "leaves",
})


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).lower().strip())


def _surfaces(food: dict) -> set[str]:
    """Every way a generated meal might name this food.

    Library names are written "Sanskrit (English)" — 'Shunthi (Dry Ginger)' — or as a
    bare English name. Both halves are searched, because meals use both, and so is the
    id with underscores opened out, which catches names the two halves miss.
    """
    out: set[str] = set()
    name = str(food.get("name") or "")
    match = re.match(r"^(.*?)\s*\((.*)\)\s*$", name)
    if match:
        out.add(_norm(match.group(1)))
        out.add(_norm(match.group(2)))
    elif name:
        out.add(_norm(name))
    if food.get("sanskrit_name"):
        out.add(_norm(food["sanskrit_name"]))
    out.add(_norm(str(food.get("id") or "").replace("_", " ")))
    return {
        t for t in out
        if len(t) >= _MIN_TERM_LEN and t not in _MODIFIER_ONLY
    }


@lru_cache(maxsize=1)
def _library() -> list[dict]:
    try:
        raw = json.loads(_FOODS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return raw if isinstance(raw, list) else (raw.get("foods") or [])


@lru_cache(maxsize=1)
def _term_owners() -> dict[str, frozenset[str]]:
    """Every surface form in the library, mapped to the food ids it can match.

    A term with more than one owner is not discarded here — whether it is usable
    depends on whether its owners agree about the condition in question, which is
    decided in `condition_food_rules`.
    """
    foods = _library()
    identity = {
        food["id"]: " | ".join(sorted(_surfaces(food)))
        for food in foods if food.get("id")
    }
    owners: dict[str, set[str]] = {}
    for food in foods:
        for term in _surfaces(food):
            if term in owners:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)")
            owners[term] = {
                fid for fid, text in identity.items() if pattern.search(text)
            }
    return {term: frozenset(ids) for term, ids in owners.items()}


@lru_cache(maxsize=1)
def _by_id() -> dict[str, dict]:
    return {f["id"]: f for f in _library() if f.get("id")}


# Library condition keys that an app condition should also read. The app's canonical
# vocabulary (`engine/condition_vocab`) and the library's tags were authored
# separately and do not line up everywhere:
#
# The `hemorrhoids` -> `arsha` and `constipation_chronic` -> `constipation` entries
# that used to live here have moved to `ahara_safety._COND_CANON`, which is now the
# single canonical-condition table for the whole diet feature; they belonged there,
# not in a library-specific map. What remains is genuinely library-specific:
#
# * `grahani` is reachable from no app condition at all. Its 22 Apathya foods are a
#   strict subset of `ibs`'s 44 and its Pathya list adds 11 foods `ibs` does not
#   carry, so the library's own tagging treats it as the classical companion label
#   for the same territory, and 11 authored recommendations were unreachable.
_LIBRARY_CONDITION_ALIASES: dict[str, tuple[str, ...]] = {
    "ibs": ("ibs", "grahani"),
    "grahani": ("grahani", "ibs"),
}


def _library_keys(condition: str) -> tuple[str, ...]:
    key = _norm(condition).replace(" ", "_").replace("-", "_")
    return _LIBRARY_CONDITION_ALIASES.get(key, (key,))


@lru_cache(maxsize=None)
def condition_food_rules(condition: str) -> dict:
    """The library's Apathya and Pathya for one canonical condition.

    Returns {"apathya_terms": [...], "apathya_names": [...], "pathya_names": [...]}.
    `apathya_terms` are safe to match against meal text; the name lists are for the
    brief, where precision matters less because the model is reading them as guidance
    rather than firing a warning off them.
    """
    keys = set(_library_keys(condition))
    by_id = _by_id()
    apathya_ids = {
        fid for fid, food in by_id.items()
        if keys & {_norm(c) for c in (food.get("apathya_for") or ())}
    }
    pathya_ids = {
        fid for fid, food in by_id.items()
        if keys & {_norm(c) for c in (food.get("pathya_for") or ())}
    }
    # A food that is Apathya under one of this condition's keys and Pathya under
    # another is not offered as a recommendation. The restriction wins, which is the
    # same direction `_CONDITION_PRIORITY` resolves a multi-condition conflict.
    pathya_ids -= apathya_ids

    terms: list[str] = []
    for term, owners in _term_owners().items():
        if not owners & apathya_ids:
            continue
        # Every food this term can match must agree that it is Apathya here. One
        # dissenting owner — the ripe banana beside the unripe one — and the term is
        # dropped rather than allowed to speak for both.
        if owners <= apathya_ids:
            terms.append(term)

    def _label(fid: str) -> str:
        return str(by_id[fid].get("name") or fid)

    # Deduplicated by label: the same food is entered twice under two categories in
    # a few places (ghee as dairy and as an oil, sweet corn as grain and vegetable),
    # and listing it twice in the brief reads as an error.
    return {
        "apathya_terms": sorted(terms),
        "apathya_names": sorted({_label(f) for f in apathya_ids}),
        "pathya_names": sorted({_label(f) for f in pathya_ids}),
    }


def library_conditions() -> set[str]:
    """Canonical conditions the library has any claim about."""
    out: set[str] = set()
    for food in _library():
        out.update(_norm(c) for c in (food.get("apathya_for") or ()))
        out.update(_norm(c) for c in (food.get("pathya_for") or ()))
    return out


def withheld_claims() -> list[tuple[str, str]]:
    """(shared name, condition) pairs the agreement rule refuses to act on.

    A name owned by several foods can only speak for a condition all of them agree
    about, so where they disagree the claim is authored and does not fire. Most of
    these are the rule working — "banana" is withheld for diabetes because only the
    ripe row carries it, and the raw row is a different food. It is counted rather
    than listed because the number moving is the signal: a new collision means a
    newly authored claim has gone quiet, which is exactly the failure this module
    exists to make visible rather than silent.
    """
    by_id = _by_id()
    out: list[tuple[str, str]] = []
    for term, owners in _term_owners().items():
        if len(owners) < 2:
            continue
        claimed: dict[str, set[str]] = {}
        for fid in owners:
            for cond in (by_id[fid].get("apathya_for") or ()):
                claimed.setdefault(_norm(cond), set()).add(fid)
        for cond, claimers in claimed.items():
            if claimers != set(owners):
                out.append((term, cond))
    return sorted(out)
