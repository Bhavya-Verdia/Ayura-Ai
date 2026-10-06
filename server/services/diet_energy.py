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
# `other` and an unset gender take the mean, the same way the BMR equation does.
# It used to be `.get(gender, 1200)` — the female floor — beside a BMR that fell
# through to the male equation, so a user who chose `other` got half of each.
_SEX_FLOOR = {"female": 1200, "male": 1500, "other": 1350}

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
# ── Age ──────────────────────────────────────────────────────────────────────
# The profile accepts age 10-120 and the energy model treated all of it as one adult.
# Mifflin-St Jeor and Harris-Benedict are derived from and validated on adults; they
# are not paediatric equations, and a growing child's requirement is not a smaller
# adult's. Measured before this: a 10-year-old at 150 cm / 45 kg was handed 1990 kcal
# from the adult formula, with nothing in the brief to say a child was being fed.
#
# Schofield (1985) is the WHO/FAO standard for this band and is weight-only, so it
# needs nothing the profile does not already hold.
_PAEDIATRIC_MAX_AGE = 17
_SCHOFIELD_10_17 = {          # BMR kcal/day = a * weight_kg + b
    "male": (17.686, 658.2),
    "female": (13.384, 692.6),
}

# Sarcopenia. Protein requirement RISES with age while appetite falls, so the one
# group most at risk of losing muscle was being given the lowest floor in the table.
_GERIATRIC_MIN_AGE = 65
_GERIATRIC_PROTEIN_PER_KG = 1.1
_PAEDIATRIC_PROTEIN_PER_KG = 1.0


def _schofield_bmr(gender: str, weight_kg: float) -> float:
    if gender in _SCHOFIELD_10_17:
        a, b = _SCHOFIELD_10_17[gender]
        return a * float(weight_kg) + b
    # `other` or unset — the mean, as the adult equation does.
    return sum(a * float(weight_kg) + b for a, b in _SCHOFIELD_10_17.values()) / 2


