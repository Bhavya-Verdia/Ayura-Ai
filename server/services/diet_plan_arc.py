"""
Which four-week therapeutic progression this patient's plan should follow.

The arc used to be four literals in the prompt — Ama Pachana, Agni Deepana, Brimhana,
Rasayana — for every patient who has ever generated a plan. The app computed
`ama_indicator`, `ojas_level`, `bmi_category` and `agni_type` first and then handed
the model a sequence that took account of none of them, which is the wrong way round:
Charaka Sutrasthana 22 makes the choice between **Langhana** (reducing, Apatarpana)
and **Brimhana** (nourishing, Santarpana) the first decision in treatment, taken from
the patient's Bala and the state of their Dosha and Ama.

Two ways the fixed sequence was actually wrong rather than merely unpersonalised:

* **Week 3 prescribed Santarpana to Santarpana-caused disease.** Charaka Sutrasthana
  23 (Santarpaniya) names Prameha, Medoroga and Kushtha as the diseases of
  over-nourishment. A Kapha-dominant, obese, diabetic patient was given a nourishing
  week with ghee, nuts and root vegetables halfway through their plan.
* **Week 1 prescribed Langhana to the depleted.** A 52 kg underweight patient with low
  Ojas and no Ama was given a week of light, clearing food. The model noticed and
  wrote the contradiction into the plan itself: *"Although Ama is reported as absent,
  this first week keeps meals light..."*.

The model often compensated, which is why this reads as a design defect rather than a
stream of incident reports — but a plan that is right because the model overrode the
instructions is not a plan the instructions can be trusted to produce.

`Rasayana` carries its own rule and it is the one most often broken in practice:
Rasayana on an Ama-laden Srotas feeds the Ama rather than the Dhatu, so a final
rejuvenation week is only scheduled when the weeks before it have had time to clear
what was there at the start.
"""
from __future__ import annotations

# Diseases of over-nourishment (Charaka Sutrasthana 23, Santarpaniya). A nourishing
# phase is contraindicated in these regardless of what the patient's goal says.
_SANTARPANA_JANYA = frozenset({
    "obesity", "diabetes", "fatty_liver", "high_cholesterol", "pcos", "hypothyroid",
})
# Only two of those are named in Sutrasthana 23. The others are placed with them as
# a modern extrapolation (a Kapha-Meda, Dhatvagni-mandya picture), and the withheld
# note says so rather than citing a chapter that does not describe them: the live
# sweep found a hypothyroid patient told Brimhana was withheld for Prameha,
# Medoroga and Kushtha, three diseases they did not have.
_CLASSICAL_NAME = {"diabetes": "Prameha", "obesity": "Sthaulya (Medoroga)"}

# A sharp or Pitta-provoked Agni. Deepana with warming spices is the remedy for a
# dull Agni and the cause of Amlapitta, and every arc used to open with it whatever
# the Agni: a Tikshna patient with acid reflux was told to kindle with warming
# spices in week 1. For these patients the phase becomes Agni Samana (regulating),
# and Pachana works through bitter, non-heating herbs.
_PITTA_PROVOKED = frozenset({"acidity", "peptic_ulcer", "ulcer"})

# States where a reducing phase is contraindicated regardless of Ama, because the
# patient has no Bala to spend on it.
_DEPLETED_BMI = frozenset({"underweight"})
_DEPLETED_OJAS = frozenset({"low", "very_low", "depleted"})

_HIGH_AMA = frozenset({"high", "severe", "moderate"})


def _phase(number: int, name: str, focus: str, rationale: str) -> dict:
    return {
        "week_number": number,
        "phase": name,
        "focus": focus,
        "rationale": rationale,
    }


