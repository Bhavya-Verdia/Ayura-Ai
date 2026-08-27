"""The vocabulary an authored food library is written in.

Every field here exists because `scripts/seed_diet_foods.py` is currently inferring
it. That generator produces the whole Ayurvedic layer of `diet_foods.json` from a
ten-row table of category defaults, roughly six hand-listed name overrides per axis,
and substring matches on the food's id (`if "bitter" in name`). Measured over its 150
rows: six distinct rasa combinations, eight of twenty-seven possible dosha triples,
`season_suitable` equal to `["all"]` on every row, `best_for` empty on 140, and zero
foods with sour Vipaka — one of the three classical values the generator cannot emit.

A category is not a dravya. These are.

## Two languages, on purpose

The spec is authored in Sanskrit, because that is the language the sources are written
in and because `madhura` is unambiguous where "sweet" is not. The builder emits the
English vocabulary that `diet_plan_engine` and `build_vectors` already read, through
the definitional maps below. That translation is a mapping, not a judgement — which is
the whole distinction this library exists to draw.
"""

# ------------------------------------------------------------------- rasa ---
# The six tastes. Authored per food; a food may carry one to three, dominant first.
RASA = ("madhura", "amla", "lavana", "katu", "tikta", "kashaya")

RASA_EN = {
    "madhura": "sweet", "amla": "sour", "lavana": "salty",
    "katu": "pungent", "tikta": "bitter", "kashaya": "astringent",
}

# ------------------------------------------------------------------- guna ---
# The axis the knowledge base never had. `diet_llm_generator`'s system prompt requires
# that "every meal must have an Ayurvedic rationale citing Rasa (taste), Guna
# (quality), Virya (potency), Vipaka (post-digestive effect)" — and Guna appears on
# none of the 150 foods, so the model invents it on every meal of every plan.
#
# The classical twenty are ten opposed pairs. Only the pairs that describe a food are
# admitted here; `shlakshna/khara` and `sukshma/sthula` describe substances a diet
# engine has no use for, and admitting fields nobody reads is what produced
# `season_suitable`.
GUNA_PAIRS = (
    ("guru", "laghu"),        # heavy / light to digest
    ("snigdha", "ruksha"),    # unctuous / dry
    ("tikshna", "manda"),     # sharp, penetrating / slow, dulling
    ("drava", "sandra"),      # liquid / dense
    ("picchila", "vishada"),  # slimy / clearing
    ("mridu", "kathina"),     # soft / hard
    ("sthira", "chala"),      # stable / mobile
)
GUNA = tuple(g for pair in GUNA_PAIRS for g in pair)

# `agni_effect` is DERIVED from the guru/laghu guna rather than authored, because it
# is that guna restated in the engine's own words. The generator asked a name whether
# it was heavy; the library states the quality and the mapping does the rest.
AGNI_FROM_GUNA = {"guru": "heavy", "laghu": "easy"}
AGNI_DEFAULT = "moderate"

# ------------------------------------------------------------------ virya ---
# The one derived field whose vocabulary was already right.
VIRYA = ("ushna", "shita")
VIRYA_EN = {"ushna": "heating", "shita": "cooling"}

# ----------------------------------------------------------------- vipaka ---
# Three values, not two. `seed_diet_foods.py` can only ever write madhura or katu,
# so Amla Vipaka does not occur anywhere in the current library and every sour food
# is mislabelled — tomato, curd, lemon and tamarind among them.
VIPAKA = ("madhura", "amla", "katu")
VIPAKA_EN = {"madhura": "sweet", "amla": "sour", "katu": "pungent"}

# Charaka Sutrasthana 26 / Ashtanga Hridaya Sutrasthana 9: Vipaka follows Rasa.
# Madhura and lavana yield madhura; amla yields amla; katu, tikta and kashaya yield
# katu. A row may depart from this ONLY by stating a prabhava — see `validate`.
VIPAKA_FROM_RASA = {
    "madhura": "madhura", "lavana": "madhura", "amla": "amla",
    "katu": "katu", "tikta": "katu", "kashaya": "katu",
}

# ------------------------------------------------------------------ dosha ---
# Charaka Sutrasthana 26.43. Which rasas pacify and which aggravate each dosha.
RASA_PACIFIES = {
    "vata":  {"madhura", "amla", "lavana"},
    "pitta": {"madhura", "tikta", "kashaya"},
    "kapha": {"katu", "tikta", "kashaya"},
}
RASA_AGGRAVATES = {
    "vata":  {"katu", "tikta", "kashaya"},
    "pitta": {"katu", "amla", "lavana"},
    "kapha": {"madhura", "amla", "lavana"},
}
DOSHAS = ("vata", "pitta", "kapha")