_PROTEIN_PER_KG = {
    "weight_loss": 1.0,
    # ACSM/AND/DC position stand (2016): 1.2-2.0 g/kg for training adults. 1.2 was
    # the bottom of that range, and a vegan's lower-digestibility protein sits
    # further from it.
    "muscle_support": 1.4,
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
    # Unset defaults to the sex-neutral path, not to male. Defaulting an absent
    # answer to one of the two options is a guess presented as a fact.
    gender = (user_profile.get("gender") or "other").lower()
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


# ── Pregnancy and lactation, by stage ───────────────────────────────────────
# ICMR-NIN, Nutrient Requirements for Indians (2020). The profile used to carry one
# combined flag and every pregnant or nursing user got +350 kcal — a first-trimester
# woman (who needs no addition) was over-fed and a breastfeeding mother (who needs
# +600 in the first six months) was told to add the rest herself. The profile has
# recorded `pregnancy_status` and `pregnancy_trimester` since the gym pass; nothing on
# the diet path read them.
_PREGNANCY_KCAL = {1: 0, 2: 350, 3: 350}
_PREGNANCY_PROTEIN_G = {1: 0.0, 2: 9.5, 3: 22.0}
_LACTATION_KCAL, _LACTATION_PROTEIN_G = 600, 16.9      # 0-6 months postpartum
_ICMR_2020 = "ICMR-NIN, Nutrient Requirements for Indians (2020)"

# ── Weight loss ──────────────────────────────────────────────────────────────
# AHA/ACC/TOS (2013): a 500-750 kcal daily deficit, or 1200-1500 kcal for women and
# 1500-1800 for men. The floor here used to be the patient's own BMR, which is a
# fitness heuristic rather than clinical guidance: it held a sedentary 104 kg
# diabetic asking to lose weight at maintenance, 2110 kcal. The sex floors below are
# the guideline's lower bounds.
_DEFICIT_KCAL = 500

# ── Disease-specific targets ─────────────────────────────────────────────────
# Protein per kg is capped in chronic kidney disease (KDIGO 2020: 0.8 g/kg in CKD
# G3-G5 not on dialysis, avoiding > 1.3 g/kg). The goal table above — 1.0 for weight
# loss, 1.2 for muscle — and the over-65 floor of 1.1 each pushed a CKD patient past
# it. A renal cap wins over every raise except pregnancy, which a nephrologist sets.
_RENAL_PROTEIN_CAP = 0.8
_RENAL = {"kidney_disease", "chronic_kidney_disease"}
_DIABETES = {"diabetes", "diabetes_type2", "diabetes_type1", "gestational_diabetes",
             "prediabetes", "insulin_resistance"}
_CARDIAC = {"heart_disease", "high_cholesterol", "hypertension", "heart_failure",
            "dyslipidemia", "fatty_liver"}


def _canon(conditions) -> set:
    return {str(c).strip().lower().replace(" ", "_") for c in conditions or []}


def nutrient_targets(target_kcal: int, protein_target_g: int, protein_floor_g: int,
                     conditions, *, age: int, weight_kg, pregnant_or_nursing: bool,
                     fluid_weight_kg=None) -> dict:
    """What a dietitian writes beside the energy figure, for this patient.

    Carbohydrate, fat and fibre follow from the energy and protein targets, so the
    three macros always sum to the day's energy — the old split was a fixed
    percentage of energy and contradicted the protein floor beside it (119 g of
    protein for a 12-year-old whose floor was 40). Each target names its source,
    because a reviewer checks the figure against it.
    """
    conds = _canon(conditions)
    diabetic, cardiac, renal = conds & _DIABETES, conds & _CARDIAC, conds & _RENAL
    protein_kcal = protein_target_g * 4
    # Fat 30% of energy (ICMR-NIN 2020 and the IOM range of 20-35%); 25% where LDL
    # is the target.
    fat_pct = 0.25 if cardiac else 0.30
    fat_g = round(target_kcal * fat_pct / 9)
    carbs_g = max(0, round((target_kcal - protein_kcal - fat_g * 9) / 4))
    # Diabetes: carbohydrate held at or under half the energy, the remainder moved
    # to fat — but never past 35%, the top of the acceptable range. Where both
    # limits bind (a renal cap holds protein down too) carbohydrate takes the rest:
    # a diabetic kidney patient came out at 40% fat before this.
    if diabetic and carbs_g * 4 > 0.50 * target_kcal:
        carbs_g = round(0.50 * target_kcal / 4)
        fat_g = round((target_kcal - protein_kcal - carbs_g * 4) / 9)
        if fat_g * 9 > 0.35 * target_kcal:
            fat_g = round(0.35 * target_kcal / 9)
            carbs_g = max(0, round((target_kcal - protein_kcal - fat_g * 9) / 4))
    fibre_g = max(25, round(14 * target_kcal / 1000))                  # 14 g / 1000 kcal
    targets = {
        "energy_kcal": target_kcal,
        "protein_g": {"target": protein_target_g, "min": protein_floor_g,
                      **({"max": protein_target_g} if renal else {})},
        # In diabetes the target is AVAILABLE carbohydrate (total less fibre).
        "carbs_g": {"target": carbs_g,
                    "pct_energy": round(carbs_g * 4 * 100 / max(target_kcal, 1)),
                    **({"basis": "available (total minus fibre)"} if diabetic else {})},
        "fat_g": {"target": fat_g, "pct_energy": round(fat_g * 9 * 100 / max(target_kcal, 1))},
        "fibre_g": {"min": fibre_g if age >= 18 else max(20, round(fibre_g * 0.8))},
        # WHO (2023): < 2 g sodium (5 g salt) a day for every adult.
        "sodium_mg": {"max": 2000 if age >= 18 else 1500},
        # WHO (2015): free sugars < 10% of energy, ideally < 5%. Diabetes: none added.
        "added_sugar_g": {"max": 0 if diabetic else round(0.05 * target_kcal / 4)},
        "sources": {
            "protein": ("KDIGO 2020 (CKD)" if renal else _ICMR_2020),
            "fibre": "14 g per 1000 kcal (Dietary Guidelines for Americans 2020-25; ICMR-NIN 2020 ≥ 25 g)",
            "sodium": "WHO, sodium intake guideline (2023)",
            "added_sugar": "WHO, sugars intake guideline (2015)",
        },
        "notes": [],
    }
    if cardiac:
        # AHA (2021): saturated fat < 6-7% of energy for LDL lowering.
        targets["sat_fat_g"] = {"max": round(0.07 * target_kcal / 9)}
        targets["sources"]["sat_fat"] = "AHA/ACC 2019 primary prevention; AHA dietary guidance 2021"
    if diabetic:
        targets["sources"]["carbs"] = "ADA Standards of Care in Diabetes (2024), section 5"
        pct = targets["carbs_g"]["pct_energy"]
        if pct <= 50:
            targets["notes"].append(
                "Carbohydrate is kept to half the day's energy or less, from whole grains, "
                "pulses and vegetables, spread evenly across meals.")
        else:
            # Only where a renal protein cap and the fat ceiling both bind. Said
            # outright: a note promising "half or less" beside 55% is the plan
            # contradicting its own figure.
            targets["notes"].append(
                f"Carbohydrate is {pct}% of energy — above the usual half, because protein "
                "is capped for your kidneys and fat is already at its limit. Take it from "
                "low-glycaemic whole grains, pulses and vegetables, spread evenly, never "
                "as sugar or refined flour.")
    if renal:
        targets["notes"].append(
            "Kidney disease: protein is capped at 0.8 g/kg. Potassium and phosphorus "
            "limits depend on your blood results — ask your nephrologist for them.")
    # Fluids: 35 ml/kg for adults (ESPEN); the two states where a fixed target can
    # harm are the ones whose fluid allowance is set by the treating doctor.
    if renal or "heart_failure" in conds:
        targets["water_ml"] = {"target": None}
        targets["notes"].append("Fluids: follow the limit your doctor sets — no target is given here.")
    elif weight_kg:
        per_kg = 30 if age >= 65 else 35
        extra = 700 if pregnant_or_nursing else 0
        # On the same adjusted weight as protein: 35 ml/kg of a 104 kg man's scale
        # weight asked for 3.65 L a day.
        fluid_kg = float(fluid_weight_kg or weight_kg)
        targets["water_ml"] = {"target": int(round((fluid_kg * per_kg + extra) / 50) * 50)}
    return targets


# A day under 12% of energy from protein reads as a starch-heavy plan however its
# g/kg figure was reached; for an adult the target is raised to that share.
_MIN_PROTEIN_SHARE = 0.12


def energy_target(user_profile: dict, diet_prefs: dict) -> dict:
    """Daily energy, protein, the nutrient targets and a per-meal budget.

    Keys:
      target_calories  what the plan should deliver per day
      floor_calories   never prescribe below this (the guideline floor for the sex)
      band             (low, high) acceptance window for a generated day
      basis            "measured" when height and weight were available, else "estimated"
      protein_target_g / protein_floor_g
      nutrient_targets the macro, fibre, sodium, sugar and fluid targets, with sources
      notes            the clinical adjustments applied, in the words shown to the user
    """
    from services.diet_brief_builder import diet_conditions

    # Unset defaults to the sex-neutral path, not to male. Defaulting an absent
    # answer to one of the two options is a guess presented as a fact.
    gender = (user_profile.get("gender") or "other").lower()
    age = int(user_profile.get("age") or 30)
    height_cm = user_profile.get("height_cm")
    weight_kg = user_profile.get("weight_kg")
    activity = (user_profile.get("activity_level") or "moderate").lower()
    bmi_category = (user_profile.get("bmi_category") or "normal").lower()
    goal = diet_prefs.get("diet_goal") or "general_wellness"
    conditions = diet_conditions(user_profile, diet_prefs)
    renal = bool(_canon(conditions) & _RENAL)

    # Pregnancy or lactation, and which stage. Left unspecified, the flag is read as
    # pregnancy in the second trimester — the case the old flat figure was written
    # for — and the plan says that is what it assumed.
    flag = bool(user_profile.get("pregnancy_or_nursing"))
    status = str(user_profile.get("pregnancy_status") or "").lower()
    nursing = flag and status == "nursing"
    pregnant = flag and not nursing
    trimester = user_profile.get("pregnancy_trimester")
    try:
        trimester = int(trimester) if trimester else None
    except (TypeError, ValueError):
        trimester = None
    if trimester not in (1, 2, 3):
        trimester = None

    notes: list[str] = []
    if gender not in ("male", "female"):
        notes.append(
            "Your profile does not record a sex for metabolic purposes, so this target "
            "is the average of the two standard equations. Setting it in Settings makes "
            "the figure more exact."
        )
    sex_floor = _SEX_FLOOR.get(gender, _SEX_FLOOR["other"])

    # Underweight, pregnancy, lactation and childhood override the stated goal.
    energy_goal = _GOAL_TO_ENERGY_GOAL.get(goal, "general_wellness")
    if bmi_category == "underweight" and energy_goal in ("weight_loss", "detox"):
        energy_goal = "general_wellness"
        notes.append("Underweight — the weight-loss deficit was not applied.")
    if flag and energy_goal in ("weight_loss", "detox"):
        energy_goal = "general_wellness"
        notes.append("Pregnancy or breastfeeding — no energy deficit is applied.")
    is_child = age <= _PAEDIATRIC_MAX_AGE
    if is_child and energy_goal in ("weight_loss", "detox"):
        energy_goal = "general_wellness"
        notes.append(
            "Under 18 — no energy deficit is applied. Weight management before "
            "adulthood belongs with a paediatrician, not a meal plan."
        )

    if height_cm and weight_kg:
        basis = "measured"
        if is_child:
            # Schofield rather than Mifflin: the adult equations are not validated
            # below 18, and this band's requirement includes growth.
            bmr = _schofield_bmr(gender, float(weight_kg))
            tdee = bmr * calorie_calculator.ACTIVITY_MULTIPLIERS.get(activity, 1.55)
            target = round(tdee)
            notes.append(
                "Under 18 — energy is calculated with the Schofield (WHO/FAO) equation "
                "for this age band rather than the adult one, and includes growth. "
                "Please review this plan with a paediatrician."
            )
        else:
            bmr = calorie_calculator._bmr(gender, age, float(weight_kg), float(height_cm))
            tdee = bmr * calorie_calculator.ACTIVITY_MULTIPLIERS.get(activity, 1.55)
            adjust = {"weight_loss": -_DEFICIT_KCAL, "detox": -200,
                      "muscle_gain": 300}.get(energy_goal, 0)
            target = round(tdee + adjust)
            if adjust < 0:
                notes.append(
                    f"Weight loss — a {-adjust} kcal daily deficit from your maintenance of "
                    f"{round(tdee)} kcal (AHA/ACC/TOS 2013), for about 0.5 kg a week.")
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

    extra_protein = 0.0
    if pregnant:
        stage = trimester or 2
        target += _PREGNANCY_KCAL[stage]
        extra_protein = _PREGNANCY_PROTEIN_G[stage]
        assumed = "" if trimester else (
            " Your trimester is not on your profile, so the second trimester was assumed — "
            "add it in Settings for an exact figure.")
        notes.append(
            f"Pregnancy, trimester {stage} — {_PREGNANCY_KCAL[stage]} kcal and "
            f"{extra_protein:g} g protein added ({_ICMR_2020}).{assumed}")
    elif nursing:
        target += _LACTATION_KCAL
        extra_protein = _LACTATION_PROTEIN_G
        notes.append(
            f"Breastfeeding — {_LACTATION_KCAL} kcal and {extra_protein:g} g protein added "
            f"for the first six months ({_ICMR_2020}); from six months the addition is "
            "520 kcal.")

    # The floor is applied last so that every reduction above is bounded by it. It is
    # the guideline floor for the sex, not the patient's BMR (see `_DEFICIT_KCAL`).
    floor = sex_floor if not is_child else max(sex_floor, round(bmr or 0))
    if target < floor:
        notes.append(
            f"The deficit for your goal would have put this plan at {target} kcal, below "
            f"the {floor} kcal minimum for an unsupervised plan. It has been raised to "
            f"{floor}.")
        target = floor

    target = int(round(target / 10.0) * 10)

    # Two figures. The FLOOR is the requirement for this stage of life — 0.8 g/kg for
    # an adult, 1.0 growing, 1.1 past 65 when muscle is lost and appetite falls — and
    # the TARGET is what the goal asks for on top (weight loss and training raise it).
    floor_per_kg = 0.8
    if is_child:
        floor_per_kg = _PAEDIATRIC_PROTEIN_PER_KG
    if age >= _GERIATRIC_MIN_AGE:
        floor_per_kg = _GERIATRIC_PROTEIN_PER_KG
        if not renal:
            notes.append(
                f"Over {_GERIATRIC_MIN_AGE} — protein is raised to at least "
                f"{_GERIATRIC_PROTEIN_PER_KG} g/kg to protect muscle.")
    target_per_kg = max(_PROTEIN_PER_KG.get(goal, 0.8), floor_per_kg)
    from services.diet_clinical_notes import has_ibd
    if has_ibd(user_profile):
        # ESPEN (2023): 1.2-1.5 g/kg in active inflammatory bowel disease, where
        # losses and catabolism raise the requirement.
        target_per_kg = max(target_per_kg, 1.2)
        notes.append("Crohn's / ulcerative colitis — protein raised to 1.2 g/kg (ESPEN 2023).")
    if renal and not flag and target_per_kg > _RENAL_PROTEIN_CAP:
        target_per_kg = _RENAL_PROTEIN_CAP
        floor_per_kg = min(floor_per_kg, _RENAL_PROTEIN_CAP)
        notes.append(
            f"Kidney disease — protein is capped at {_RENAL_PROTEIN_CAP} g/kg (KDIGO 2020), "
            "whatever the goal. Your nephrologist may set it lower.")
    if weight_kg:
        basis_weight = _protein_basis_weight(float(weight_kg), height_cm, bmi_category)
        protein_floor = int(round(basis_weight * floor_per_kg + extra_protein))
        protein_target = int(round(basis_weight * target_per_kg + extra_protein))
        if not renal and not is_child:
            # Diabetes: 15-20% of energy is usual (ADA 2024) and it is what lets
            # carbohydrate stay at half the energy without fat passing 35%.
            share = 0.15 if (_canon(conditions) & _DIABETES) else _MIN_PROTEIN_SHARE
            protein_target = max(protein_target, int(round(target * share / 4)))
    else:
        # No weight on file — fall back to a share of energy rather than dropping the
        # floor entirely, since the protein floor is what a low day damages first.
        protein_target = protein_floor = int(round(target * 0.15 / 4))
    protein_floor = min(protein_floor, protein_target)

    targets = nutrient_targets(
        target, protein_target, protein_floor, conditions, age=age, weight_kg=weight_kg,
        pregnant_or_nursing=flag,
        fluid_weight_kg=(_protein_basis_weight(float(weight_kg), height_cm, bmi_category)
                         if weight_kg else None))
    return {
        "target_calories": target,
        "floor_calories": int(floor),
        "band": (int(round(target * (1 - BAND))), int(round(target * (1 + BAND)))),
        "bmr": int(bmr),
        "tdee": int(tdee),
        "basis": basis,
        "energy_goal": energy_goal,
        "protein_target_g": protein_target,
        "protein_floor_g": protein_floor,
        "macros": {"protein_g": targets["protein_g"]["target"],
                   "carbs_g": targets["carbs_g"]["target"],
                   "fat_g": targets["fat_g"]["target"]},
        "nutrient_targets": targets,
        "meal_budget": {
            slot: int(round(target * frac)) for slot, frac in MEAL_FRACTIONS.items()
        },
        "notes": notes,
    }
