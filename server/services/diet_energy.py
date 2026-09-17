"""
Daily energy target for a diet plan, computed from the patient's actual body.

Until this module existed, `diet_brief_builder.target_calories` was the whole of the
app's nutrition arithmetic: `1800 if female else 2000`, nudged by BMI *category* and
goal. It read neither height, weight nor activity level, so a very active 82 kg woman
and a sedentary 78 kg woman were both told 1200 kcal, and a 95 kg active man on
muscle support was told 1900. `engine/calorie_calculator.py` — Harris-Benedict BMR ×
activity multiplier, with a macro split and a per-meal distribution, and documented in
CLAUDE.md as a Tier-1 core engine — was meanwhile called by nothing but its own unit
test.

Two things are computed here that the old heuristic could not express:

* **A floor that is a real floor.** The old `max(1200, ...)` clamp is gender-blind and
  sits below the basal requirement of most adults. A deficit is capped at the larger of
  the sex floor and the patient's own BMR, so the app never prescribes an intake below
  what the patient burns at rest. For the obese/diabetic probe profile that turns a
  1200 kcal prescription into 1485 — still a ~300 kcal deficit, and an honest one.
* **The states where a deficit is wrong regardless of the stated goal.** `diet_goal`
  has no `weight_gain` value, so an underweight patient picks `muscle_support` or
  `general_wellness`; underweight is read off `bmi_category` instead. Pregnancy and
  nursing take a surplus and can never take a deficit — the profile carries a single
  combined flag, so the smaller of the two additions is used and the reason is stated.

`meal_budget` is the reason this returns a dict rather than an int. The brief used to
state a daily number and nothing else, and the model divided it by eye — measured at
585-720 kcal against a stated 1200. A per-meal budget gives each generated meal an
anchor, and gives `diet_portion_reconciler` a per-slot target to correct against.
"""
from engine.calorie_calculator import calorie_calculator

# Unsupervised intake floors. Below these an adult needs clinical supervision, which
# is not what this app is: a plan is generated and followed at home.
_SEX_FLOOR = {"female": 1200, "male": 1500}

# `diet_goal` (DIET_GOALS in preferences_schema) → the goal vocabulary
# `calorie_calculator.GOAL_ADJUSTMENTS` speaks. Goals with no energy implication map
# to maintenance deliberately: `gut_health` and `energy` change what is eaten and when,
# not how much.
_GOAL_TO_ENERGY_GOAL = {
    "weight_loss": "weight_loss",        # -500
    "muscle_support": "muscle_gain",     # +300
    "detox": "detox",                    # -200
    "gut_health": "general_wellness",
    "energy": "general_wellness",
    "general_wellness": "general_wellness",
}

# g of protein per kg of body weight. A deficit without a protein floor costs lean
# mass, which is why weight loss sits above maintenance here rather than below.
_PROTEIN_PER_KG = {
    "weight_loss": 1.0,
    "muscle_support": 1.2,
    "general_wellness": 0.8,
    "gut_health": 0.8,
    "energy": 0.9,
    "detox": 0.8,
}

# Fraction of the day's energy each slot carries. Mirrors
# `calorie_calculator._meal_distribution`, kept here because the reconciler needs the
# fractions themselves and not only the rounded kcal.
MEAL_FRACTIONS = {"breakfast": 0.25, "lunch": 0.35, "snack": 0.10, "dinner": 0.30}

# A generated day is accepted if it lands inside ±this fraction of target.
BAND = 0.12


def _protein_basis_weight(weight_kg: float, height_cm, bmi_category: str) -> float:
    """The body weight a protein requirement should be read against.

    Lean mass does not scale with fat mass, so multiplying an obese patient's scale
    weight by g/kg overstates the requirement: an 84 kg woman at 157 cm came out at
    84 g/day, where adjusted body weight gives 66 g. Standard practice is ideal weight
    plus 40% of the excess. Below ideal weight the scale weight is used as-is — an
    underweight patient's requirement must not be scaled down toward their deficit.
    """
    if not height_cm or bmi_category not in ("overweight", "obese"):
        return weight_kg
    ideal = 22.0 * (float(height_cm) / 100.0) ** 2
    if weight_kg <= ideal:
        return weight_kg
    return ideal + 0.4 * (weight_kg - ideal)


def _estimated_target(user_profile: dict, diet_prefs: dict) -> int:
    """The pre-existing heuristic, kept for profiles with no height or weight.

    It is a poor estimator — that is the point of the rest of this module — but a
    profile that skipped the body-measurement step still needs a number, and one
    derived from gender and BMI category beats refusing to plan.
    """
    age = int(user_profile.get("age") or 30)
    gender = (user_profile.get("gender") or "male").lower()
    bmi = (user_profile.get("bmi_category") or "normal").lower()
    goal = diet_prefs.get("diet_goal") or "general_wellness"

    base = 1800 if gender == "female" else 2000
    if bmi in ("overweight", "obese"):
        base -= 300
    if bmi == "underweight":
        base += 200
    if age > 60:
        base -= 100
    if age < 20:
        base += 100
    if goal == "weight_loss":
        base -= 300
    elif goal == "muscle_support":
        base += 200
    return max(1200, min(3000, base))