# Virya acts on the Doshas too, and outranks Rasa when they disagree — the classical
# order is Rasa, then Virya, then Vipaka, then Prabhava (Ashtanga Hridaya Sutrasthana 9).
# Ushna is Vata-hara, Kapha-hara and Pitta-vardhaka; shita is the reverse.
#
# This map was not here at first, and the validator demanded a prabhava from every
# ushna-virya food that reduced Vata — Jiraka, Maricha, Yavani, Methika. Those rows are
# not exceptions to the system; they ARE the system, one rung up. Requiring a prabhava
# for them made the rule cry wolf, and a rule that fires on ordinary rows is a rule
# authors learn to satisfy with a sentence rather than a reason.
VIRYA_DIRECTION = {
    "ushna": {"vata": -1, "pitta": +1, "kapha": -1},
    "shita": {"vata": +1, "pitta": -1, "kapha": +1},
}

# -1/0/+1 was the old range and it could not tell "mildly increases" from "is
# contraindicated". Basmati rice and green chilli were both `pitta: -1` and `+1`.
DOSHA_RANGE = (-2, -1, 0, 1, 2)

# ------------------------------------------------------------- prep state ---
# Raw and cooked apple are different dravyas; so are Ardraka and Shunthi — fresh
# ginger is snigdha with madhura vipaka, dry ginger is ruksha and tikshna, and they
# have opposite indications. `diet_foods.json` has one row per ingredient and no way
# to say which state it describes, which is why `ayurvedic_foods.json` (25 authored
# entries, which DO split them) contradicts it and both are seeded into one corpus.
PREP_STATES = ("raw", "cooked", "fresh", "dry", "roasted", "fermented",
               "sprouted", "soaked", "ripe", "unripe", "prepared")

# -------------------------------------------------------------------- ritu ---
# The six seasons, named as `engine/seasonal.py` and `panchakarma_engine` name them,
# so a food's Ritucharya claim and a Panchakarma plan's season are the same word.
RITU = ("shishira", "vasanta", "grishma", "varsha", "sharad", "hemanta")
# An explicit constant, never a default. `season_suitable: ["all"]` on all 150 rows
# is what a field looks like when nobody ever decided; ALL_RITU is a decision.
ALL_RITU = RITU

# -------------------------------------------------------------- provenance ---
# Nutrition currently has no provenance and 109 of 150 rows are a per-category
# placeholder: 27 vegetables share one macro block, and coconut is recorded at
# 50 kcal / 0.2 g fat against roughly 354 kcal / 33 g fat. The engine sums these into
# the macro bar the user reads, so a row without a source is not admissible.
NUTRITION_SOURCES = ("ifct2017", "usda", "authored_estimate")

# The nighantu a claim is drawn from, so a reviewer can check one food at a time
# rather than accepting or rejecting the file.
#
# `modern_extrapolated` is not a text and is not a hedge. Roughly a fifth of the 150
# foods this library replaces have no classical entry at all — quinoa, oats, broccoli,
# kiwi, tofu, tempeh, soy milk, nutritional yeast, olive oil. The old generator gave
# them a rasa and a virya from their category exactly as confidently as it gave
# Shunthi one, and nothing in the row recorded the difference. A row using this value
# must put the basis of the extrapolation in `varga` — the dravya it is reasoned from
# and why — so a Vaidya reviewing the library can see at a glance which claims are
# cited and which are argued.
NIGHANTU = ("bhavaprakasha", "dhanvantari", "raja", "kaiyadeva",
            "charaka", "sushruta", "ashtanga_hridaya", "modern_extrapolated")


class SpecError(ValueError):
    """A library row that cannot be admitted. Raised at build time, never at runtime."""


