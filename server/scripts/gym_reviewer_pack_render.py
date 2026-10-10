"""Render the reviewer pack's plan sections from `gym_reviewer_pack.py generate`.

Everything in a section is the plan's own text except the "Please check" list,
which is a reviewer's question per plan and lives in PLEASE_CHECK. Re-read
those questions against the new output whenever the pack is regenerated: a
question about behaviour the plan no longer has is a question the reviewer will
spend time on for nothing.
"""
import json
from pathlib import Path

DAY = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
       "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun"}
EQUIPMENT = {"barbell": "barbell", "dumbbells": "dumbbells", "machines": "machines",
             "cables": "cables", "kettlebell": "kettlebell", "resistance_bands": "bands",
             "cardio_machines": "cardio machines"}
NOTICES = ("age_notice", "pool_notice", "schedule_notice", "focus_notice", "cardio_notice",
           "preference_notice", "adaptation_notice", "substitution_notice", "injury_notice",
           "intensity_notice", "block_notice")
INJURY = {"lower_back": "lower back"}
LIFT = {"squat": "squat", "bench": "bench", "deadlift": "deadlift",
        "overhead_press": "overhead press", "row": "row"}

# One reviewer question per thing the code cannot decide. Carried from the
# first pack and re-checked against this run's output.
PLEASE_CHECK: dict[int, list[str]] = {
    1: ["Is three full-body days of 8–12 reps, with no sets below 8 reps, the right ceiling for a 15-year-old who asked for five days?",
        "Is a barbell bench press appropriate at this age, given an adult must supervise?",
        "Asthma changes no exercise, only a warm-up note that asks for ten minutes — while the listed warm-up is shorter. Is that enough?"],
    2: ["Is the pregnancy note's stop-list complete, and is it right to give it without asking the trimester?",
        "Push-ups, goblet squats, an inchworm warm-up and an underhand inverted row are kept; supine pressing and supine rest poses are removed. Would you keep or remove anything else?",
        "Week 3 takes the main lifts to 5 sets of 12–15. Is any volume increase right in pregnancy, or should the block stay flat?",
        "The plan says it is not a prenatal programme. Should pregnancy instead block plan generation until a clinician clears it?"],
    3: ["Moderate loads, 10–15 reps, a balance block each session and steady cardio only — is that right for heart disease at 75?",
        "Should a cardiac patient this age get any plan before cardiologist clearance, or only the note asking for it?",
        "The kettlebell deadlift starts at a 14 kg bell for a sedentary 75-year-old who has never lifted. Too heavy for a first session?",
        "Is the diabetes note (check glucose before training, carry fast carbohydrate) correct and sufficient?"],
    4: ["Jumping and running are removed for BMI ≥ 30 and conditioning is steady-state only. Too cautious, or right for month one?",
        "Inverted rows and pike push-ups at 96 kg in week one — achievable, or should the plan start a step easier?",
        'The Kapha rest day prescribes Kapalabhati and a "vigorous" walk; the AI coaching says "easy walking". Which is right for a sedentary start?',
        "Is a bodyweight-and-bands programme at this volume reasonable for a sedentary start?"],
    5: ["Are the loads derived from the entered lifts (170 × 5 squat, 125 × 5 bench, 200 × 4 deadlift) sensible for sets of 3–5 with two in reserve?",
        "Thursday opens on push-press triples and Friday on Romanian-deadlift triples. Would you programme either as a heavy main lift, or should the second days lead with the press and the squat?",
        "Is one heavy main lift per session plus 4-set support work the right volume for an advanced lifter?",
        "Squat and deadlift on the same day: acceptable, given the deadlift is the support lift at 6–8?",
        "The deload week keeps 5 sets of 3–5 at 80% load. Enough of a deload?"],
    6: ["Free bars over the face and body are swapped for machines for epilepsy — but a seated dumbbell shoulder press (weights overhead) and a barbell Romanian deadlift remain. Should those go too?",
        "Glaucoma removes head-below-heart positions, yet child's pose stays in the cool-down. Keep it?",
        "Should heavy lower-body work be limited further for glaucoma, beyond the no-breath-holding instruction?",
        "Monday ends on battle-rope intervals at about 8/10. Are hard intervals acceptable with glaucoma, or should conditioning be steady?"],
    7: ["Deadlifts and other loaded hinges are removed. Standing barbell overhead press, barbell shrugs, farmer's walks, lunges and step-ups are kept. Which would you remove for sciatica with a declared lower-back injury?",
        "Is the stop-rule in the back note — stop an exercise if pain spreads further down the leg — the right instruction for a gym user?",
        "Week 3 runs main lifts at 5 × 20–25 with 20-second accessory rest. Appropriate with an active back problem?",
        "Monday's finisher is twelve rounds of high-knee intervals. Is repeated impact right with sciatica?"],
    8: ["Muscle gain with conditioning kept light — right for someone underweight?",
        'Anaemia now gets steady cardio rather than intervals, matching its note. Should depression change anything? (The AI coaching adds a "skip when mentally unsteady" line on its own; the engine adds nothing for depression.)',
        'Is pricing loads at the midpoint of the male and female standards the right default when sex is "other" or unanswered?'],
    9: ["Is avoiding spinal flexion, twisting and side bends correct for osteoporosis, and are the remaining exercises (including a hanging inverted row) safe for RA hands and wrists?",
        "The plan withholds all impact for osteoporosis. Too Fit to Fracture recommends some impact work where there is no vertebral fracture. Should the app ask about fracture history and allow it?",
        "Two 30-minute sessions a week — enough to matter for bone, or too little?"],
    10: ["Three exercises in 20 minutes, no sets below 12 reps, breathing out on every effort — right for hypertension?",
         "Should a hypertensive person be told a blood-pressure threshold for skipping (the plan says 180/110)?",
         "Monday's main lifts are cut to 2 sets to fit 20 minutes, and the day now says so. Better to cut an exercise instead, or keep the sets and run long?",
         "A 28 kg kettlebell deadlift and a 45–52.5 kg bench press for someone who rated himself intermediate but is sedentary. Should a sedentary answer lower the starting load as well as the volume?"],
    11: ["Are the starting bells sensible for a beginner woman (4 kg press, 6–8 kg row and goblet squat, 16 kg deadlift)?",
         "The plan needs four bell sizes. Is that realistic for a home lifter, or should it be built around the one or two bells they own — which means asking which bells they have?",
         "Mountain-climber intervals on Monday for a beginner with no health limits — appropriate?"],
    12: ["Block 2 builds on block 1 because 12 of 16 sessions were logged; with fewer than half it would repeat. Is half the right threshold?",
         "Block 2 starts each logged lift at the heaviest load the person managed in block 1 (65 kg × 10 → 55–65 kg for 8–10). Should a new block start there, a little above, or a little below?",
         "Loads come from the strongest recent set rather than the most recent. Right choice?"],
}