def energy_target(user_profile: dict, diet_prefs: dict) -> dict:
    """Daily energy, macro floors and a per-meal budget for this patient.

    Keys:
      target_calories  what the plan should deliver per day
      floor_calories   never prescribe below this (max of sex floor and BMR)
      band             (low, high) acceptance window for a generated day
      basis            "measured" when height and weight were available, else "estimated"
      notes            the clinical adjustments applied, in the words shown to the user
    """
    gender = (user_profile.get("gender") or "male").lower()
    age = int(user_profile.get("age") or 30)
    height_cm = user_profile.get("height_cm")
    weight_kg = user_profile.get("weight_kg")
    activity = (user_profile.get("activity_level") or "moderate").lower()
    bmi_category = (user_profile.get("bmi_category") or "normal").lower()
    goal = diet_prefs.get("diet_goal") or "general_wellness"
    pregnant = bool(user_profile.get("pregnancy_or_nursing"))

    notes: list[str] = []
    sex_floor = _SEX_FLOOR.get(gender, 1200)

    # Underweight and pregnancy override the stated goal. `diet_goal` has no
    # weight-gain value, so an underweight patient's goal cannot express the surplus
    # they need, and a weight-loss goal entered during pregnancy must not be honoured.
    energy_goal = _GOAL_TO_ENERGY_GOAL.get(goal, "general_wellness")
    if bmi_category == "underweight" and energy_goal in ("weight_loss", "detox"):
        energy_goal = "general_wellness"
        notes.append("Underweight — the weight-loss deficit was not applied.")
    if pregnant and energy_goal in ("weight_loss", "detox"):
        energy_goal = "general_wellness"
        notes.append("Pregnancy or nursing — no energy deficit is applied.")

    if height_cm and weight_kg:
        basis = "measured"
        calc = calorie_calculator.calculate(
            gender=gender, age=age, weight_kg=float(weight_kg),
            height_cm=float(height_cm), activity_level=activity, goal=energy_goal,
        )
        bmr, tdee = calc["bmr"], calc["tdee"]
        target = calc["target_calories"]
    else:
        basis = "estimated"
        bmr = tdee = 0
        target = _estimated_target(user_profile, diet_prefs)
        notes.append(
            "Height or weight is missing from your profile, so this target is estimated "
            "from age, gender and BMI category. Adding your measurements makes it exact."
        )

    if bmi_category == "underweight":
        target += 300
        notes.append("Underweight — a 300 kcal surplus is included to support tissue gain.")

    # `muscle_support` and underweight are the same physiological ask — a positive
    # energy balance — so they stack into a surplus nobody will actually eat: a 52 kg
    # man came out at 3170 kcal. Bound the combined surplus over maintenance. The
    # pregnancy addition is added after this and is deliberately exempt, being a
    # separate requirement rather than a second helping of the same one.
    _MAX_SURPLUS = 500
    if tdee and target - tdee > _MAX_SURPLUS:
        target = tdee + _MAX_SURPLUS
        notes.append(
            f"Your goal and body weight together called for more than {_MAX_SURPLUS} kcal "
            f"above maintenance. The surplus is held at {_MAX_SURPLUS} kcal so the plan "
            "stays eatable; gain is steadier this way."
        )

    if pregnant:
        # The profile carries one combined pregnancy/nursing flag. Second-trimester
        # pregnancy is the smaller of the two classical additions, so it is the one
        # used; a nursing mother needs more and is told so rather than under-fed.
        target += 350
        notes.append(
            "Pregnancy or nursing — 350 kcal added. If you are breastfeeding, add a "
            "further 150-200 kcal and discuss it with your doctor."
        )

    # The floor is applied last so that every reduction above is bounded by it.
    floor = max(sex_floor, round(bmr)) if bmr else sex_floor
    if target < floor:
        notes.append(
            f"The deficit for your goal would have put this plan at {target} kcal, below "
            f"your resting requirement of {floor} kcal. It has been raised to {floor}."
        )
        target = floor

    target = int(round(target / 10.0) * 10)

    protein_per_kg = _PROTEIN_PER_KG.get(goal, 0.8)
    if pregnant:
        protein_per_kg = max(protein_per_kg, 1.1)
    if weight_kg:
        protein_floor = int(round(_protein_basis_weight(
            float(weight_kg), height_cm, bmi_category) * protein_per_kg))
    else:
        # No weight on file — fall back to a share of energy rather than dropping the
        # floor entirely, since the protein floor is what a low day damages first.
        protein_floor = int(round(target * 0.15 / 4))

    return {
        "target_calories": target,
        "floor_calories": int(floor),
        "band": (int(round(target * (1 - BAND))), int(round(target * (1 + BAND)))),
        "bmr": int(bmr),
        "tdee": int(tdee),
        "basis": basis,
        "energy_goal": energy_goal,
        "protein_floor_g": protein_floor,
        "macros": calorie_calculator._macros(target, energy_goal),
        "meal_budget": {
            slot: int(round(target * frac)) for slot, frac in MEAL_FRACTIONS.items()
        },
        "notes": notes,
    }