def validate(food: dict) -> None:
    """Reject a row that is malformed, or that contradicts classical rule silently.

    The second half is the point. A rule engine may not decide that a sweet food
    reduces Kapha — but barley does, and honey does, and the texts say so under
    Prabhava, the specific action that overrides the rasa-virya logic. So the rule is
    not "never contradict"; it is **contradict only out loud**. A row whose dosha
    effect or vipaka departs from its own rasa must state the prabhava that licenses
    it, and that statement is a sentence a Vaidya can reject.

    This is the check the old generator could not have: it had no place to write down
    why barley is Kapha-reducing, so it hardcoded barley into a list and the reason
    lived nowhere.
    """
    fid = food.get("id") or "<unnamed>"

    def bad(msg):
        raise SpecError(f"{fid}: {msg}")

    rasa = tuple(food.get("rasa") or ())
    if not 1 <= len(rasa) <= 3:
        bad(f"needs 1-3 rasa, got {list(rasa)}")
    for r in rasa:
        if r not in RASA:
            bad(f"unknown rasa {r!r} — expected one of {RASA}")
    if len(set(rasa)) != len(rasa):
        bad(f"repeated rasa in {list(rasa)}")

    guna = tuple(food.get("guna") or ())
    if not guna:
        bad("needs at least one guna — the axis the prompt requires citing")
    for g in guna:
        if g not in GUNA:
            bad(f"unknown guna {g!r}")
    for a, b in GUNA_PAIRS:
        if a in guna and b in guna:
            bad(f"carries both halves of an opposed pair ({a}/{b})")

    if food.get("virya") not in VIRYA:
        bad(f"virya must be one of {VIRYA}, got {food.get('virya')!r}")
    if food.get("vipaka") not in VIPAKA:
        bad(f"vipaka must be one of {VIPAKA}, got {food.get('vipaka')!r}")

    prabhava = (food.get("prabhava") or "").strip()

    implied = {VIPAKA_FROM_RASA[r] for r in rasa}
    if food["vipaka"] not in implied and not prabhava:
        bad(f"vipaka {food['vipaka']!r} does not follow rasa {list(rasa)} "
            f"(classically {sorted(implied)}) and no prabhava explains it")

    effect = food.get("dosha_effect") or {}
    if set(effect) != set(DOSHAS):
        bad(f"dosha_effect must name exactly {DOSHAS}, got {sorted(effect)}")
    for d, v in effect.items():
        if v not in DOSHA_RANGE:
            bad(f"dosha_effect[{d}] = {v!r}, expected one of {DOSHA_RANGE}")
        against_rasa = (
            (v < 0 and set(rasa) <= RASA_AGGRAVATES[d]) or
            (v > 0 and set(rasa) <= RASA_PACIFIES[d])
        )
        # Virya licenses what rasa alone would forbid. Only an effect that runs against
        # BOTH needs a prabhava — that is the one place a claim has left the classical
        # system entirely, and the one place a reviewer needs a sentence to argue with.
        with_virya = VIRYA_DIRECTION[food["virya"]][d] * v > 0
        if against_rasa and not with_virya and not prabhava:
            bad(f"{d} {v:+d} runs against rasa {list(rasa)} and against {food['virya']} "
                f"virya, and no prabhava explains it")

    prep = food.get("prep_state")
    if prep not in PREP_STATES:
        bad(f"prep_state must be one of {PREP_STATES}, got {prep!r}")

    ritu = tuple(food.get("ritu") or ())
    if not ritu:
        bad("needs at least one ritu — `season_suitable: ['all']` on every row is "
            "what this field looked like when nobody decided; pass ALL_RITU to mean it")
    for r in ritu:
        if r not in RITU:
            bad(f"unknown ritu {r!r}")

    nut = food.get("nutrition") or {}
    if nut.get("source") not in NUTRITION_SOURCES:
        bad(f"nutrition needs a source from {NUTRITION_SOURCES}, got {nut.get('source')!r}")
    for key in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g"):
        if not isinstance(nut.get(key), (int, float)):
            bad(f"nutrition.{key} missing or not a number")

    ref = food.get("nighantu_ref") or {}
    if ref.get("text") not in NIGHANTU:
        bad(f"nighantu_ref.text must be one of {NIGHANTU}, got {ref.get('text')!r}")
    varga = (ref.get("varga") or "").strip()
    if not varga:
        bad("nighantu_ref needs a varga so a reviewer can find the entry")
    # An extrapolation has to show its reasoning, or it is a citation-shaped guess —
    # which is what the generator produced for every modern food.
    if ref["text"] == "modern_extrapolated" and len(varga) < 25:
        bad("modern_extrapolated needs the basis of the extrapolation in `varga` "
            f"(the dravya it is reasoned from, and why) — got {varga!r}")

    if food.get("reviewed") is not False:
        bad("reviewed must be False — nothing here has been seen by a Vaidya")


def to_kb_row(food: dict) -> dict:
    """One authored food, in the shape `diet_plan_engine` and `build_vectors` read.

    Sanskrit in, English out. Every value below is either copied or passed through a
    definitional map; nothing is inferred, which is the difference between this and
    the function it replaces.
    """
    guna = tuple(food["guna"])
    agni = next((AGNI_FROM_GUNA[g] for g in guna if g in AGNI_FROM_GUNA), AGNI_DEFAULT)

    return {
        "id": food["id"],
        "name": food["name"],
        "category": food["category"],
        "prep_state": food["prep_state"],
        "dietary_type": list(food["dietary_type"]),
        "nutrition_per_100g": {
            k: food["nutrition"][k]
            for k in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")
        },
        "nutrition_source": food["nutrition"]["source"],
        "ayurvedic": {
            "rasa": [RASA_EN[r] for r in food["rasa"]],
            "rasa_sanskrit": list(food["rasa"]),
            "guna": list(guna),
            "virya": VIRYA_EN[food["virya"]],
            "virya_sanskrit": food["virya"],
            "vipaka": VIPAKA_EN[food["vipaka"]],
            "vipaka_sanskrit": food["vipaka"],
            "prabhava": food.get("prabhava") or "",
            "dosha_effect": dict(food["dosha_effect"]),
            "agni_effect": agni,
            "best_for": list(food.get("pathya_for") or ()),
        },
        "pathya_for": list(food.get("pathya_for") or ()),
        "apathya_for": list(food.get("apathya_for") or ()),
        "viruddha_with": list(food.get("viruddha_with") or ()),
        "meal_suitable": list(food["meal_suitable"]),
        "prep_time_minutes": food["prep_time_minutes"],
        "season_suitable": list(food["ritu"]),
        "vegan": food["vegan"],
        "common_allergen": food["common_allergen"],
        "nighantu_ref": dict(food["nighantu_ref"]),
        "reviewed": False,
    }