def _load(ex: dict) -> str:
    """The figure and the engine's own words for where it came from."""
    text = ex.get("weight_range") or ""
    head, _, rest = text.partition(" · ")
    if "kg" not in head and "bell" not in head:
        return head or "—"   # bodyweight, a band, or effort-based: not a weight
    basis = rest.split(" — ")[0].strip()
    if not basis or basis.startswith("a starting estimate"):
        return f"{head} (estimate)"
    return f"{head} ({basis})"


def _who(d: dict) -> str:
    p, f = d["profile"], d["prefs"]
    health = ", ".join(c.replace("_", " ").replace("type2", "type 2")
                       for c in p.get("medical_history") or []) or "none"
    bits = [f"{p['gender']}, {p['age']}, {p['weight_kg']} kg, {p['fitness_level']}, "
            f"{p['activity_level'].replace('_', ' ')}, {p['dominant_dosha'].title()} · health: {health}"]
    if p.get("pregnancy_or_nursing"):
        bits.append("pregnant")
    if f.get("injuries"):
        bits.append("injury: " + ", ".join(INJURY.get(i, i) for i in f["injuries"]))
    if f.get("known_lifts"):
        bits.append("entered lifts: " + ", ".join(
            f"{LIFT[k]} {v['kg']} kg × {v['reps']}" for k, v in f["known_lifts"].items()))
    if p.get("allergies"):
        bits.append("allergy: " + ", ".join(a.replace("nuts_tree", "tree nuts") for a in p["allergies"]))
    kit = [e for e in f["available_equipment"] if e != "bodyweight"]
    kit_s = ("full gym" if len(kit) >= 6 else ", ".join(EQUIPMENT[e] for e in kit))
    us = d["plan"]["user_summary"]
    return (f"**Who:** {' · '.join(bits)}\\\n"
            f"**Asked for:** {f['gym_goal'].replace('_', ' ')}, {f['workout_days_per_week']} days × "
            f"{f['workout_duration_minutes']} min, {kit_s} · **Built:** {us['workout_days']} days, "
            f"{us['set_scheme'].replace('_', ' ')} sets, block {us.get('block', 1)}")