# ── Plan over plan ───────────────────────────────────────────────────────────
# The arc is chosen from the patient's state, and every plan used to begin it
# again: a balanced patient kindled Agni at the start of every month, a reducing
# patient spent every fourth week on the opening kindling and never more than two on
# Langhana itself. When the last plan was finished and followed and the state still
# calls for the same line of treatment, the next one continues it instead — the
# opening phase is done. What it never skips is clearing: an arc that opens with Ama
# Pachana is only chosen while the assessment still shows Ama, and Ama that is still
# there has not been cleared, however well the last plan was followed.
_CONTINUED = {
    "Samatva (balance-led)": [
        ("Sthairya", "Steadying — the meals that suited you, matched to the Dosha and season",
         "Agni was kindled last plan; this one starts from the steady pattern."),
        ("Brimhana", "Moderately nourishing — good fats, whole grains, seasonal produce",
         "Build Dhatu at a pace a balanced Agni can carry."),
        ("Rasayana", "Rejuvenation — amla, seasonal Rasayana, maintenance",
         "Rasayana suits a clear Srotas and a steady Agni."),
        ("Sthairya", "Holding — the pattern as ordinary food, seasonally adjusted",
         "A balanced patient's plan is maintenance; it should become habit."),
    ],
    "Langhana-pradhana (reduction-led)": [
        ("Langhana", "Reducing — lighter meals, barley and millets over wheat and rice, no late eating",
         "Agni was kindled last plan, so reduction starts in the first week."),
        ("Rukshana", "Drying — astringent and bitter tastes, minimal oil",
         "Rukshana addresses the Snigdha, Kapha-Meda quality these conditions share."),
        ("Langhana", "Reducing, continued — the lighter pattern held",
         "Meda comes down over months, not weeks; the reduction is sustained."),
        ("Sthairya", "Holding — a sustainable version of the reducing weeks",
         "Consolidate rather than rebound."),
    ],
    "Brimhana-pradhana (nourishment-led)": [
        ("Brimhana", "Nourishing — ghee, nuts, root vegetables, whole grains, dairy",
         "Agni was steadied last plan, so nourishment starts in the first week."),
        ("Balya", "Strength-building — protein-dense meals, dates, milk",
         "Convert the nourishment into Bala rather than only weight."),
        ("Rasayana", "Rejuvenation — amla, ghee, seasonal Rasayana preparations",
         "Rasayana lands on a clear Srotas."),
        ("Sthairya", "Holding — the nourishing pattern kept as ordinary food",
         "Consolidate the gain."),
    ],
}


def _continue(arc: dict, user_profile: dict) -> dict:
    prev = (user_profile.get("diet_log") or {}).get("continues")
    if not prev:
        return arc
    n = int(prev.get("plan_number") or 2)
    arc = {**arc, "plan_number": n}
    same_line = prev.get("arc") == arc["arc"]
    if not same_line:
        arc["continuation"] = "new_line"
        if prev.get("arc"):
            arc["basis"] += (f" Plan {n}: your last plan followed {prev['arc']}; your state now "
                             f"calls for this line instead, so it starts from its first week.")
        return arc
    if not prev.get("followed"):
        arc["continuation"] = "repeated"
        arc["basis"] += (f" Plan {n}: the last plan was not followed long enough to build on "
                         f"({prev.get('meals_logged', 0)} meals logged), so this one starts the "
                         "same progression again.")
        return arc
    weeks = _CONTINUED.get(arc["arc"])
    if not weeks:
        arc["continuation"] = "held"
        arc["basis"] += (f" Plan {n}: the same progression again, deliberately — "
                         + ("Ama is still present on your latest assessment, and Ama that is "
                            "still there has not been cleared."
                            if arc["weeks"][0]["phase"] in ("Ama Pachana", "Deepana-Pachana")
                            else "it is held for as long as the state that chose it lasts."))
        return arc
    arc["continuation"] = "continued"
    arc["weeks"] = [_phase(i + 1, *w) for i, w in enumerate(weeks)]
    arc["basis"] += (f" Plan {n}: you finished and followed the last plan, so this one "
                     "continues it rather than starting the opening week again.")
    return arc


