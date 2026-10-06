"""Generate the diet reviewer pack: people across every age, size and disease, their
plans exactly as the app builds them.

A dietitian reads this. Each plan is the real `build_diet_plan` output — LLM
primary, rule engine fallback, the same safety and energy layers — with no
database. Read the plans whole: the defects that matter are a meal that
contradicts the plan's own note, which no grep finds.

    python scripts/diet_reviewer_pack.py generate        # all personas (live LLM calls)
    python scripts/diet_reviewer_pack.py generate 3 7    # only those
    python scripts/diet_reviewer_pack.py audit           # numbers per plan, from the JSON
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path(__file__).resolve().parent / "diet_reviewer_pack"

_BASE = dict(agni_type="sama", ama_indicator="none", ojas_level="moderate",
             current_season="sharad", medical_history=[], allergies=[])


def P(**kw):
    return {**_BASE, **kw}


# (title, profile, diet prefs). Every field is one onboarding or the diet form records.
PERSONAS = [
    ("12-year-old girl, healthy, school day",
     P(age=12, gender="female", height_cm=150, weight_kg=40, bmi_category="normal",
       activity_level="moderate", dominant_dosha="vata"),
     dict(diet_goal="general_wellness", dietary_type="vegetarian")),
    ("16-year-old boy, underweight, wants muscle",
     P(age=16, gender="male", height_cm=176, weight_kg=52, bmi_category="underweight",
       activity_level="active", dominant_dosha="vata", agni_type="vishama"),
     dict(diet_goal="muscle_support", dietary_type="vegetarian")),
    ("24-year-old with PCOS, overweight, vegan, losing weight",
     P(age=24, gender="female", height_cm=158, weight_kg=78, bmi_category="obese",
       activity_level="light", dominant_dosha="kapha", medical_history=["pcos"],
       ama_indicator="moderate"),
     dict(diet_goal="weight_loss", dietary_type="vegan")),
    ("29-year-old, pregnant (2nd trimester), anaemic",
     P(age=29, gender="female", height_cm=160, weight_kg=62, bmi_category="normal",
       activity_level="light", dominant_dosha="pitta", medical_history=["anemia"],
       pregnancy_or_nursing=True, pregnancy_status="pregnant", pregnancy_trimester=2),
     dict(diet_goal="general_wellness", dietary_type="vegetarian")),
    ("34-year-old with type 2 diabetes and obesity, sedentary",
     P(age=34, gender="male", height_cm=172, weight_kg=104, bmi_category="obese",
       activity_level="sedentary", dominant_dosha="kapha", agni_type="manda",
       medical_history=["diabetes_type2", "obesity"], ama_indicator="high"),
     dict(diet_goal="weight_loss", dietary_type="vegetarian")),
    ("45-year-old with hypothyroidism and hypertension, dairy allergy",
     P(age=45, gender="female", height_cm=162, weight_kg=74, bmi_category="overweight",
       activity_level="light", dominant_dosha="kapha",
       medical_history=["hypothyroidism", "hypertension"], allergies=["dairy"]),
     dict(diet_goal="weight_loss", dietary_type="vegetarian", food_allergies=["dairy"])),
    ("52-year-old with chronic kidney disease, diabetes and hypertension",
     P(age=52, gender="male", height_cm=170, weight_kg=76, bmi_category="overweight",
       activity_level="light", dominant_dosha="kapha",
       medical_history=["kidney_disease", "diabetes_type2", "hypertension"]),
     dict(diet_goal="general_wellness", dietary_type="vegetarian")),
    ("58-year-old with heart disease, high cholesterol and gout",
     P(age=58, gender="male", height_cm=175, weight_kg=86, bmi_category="overweight",
       activity_level="sedentary", dominant_dosha="pitta",
       medical_history=["heart_disease", "high_cholesterol", "gout"]),
     dict(diet_goal="general_wellness", dietary_type="vegetarian")),
    ("66-year-old with osteoporosis and IBS, lactose intolerant",
     P(age=66, gender="female", height_cm=155, weight_kg=54, bmi_category="normal",
       activity_level="light", dominant_dosha="vata", agni_type="vishama",
       medical_history=["osteoporosis"]),
     dict(diet_goal="gut_health", dietary_type="vegetarian", food_intolerances=["lactose"],
          gut_health_issue="ibs")),
    ("78-year-old man, underweight, poor appetite, constipated",
     P(age=78, gender="male", height_cm=168, weight_kg=50, bmi_category="underweight",
       activity_level="sedentary", dominant_dosha="vata", agni_type="manda",
       ojas_level="low", bala="low"),
     dict(diet_goal="general_wellness", dietary_type="vegetarian",
          gut_health_issue="constipation")),
    ("38-year-old with coeliac disease and acidity",
     P(age=38, gender="female", height_cm=165, weight_kg=58, bmi_category="normal",
       activity_level="moderate", dominant_dosha="pitta", agni_type="tikshna",
       medical_history=["celiac"], allergies=["gluten"]),
     dict(diet_goal="gut_health", dietary_type="vegetarian", food_allergies=["gluten"],
          gut_health_issue="acidity")),
    ("30-year-old athlete, very active, vegan, peanut allergy",
     P(age=30, gender="male", height_cm=182, weight_kg=80, bmi_category="normal",
       activity_level="very_active", dominant_dosha="pitta", agni_type="tikshna"),
     dict(diet_goal="muscle_support", dietary_type="vegan", food_allergies=["peanuts"])),
    ("31-year-old, breastfeeding a 3-month-old",
     P(age=31, gender="female", height_cm=163, weight_kg=64, bmi_category="normal",
       activity_level="light", dominant_dosha="vata",
       pregnancy_or_nursing=True, pregnancy_status="nursing"),
     dict(diet_goal="general_wellness", dietary_type="vegetarian")),
    ("27-year-old with Crohn's disease, sex not given",
     P(age=27, gender="other", height_cm=168, weight_kg=55, bmi_category="normal",
       activity_level="moderate", dominant_dosha="pitta", medical_history=["crohns disease"]),
     dict(diet_goal="gut_health", dietary_type="vegetarian")),
    ("19-year-old, underweight, asks to lose weight",
     P(age=19, gender="female", height_cm=165, weight_kg=46, bmi_category="underweight",
       activity_level="moderate", dominant_dosha="vata"),
     dict(diet_goal="weight_loss", dietary_type="vegetarian")),
    ("62-year-old with type 2 diabetes on warfarin, fasting Mondays",
     P(age=62, gender="male", height_cm=170, weight_kg=72, bmi_category="normal",
       activity_level="light", dominant_dosha="pitta",
       medical_history=["diabetes_type2", "heart_disease"], current_medications=["warfarin", "metformin"]),
     dict(diet_goal="general_wellness", dietary_type="vegetarian", fasting_days=["Monday"])),
]


async def _one(i: int):
    from services.diet_llm_generator import build_diet_plan

    title, profile, prefs = PERSONAS[i - 1]
    profile = {"id": f"pack{i}", "name": f"Persona {i}", **profile}
    t0 = time.time()
    plan = await build_diet_plan(profile, dict(prefs))
    OUT.mkdir(exist_ok=True)
    (OUT / f"plan_{i:02d}.json").write_text(json.dumps(
        {"n": i, "title": title, "profile": profile, "prefs": prefs, "plan": plan,
         "seconds": round(time.time() - t0)}, indent=1, default=str))
    print(f"  {i:2d} {plan.get('generation_method', 'rule_engine'):>12} "
          f"{round(time.time() - t0):>4}s  {title}")


async def generate(which):
    from database.chromadb_client import init_chromadb
    try:
        init_chromadb()
    except Exception as e:  # noqa: BLE001 — retrieval degrades, it does not block the pack
        print(f"  (ChromaDB unavailable: {e})")
    sem = asyncio.Semaphore(4)

    async def run(i):
        async with sem:
            try:
                await _one(i)
            except Exception as e:  # noqa: BLE001
                print(f"  {i:2d} FAILED: {e}")
    await asyncio.gather(*(run(i) for i in which))


_SLOTS = ("breakfast", "lunch", "snack", "dinner")


def _days(plan):
    """(week, day name, day dict) for every day that carries meal objects."""
    for w in plan.get("diet_weeks") or []:
        for name, day in (w.get("daily_plan") or {}).items():
            if isinstance(day, dict):
                yield w.get("week_number"), name, day


def _day_macros(day):
    tot = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    measured = False
    for slot in _SLOTS:
        m = day.get(slot)
        if isinstance(m, dict) and isinstance(m.get("macros_approx"), dict):
            measured = True
            for k in tot:
                try:
                    tot[k] += float(m["macros_approx"].get(k) or 0)
                except (TypeError, ValueError):
                    pass
    return tot if measured else None


def audit():
    for f in sorted(OUT.glob("plan_*.json")):
        d = json.loads(f.read_text())
        plan, e = d["plan"], d["plan"].get("energy_prescription") or {}
        rec = plan.get("energy_reconciliation") or {}
        print(f"\n#{d['n']:02d} {d['title']}  [{plan.get('generation_method', 'rule_engine')}]")
        print(f"   target {e.get('target_calories')} band {e.get('band')} protein floor "
              f"{e.get('protein_floor_g')} g, macros {e.get('macros')}")
        print(f"   days quantified {rec.get('days_quantified')} / unquantified "
              f"{rec.get('days_unquantified')}, adjusted {rec.get('days_adjusted')}, below "
              f"protein floor {len(rec.get('days_below_protein_floor') or [])}")
        rows = [(w, n, _day_macros(day)) for w, n, day in _days(plan)]
        rows = [r for r in rows if r[2]]
        if rows:
            kc = [r[2]["calories"] for r in rows]
            pr = [r[2]["protein_g"] for r in rows]
            print(f"   delivered kcal {min(kc):.0f}-{max(kc):.0f}, protein {min(pr):.0f}-{max(pr):.0f} g")
        for key in ("safety_alerts", "dietary_type_alerts", "condition_safety_alerts",
                    "withheld_recommendations", "advisory_prose_alerts",
                    "conditions_without_food_floor", "conditions_screened_by_terms_only"):
            v = plan.get(key) or []
            if v:
                print(f"   {key}: {len(v)} — {json.dumps(v)[:240]}")
        for note in e.get("notes") or []:
            print(f"   note: {note[:160]}")


def render():
    """Each plan as a dietitian reads it: the person, the targets with their sources,
    the notes, then every day's meals with portions and computed totals."""
    for f in sorted(OUT.glob("plan_*.json")):
        d = json.loads(f.read_text())
        plan, prof, prefs = d["plan"], d["profile"], d["prefs"]
        rx, nt = plan.get("energy_prescription") or {}, plan.get("nutrient_targets") or {}
        rec = plan.get("energy_reconciliation") or {}
        L = [f"# {d['n']:02d}. {d['title']}", ""]
        L.append(f"**Profile:** age {prof.get('age')}, {prof.get('gender')}, {prof.get('height_cm')} cm, "
                 f"{prof.get('weight_kg')} kg ({prof.get('bmi_category')}), activity {prof.get('activity_level')}, "
                 f"{prof.get('dominant_dosha')} / Agni {prof.get('agni_type')}; conditions "
                 f"{prof.get('medical_history') or 'none'}; medicines {prof.get('current_medications') or 'none'}; "
                 f"diet {prefs}")
        L.append(f"**Generated by:** {plan.get('generation_method')} · {d.get('seconds')} s · "
                 f"composition {json.dumps({k: v for k, v in (plan.get('composition_report') or {}).items() if k != 'excluded_foods'})}")
        L.append(f"**Energy:** {rx.get('target_calories')} kcal (band {rx.get('band')}), protein "
                 f"{rx.get('protein_target_g')} g (floor {rx.get('protein_floor_g')}), "
                 f"carbs {nt.get('carbs_g')}, fat {nt.get('fat_g')}, fibre {nt.get('fibre_g')}, "
                 f"sodium {nt.get('sodium_mg')}, sugar {nt.get('added_sugar_g')}, water {nt.get('water_ml')}"
                 + (f", sat fat {nt['sat_fat_g']}" if nt.get('sat_fat_g') else ""))
        for n in rx.get("notes") or []:
            L.append(f"- {n}")
        for n in nt.get("notes") or []:
            L.append(f"- {n}")
        if plan.get("fasting_notice"):
            L.append(f"- **Fasting:** {plan['fasting_notice']}")
        for m in plan.get("medication_interactions") or []:
            L.append(f"- **{m['medication']}:** {m['advice']}")
        for n in plan.get("clinical_notes") or []:
            L.append(f"- **{n['topic']}:** {n['note']}")
        arc = plan.get("therapeutic_arc") or {}
        L.append(f"**Arc:** {' → '.join(w['phase'] for w in arc.get('weeks') or [])}; withheld {arc.get('withheld')}")
        pa = plan.get("pathya_apathya") or {}
        L.append(f"**Pathya:** {pa.get('pathya')}")
        L.append(f"**Apathya:** {pa.get('apathya')}")
        for key in ("condition_coaching", "hydration_guidance", "fasting_guidance", "ahar_vidhi"):
            if plan.get(key):
                L.append(f"**{key}:** {plan[key]}")
        L.append(f"**Checks:** in band {rec.get('days_in_band')}/{rec.get('days_quantified')}, below "
                 f"protein floor {len(rec.get('days_below_protein_floor') or [])}, unmet "
                 f"{rec.get('targets_unmet_notice')}; alerts "
                 + str({k: len(plan.get(k) or []) for k in ("safety_alerts", "dietary_type_alerts",
                                                        "condition_safety_alerts", "advisory_prose_alerts",
                                                        "withheld_recommendations")}))
        for w in plan.get("diet_weeks") or []:
            L.append(f"\n## Week {w.get('week_number')} — {w.get('phase')}"
                     + (" (rule engine)" if w.get("composed_by") else ""))
            for day, dd in (w.get("daily_plan") or {}).items():
                t = dd.get("day_totals") or {}
                L.append(f"\n**{day}**{' [FAST]' if dd.get('is_fasting') else ''} — {dd.get('theme', '')} — "
                         f"{t.get('calories')} kcal · P {t.get('protein_g')} · C {t.get('carbs_g')} · "
                         f"F {t.get('fat_g')} · fib {t.get('fiber_g')}")
                for slot in _SLOTS + ("special_drink",):
                    m = dd.get(slot)
                    if isinstance(m, dict):
                        mm = m.get("macros_approx") or {}
                        L.append(f"- {slot}: **{m.get('meal_name') or m.get('name')}** — {m.get('portion')} "
                                 f"({mm.get('calories')} kcal, P {mm.get('protein_g')})"
                                 + (" [substituted]" if m.get("substituted") else ""))
        (OUT / f"plan_{d['n']:02d}.md").write_text("\n".join(L) + "\n")
    print(f"  rendered {len(list(OUT.glob('plan_*.md')))} plans to {OUT}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "generate"
    nums = [int(a) for a in sys.argv[2:]] or list(range(1, len(PERSONAS) + 1))
    if cmd == "generate":
        asyncio.run(generate(nums))
    elif cmd == "audit":
        audit()
    elif cmd == "render":
        render()
