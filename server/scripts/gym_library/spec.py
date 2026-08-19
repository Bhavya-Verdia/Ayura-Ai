"""`M` — one curated movement, written the way a coach would specify it.

Defaults carry the common case so a spec line says only what is true of THIS
movement. The defaults are deliberately the conservative ones: a movement is an
accessory until someone says it can open a session, and it has no impact until
someone says it lands.
"""


def M(name, *, bucket, pattern, mechanic, equipment, role,
      src=..., load_class=None, skill_floor="beginner", level="beginner",
      family=None, impact="none", unilateral=False, rep_style="reps",
      category="strength", pm=None, sm=None, instructions=None, cue=None,
      contra=(), preg=None, easier=None, harder=None, modification=None,
      goals=None, dosha=None, cal_per_min=None, canonical=False):
    """One movement.

    `src` defaults to the movement's own name — most curated entries reuse the
    upstream instructions and anatomy for a movement of that name. Pass
    `src=None` for an entry written here, or `src="Other Name"` when the
    upstream entry is filed under a name no coach uses.
    """
    return {
        "name": name,
        "src": name if src is ... else src,
        # The lift a coach names when they name the pattern — the movement a
        # block is built around, as opposed to a good variant of it.
        "canonical": canonical,
        "bucket": bucket,
        "movement_pattern": pattern,
        "mechanic": mechanic,
        "equipment": equipment,
        "role": role,
        "load_class": load_class,
        "skill_floor": skill_floor,
        "level": level,
        "family": family or _default_family(name),
        "impact": impact,
        "unilateral": unilateral,
        "rep_style": rep_style,
        "category": category,
        "primary_muscles": pm,
        "secondary_muscles": sm,
        "instructions": instructions,
        "cue": cue,
        "contraindications": list(contra),
        "pregnancy_safe": preg,
        "progression": {"easier": easier, "harder": harder},
        "modification": modification,
        "goal_suitability": goals,
        "dosha_suitability": dosha,
        "calories_per_minute": cal_per_min,
    }


def _default_family(name: str) -> str:
    """A last resort, not a strategy — the old engine derived every family this
    way and it produced four families for four shrugs. Every curated entry
    should name its own; this only catches an omission."""
    return name.lower().replace(" ", "_")