def choose_arc(user_profile: dict, diet_prefs: dict) -> dict:
    """The four-week progression for this patient, continued from the last plan when
    that one was finished and followed (`_continue`)."""
    arc = _continue(_choose_arc(user_profile, diet_prefs), user_profile)
    return _pitta_safe(arc, user_profile, diet_prefs)


def _brimhana_withheld(diseases: set[str], heavy_build: bool) -> str:
    """Why no nourishing week, citing only what this patient has."""
    classical = sorted(_CLASSICAL_NAME[d] for d in diseases if d in _CLASSICAL_NAME)
    if heavy_build and "obesity" not in diseases:
        classical.append(_CLASSICAL_NAME["obesity"])
    modern = sorted(d.replace("_", " ") for d in diseases if d not in _CLASSICAL_NAME)
    note = ("Brimhana — the fixed progression put a nourishing week with ghee, nuts and "
            "root vegetables at week 3.")
    if classical:
        note += (f" Charaka Sutrasthana 23 names {' and '.join(classical)} among the diseases "
                 "of over-nourishment; adding Santarpana to them is the cause, not the treatment.")
    if modern:
        verb = "is" if len(modern) == 1 else "are"
        note += (f" {', '.join(modern).capitalize()} {verb} treated the same way as a modern "
                 "extrapolation (a Kapha-Meda, Dhatvagni-mandya picture), not a classical "
                 "citation.")
    return note


_SAMANA = (
    "Agni Samana",
    "Regulating a sharp Agni — meals on time and never skipped; sweet, bitter and astringent "
    "tastes; coriander, fennel and cumin rather than chilli, garlic, mustard or pepper; nothing "
    "sour or fermented",
)
_TIKTA_PACHANA = (
    "Light, warm, freshly cooked; Pachana through bitter, non-heating herbs — coriander, "
    "fennel, cumin, Guduchi — not ginger, pepper or hing; no sour or fermented food"
)


def _pitta_safe(arc: dict, user_profile: dict, diet_prefs: dict) -> dict:
    """Replace heating Deepana with Agni Samana for a sharp or Pitta-provoked Agni."""
    from services.diet_brief_builder import diet_conditions
    agni = str(user_profile.get("agni_type") or "").lower()
    provoked = sorted(set(diet_conditions(user_profile, diet_prefs)) & _PITTA_PROVOKED)
    if agni != "tikshna" and not provoked:
        return arc
    why = " and ".join(([("Agni is Tikshna (sharp)")] if agni == "tikshna" else [])
                       + ([f"{', '.join(provoked)} is a Pitta disease"] if provoked else []))
    changed = False
    weeks = []
    for w in arc["weeks"]:
        w = dict(w)
        if w["phase"] == "Agni Deepana":
            w["phase"], w["focus"] = _SAMANA
            w["rationale"] = (f"{why}; kindling it with heating spices would feed the Pitta that "
                              "is the problem, so this week steadies Agni instead.")
            changed = True
        elif w["phase"] in ("Ama Pachana", "Deepana-Pachana"):
            w["focus"] = _TIKTA_PACHANA
            changed = True
        elif w["phase"] == "Snehana-Deepana":
            w["focus"] = "Unctuous and cooling — ghee, milk, soft grains; mild spices only"
            changed = True
        weeks.append(w)
    if not changed:
        return arc
    return {**arc, "weeks": weeks, "withheld": [*arc["withheld"], (
        f"Heating Deepana (ginger, pepper, chilli, hing) — {why}, and warming spices "
        "aggravate Pitta; Agni is regulated with bitter and cooling herbs instead.")]}