def _told(plan: dict) -> list[str]:
    out = [plan[k] for k in NOTICES if plan.get(k)]
    for g in plan.get("condition_guidance") or []:
        out.append(f"*{g['label']}:* {g['note']} — source: {g['source']}")
    return out


def _week_table(plan: dict) -> str:
    rows = ["| Day | Exercise | Sets × reps | Rest | Starting load |",
            "| --- | --- | --- | --- | --- |"]
    for day in plan["four_week_plan"][0]["days"]:
        work = day.get("main_workout") or []
        for i, ex in enumerate(work):
            label = (f"{DAY.get(day['day_name'], day['day_name'])} · {day['focus']} · "
                     f"{day['estimated_duration_minutes']} min") if i == 0 else ""
            rows.append(f"| {label} | {ex['exercise_name']} | {ex['sets']} × {ex['reps']} | "
                        f"{ex.get('rest_seconds', 0)}s | {_load(ex)} |")
    return "\n".join(rows)


def _sessions(plan: dict) -> str:
    days = plan["four_week_plan"][0]["days"]
    first = next(d for d in days if d.get("main_workout"))
    rest = next((d for d in days if not d.get("main_workout")), None)
    lines = [f"Warm-up ({first['day_name']}): " + "; ".join(first.get("warmup") or []) + "."]
    if first.get("balance"):
        lines.append("Balance block: " + "; ".join(first["balance"]) + ".")
    lines.append("Cool-down: " + "; ".join(first.get("cooldown") or []) + ".")
    if rest and rest.get("rest_day_recovery"):
        acts = rest["rest_day_recovery"].get("activities") or []
        lines.append("Rest days: " + "; ".join(acts[:3]) + ".")
    for d in days:
        if d.get("duration_notice"):
            lines.append(f"{d['day_name']}: {d['duration_notice']}")
            break
    return "\\\n".join(lines)


def _four_weeks(plan: dict) -> str:
    steps = [f"W{p['week']} {p['theme']} {p['main_lift_prescription']}"
             for p in plan.get("progression") or []]
    return "**Four weeks (main lifts):** " + " → ".join(steps)


def _coaching(plan: dict) -> list[str]:
    v, r = plan.get("vyayama_vidhi") or {}, plan.get("recovery_protocol") or {}
    out = []
    if v.get("ardhashakti_guideline"):
        out.append(f"*When to stop:* {v['ardhashakti_guideline']}")
    if v.get("vyayama_contraindications"):
        out.append("*Skip training today if:* " + "; ".join(v["vyayama_contraindications"]))
    if r.get("active_recovery"):
        out.append(f"*Rest days:* {r['active_recovery']}")
    for w in plan.get("nutrition_withheld") or []:
        out.append(f"*Withheld by the food screen:* the {w['field'].replace('_', ' ')} "
                   f"suggestion — it {w['reason']}")
    prog = plan.get("progression") or []
    if prog and prog[-1].get("coach_note"):
        out.append(f"*Week 4 coaching:* {prog[-1]['coach_note']}")
    return out


def render(d: dict, lead: str | None = None) -> str:
    plan, n = d["plan"], d["n"]
    parts = [f"## Plan {n} — {d['title']}", _who(d)]
    if lead:
        parts.append(lead)
    told = _told(plan)
    if told:
        parts += ["**What the plan told them**", "\n".join(f"- {t}" for t in told)]
    else:
        parts.append("No notes were shown: this person declared no condition, injury or limit.")
    parts += ["**Week 1**", _week_table(plan), _sessions(plan), _four_weeks(plan)]
    coaching = _coaching(plan)
    if coaching:
        parts += ["**AI coaching**", "\n".join(f"- {c}" for c in coaching)]
    checks = PLEASE_CHECK.get(n) or []
    if checks:
        parts += ["**Please check**", "\n".join(f"- [ ] {c}" for c in checks)]
    return "\n\n".join(parts)


LEADS = {
    8: 'Sex was answered "other", so every load is priced at the midpoint of the male and '
       "female standards.",
    12: "The logged sets behind this plan are simulated: block 1 was generated, then each main "
        'lift was "logged" at its prescribed top load for 10 reps, rising about 4% a week over '
        "12 of the 16 sessions. Everything below is the engine's real response to that history.",
}


def render_all(out: Path):
    for f in sorted(out.glob("plan_*.json")):
        d = json.loads(f.read_text())
        md = render(d, LEADS.get(d["n"]))
        f.with_suffix(".md").write_text(md)
        rows = sum(1 for line in md.splitlines() if line.startswith("| ")) - 2
        print(f"{f.with_suffix('.md').name}: {len(md)} chars, {rows} exercise rows")