def _choose_arc(user_profile: dict, diet_prefs: dict) -> dict:
    """The four-week progression for this patient, and why it is this one.

    Returns {"arc": str, "basis": str, "weeks": [ {week_number, phase, focus,
    rationale} x4 ], "withheld": [str]}. `withheld` names a phase that the fixed
    sequence would have included and this patient must not be given, so the reason
    survives into the plan rather than being silently absent.
    """
    ama = str(user_profile.get("ama_indicator") or "none").lower()
    ojas = str(user_profile.get("ojas_level") or "moderate").lower()
    bmi = str(user_profile.get("bmi_category") or "normal").lower()
    agni = str(user_profile.get("agni_type") or "sama").lower()
    age = int(user_profile.get("age") or 30)
    pregnant = bool(user_profile.get("pregnancy_or_nursing"))
    # Both places a disease is declared, via the one helper the whole diet path uses.
    # None of the four `gut_health_issue` values is Santarpana-caused, so this changes
    # no arc today; it is here so that the arc cannot be the one module still reading
    # half the patient's conditions if that vocabulary grows.
    from services.diet_brief_builder import diet_conditions
    conditions = set(diet_conditions(user_profile, diet_prefs))

    heavy_ama = ama in _HIGH_AMA
    heavy_build = bmi in ("overweight", "obese")

    # Low Ojas is not by itself a reason to nourish. Ojas Kshaya is ordinary in
    # Medoroga — the Srotas are obstructed, not empty — and reading it as depletion
    # sent an obese diabetic down the Brimhana arc, which is the error this module
    # exists to prevent. The depletion signals that survive a heavy build are the
    # ones about the body itself, and none of them can coexist with it.
    depleted = (
        bmi in _DEPLETED_BMI
        or str(user_profile.get("bala") or "").lower() in {"low", "avara", "heena"}
        or (not heavy_build and (ojas in _DEPLETED_OJAS or age >= 75))
    )
    santarpana_janya = bool(conditions & _SANTARPANA_JANYA) or heavy_build
    withheld: list[str] = []

    # ── Pregnancy and nursing ────────────────────────────────────────────────
    # Garbhini Paricharya is nourishing throughout. Langhana and Rukshana are
    # contraindicated for the whole period, and no goal the patient states changes
    # that, so this branch is taken before any of the others.
    if pregnant:
        withheld.append(
            "Langhana (reducing) — contraindicated throughout pregnancy and nursing "
            "under Garbhini Paricharya, whatever the stated goal."
        )
        return {
            "arc": "Garbhini Paricharya",
            "basis": (
                "Pregnancy or nursing. The progression is nourishing from the first "
                "week; no reducing or drying phase is scheduled at any point."
            ),
            "withheld": withheld,
            "weeks": [
                _phase(1, "Madhura-Snigdha Sthapana",
                       "Sweet, unctuous, easily digestible food establishing steady Agni",
                       "Settle digestion on Satvic, warm, freshly cooked meals."),
                _phase(2, "Brimhana",
                       "Nourishing — milk, ghee, sweet fruits, whole grains",
                       "Build Rasa and Rakta to support the growing Garbha."),
                _phase(3, "Ojas Vardhana",
                       "Ojas-building — dates, almonds, saffron milk, ghee",
                       "Support Ojas, which Garbhini Paricharya treats as the priority."),
                _phase(4, "Sthairya",
                       "Steady maintenance of the nourishing pattern",
                       "Hold the pattern rather than introducing anything new."),
            ],
        }

    # ── Depleted: Brimhana-led, no reducing week at all ──────────────────────
    # Langhana requires Bala to spend. `diet_goal` has no weight-gain value, so a
    # patient who needs this arc cannot ask for it; it is read off the body.
    if depleted and not heavy_ama:
        withheld.append(
            "Ama Pachana (Langhana) — the fixed progression opened with a clearing "
            "week. With no Ama present and Bala already low, that week would reduce "
            "a patient who has nothing to spare."
        )
        return {
            "arc": "Brimhana-pradhana (nourishment-led)",
            "basis": (
                f"Ama {ama}, Ojas {ojas}, build {bmi}. Charaka Sutrasthana 22 gives "
                "Brimhana for the depleted; there is nothing here for a reducing phase "
                "to remove."
                + (
                    " The nourishment must still respect "
                    + ", ".join(sorted(conditions & _SANTARPANA_JANYA))
                    + ": depletion decides the direction, the disease decides the foods."
                    if conditions & _SANTARPANA_JANYA else ""
                )
            ),
            "withheld": withheld,
            "weeks": [
                _phase(1, "Snehana-Deepana",
                       "Unctuous and warming — ghee, warm milk, soft grains, gentle spices",
                       "Steady a variable Agni without reducing an already-light patient."),
                _phase(2, "Brimhana",
                       "Nourishing — ghee, nuts, root vegetables, whole grains, dairy",
                       "Rebuild Rasa and Mamsa dhatu now that Agni carries more."),
                _phase(3, "Balya",
                       "Strength-building — protein-dense meals, Ashwagandha milk, dates",
                       "Convert the nourishment into Bala rather than only weight."),
                _phase(4, "Rasayana",
                       "Rejuvenation — amla, ghee, seasonal Rasayana preparations",
                       "Rasayana lands on a clear Srotas, which is the condition for it."),
            ],
        }

    # ── Santarpana-caused disease: Langhana-led, no nourishing week ──────────
    if santarpana_janya and not depleted:
        withheld.append(_brimhana_withheld(conditions & _SANTARPANA_JANYA, heavy_build))
        first = (
            _phase(1, "Ama Pachana",
                   "Deepaniya-Pachana — light, warm, spiced; no heavy, sour or fermented food",
                   f"Ama is {ama}. Nothing else can work while it is present.")
            if heavy_ama else
            _phase(1, "Agni Deepana",
                   "Kindling — warming spices, regular timing, nothing heavy",
                   "No significant Ama, so the first week goes straight to Agni.")
        )
        return {
            "arc": "Langhana-pradhana (reduction-led)",
            "basis": (
                f"Ama {ama}, build {bmi}"
                + (f", {', '.join(sorted(conditions & _SANTARPANA_JANYA))}"
                   if conditions & _SANTARPANA_JANYA else "")
                + ". Apatarpana is the line of treatment; no Santarpana phase is scheduled."
            ),
            "withheld": withheld,
            "weeks": [
                first,
                _phase(2, "Langhana",
                       "Reducing — lighter meals, barley and millets over wheat and rice, no late eating",
                       "Reduce Meda and Kapha while Agni is now able to carry it."),
                _phase(3, "Rukshana",
                       "Drying — astringent and bitter tastes, minimal oil, honey over sugar",
                       "Rukshana addresses the Snigdha, Kapha-Meda quality these conditions share."),
                _phase(4, "Sthairya",
                       "Holding — a sustainable version of weeks 2-3, seasonally adjusted",
                       "Consolidate rather than rebound; this is the week the plan has to outlive."),
            ],
        }

    # ── Depleted and Ama-laden at once ──────────────────────────────────────
    # The Ama still has to go, but Langhana spends Bala this patient does not have.
    # The classical answer is Deepana-Pachana — kindle the fire to burn the Ama —
    # rather than Apatarpana, which reduces the patient along with it. Without this
    # branch a frail patient with Ama fell through to the ordinary clearing arc and
    # was given the same reducing week as someone twice their strength.
    if depleted and heavy_ama:
        withheld.append(
            "Langhana (fasting-type reduction) — Ama is present and must be addressed, "
            "but with Bala this low it is cleared by kindling Agni, not by reducing "
            "the patient."
        )
        withheld.append(
            "Rasayana — Ama was high at the start of this plan, and Rasayana on an "
            "Ama-laden Srotas feeds the Ama rather than the Dhatu. It belongs in the "
            "next plan, once digestion has held."
        )
        return {
            "arc": "Deepana-pradhana (gentle clearing)",
            "basis": (
                f"Ama {ama} with Ojas {ojas} and build {bmi}. Ama has to be addressed "
                "and there is no Bala to spend on reducing, so the Ama is burned by "
                "kindling Agni rather than by withdrawing food."
            ),
            "withheld": withheld,
            "weeks": [
                _phase(1, "Deepana-Pachana",
                       "Warm, light, well-spiced but not scanty — thin khichdi, ginger, "
                       "ajwain, hing; small portions eaten to appetite",
                       "Kindle Agni so it consumes the Ama. This is not a fasting week."),
                _phase(2, "Agni Deepana",
                       "Kindling continues — warming spices, regular timing, gradually more substance",
                       "Let Agni carry more before anything heavy is offered."),
                _phase(3, "Snehana-Brimhana",
                       "Unctuous and nourishing — ghee, warm milk, soft grains",
                       "Begin rebuilding, now that Agni can digest what is given."),
                _phase(4, "Balya",
                       "Strength-building — protein-dense but easily digestible meals",
                       "Consolidate strength rather than closing on Rasayana, which Ama "
                       "at the start of this plan rules out."),
            ],
        }

    # ── Ama present with Bala intact: clear, kindle, then nourish carefully ──
    if heavy_ama:
        return {
            "arc": "Ama Pachana to Rasayana",
            "basis": (
                f"Ama {ama} with Bala intact. Clearing comes first, and Rasayana is "
                "scheduled only at the end, once the weeks before it have had time to "
                "clear the Srotas — Rasayana on Ama feeds the Ama."
            ),
            "withheld": withheld,
            "weeks": [
                _phase(1, "Ama Pachana",
                       "Deepaniya-Pachana — light, warm, spiced; no heavy, sour or fermented food",
                       f"Ama is {ama}. Nothing else can work while it is present."),
                _phase(2, "Agni Deepana",
                       "Kindling — warming spices, gradually richer meals",
                       "Agni carries more now that the load on it has come down."),
                _phase(3, "Brimhana",
                       "Nourishing — ghee, nuts, root vegetables where they suit the Dosha",
                       "Rebuild what the clearing weeks spent, now that Agni can digest it."),
                _phase(4, "Rasayana",
                       "Rejuvenation — amla, Rasayana preparations, seasonal maintenance",
                       "The Srotas is clear, which is the classical condition for Rasayana."),
            ],
        }

    # ── Nothing urgent in either direction ──────────────────────────────────
    return {
        "arc": "Samatva (balance-led)",
        "basis": (
            f"Ama {ama}, Ojas {ojas}, build {bmi}, Agni {agni}. No depletion and no "
            "excess to correct, so the progression steadies Agni and then maintains."
        ),
        "withheld": withheld,
        "weeks": [
            _phase(1, "Agni Deepana",
                   "Kindling — regular timing, warming spices, nothing heavy",
                   "Agni first; every later week depends on it."),
            _phase(2, "Sthairya",
                   "Steadying — consistent meals matched to the Dosha and the season",
                   "Hold the pattern long enough for it to become ordinary."),
            _phase(3, "Brimhana",
                   "Moderately nourishing — good fats, whole grains, seasonal produce",
                   "Build Dhatu at a pace a balanced Agni can carry."),
            _phase(4, "Rasayana",
                   "Rejuvenation — amla, seasonal Rasayana, maintenance",
                   "Close on Rasayana, appropriate here because there is no Ama to feed."),
        ],
    }


def arc_prompt_block(arc: dict) -> str:
    """The progression, written for the prompt in place of the four fixed literals."""
    lines = [
        f"THERAPEUTIC PROGRESSION — {arc['arc']}",
        f"  Chosen for this patient: {arc['basis']}",
        "  Follow this sequence exactly. The phase names below are the ones to return.",
    ]
    for week in arc["weeks"]:
        lines.append(
            f"    Week {week['week_number']} ({week['phase']}): {week['focus']}. "
            f"{week['rationale']}"
        )
    for note in arc["withheld"]:
        lines.append(f"  Deliberately NOT in this plan: {note}")
    return "\n".join(lines)
