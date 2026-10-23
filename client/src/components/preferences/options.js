import { tr } from '../../lib/tr'

// Option tables for the preferences forms, and `savedToForm`, which turns a
// saved document back into each form's own shape. Several server tests read
// these lists (INJURIES, the allergy chips) against the schemas.

export const GOALS = {
  gym: [
    { value: 'fat_loss', get label() { return tr('ui.options.fatLoss', 'Fat Loss') } },
    { value: 'muscle_gain', get label() { return tr('ui.options.muscleGain', 'Muscle Gain') } },
    { value: 'endurance', get label() { return tr('ui.options.endurance', 'Endurance') } },
    { value: 'strength', get label() { return tr('ui.options.strength', 'Strength') } },
    { value: 'general_fitness', get label() { return tr('ui.options.generalFitness', 'General Fitness') } }
  ],
  yoga: [
    { value: 'flexibility', get label() { return tr('ui.options.flexibility', 'Flexibility') } },
    { value: 'stress_relief', get label() { return tr('ui.options.stressRelief', 'Stress Relief') } },
    { value: 'strength', get label() { return tr('ui.options.strength', 'Strength') } },
    { value: 'balance', get label() { return tr('ui.options.balance', 'Balance') } },
    { value: 'healing', get label() { return tr('ui.options.healing', 'Healing') } },
    { value: 'spiritual', get label() { return tr('ui.options.spiritual', 'Spiritual') } }
  ],
  diet: [
    { value: 'weight_loss', get label() { return tr('ui.options.weightLoss', 'Weight Loss') } },
    { value: 'muscle_support', get label() { return tr('ui.options.muscleSupport', 'Muscle Support') } },
    { value: 'gut_health', get label() { return tr('ui.options.gutHealth', 'Gut Health') } },
    { value: 'energy', get label() { return tr('ui.options.energy', 'Energy') } },
    { value: 'detox', get label() { return tr('ui.options.detox', 'Detox') } },
    { value: 'general_wellness', get label() { return tr('ui.options.generalWellness', 'General Wellness') } }
  ],
  routine: [
    { value: 'weight_loss', get label() { return tr('ui.options.weightLoss', 'Weight Loss') } },
    { value: 'muscle_support', get label() { return tr('ui.options.muscleSupport', 'Muscle Support') } },
    { value: 'gut_health', get label() { return tr('ui.options.gutHealth', 'Gut Health') } },
    { value: 'energy', get label() { return tr('ui.options.energy', 'Energy') } },
    { value: 'detox', get label() { return tr('ui.options.detox', 'Detox') } },
    { value: 'general_wellness', get label() { return tr('ui.options.generalWellness', 'General Wellness') } }
  ],
  panchakarma: [
    { value: 'detox', get label() { return tr('ui.options.detox', 'Detox') } },
    { value: 'rejuvenation', get label() { return tr('ui.options.rejuvenation', 'Rejuvenation') } },
    { value: 'stress_relief', get label() { return tr('ui.options.stressRelief', 'Stress Relief') } },
    { value: 'seasonal_cleanse', get label() { return tr('ui.options.seasonalCleanse', 'Seasonal Cleanse') } },
    { value: 'specific_condition', get label() { return tr('ui.options.specificCondition', 'Specific Condition') } }
  ]
};

// Three session lengths, one per experience level. A free-entry field let
// someone ask for 17 or 83 minutes, which the engine can build but nobody
// designed: the pranayama and meditation blocks are sized per level, so the
// tiers are where the practice is actually coherent.
//
// The pairing is the default, not a restriction — any level can pick any of the
// three, and the field stops being overwritten once the practitioner sets it.
// What the practitioner can actually train with. This was hardcoded to
// `['bodyweight']` for every user — the picker did not exist — so the 763
// barbell, dumbbell, machine and cable exercises in the library were unreachable
// in production no matter what gym someone had. Values must stay in step with
// the server's EQUIPMENT_OPTIONS.
export const EQUIPMENT = [
  { value: 'dumbbells',       get label() { return tr('ui.options.dumbbells', 'Dumbbells') } },
  { value: 'barbell',         get label() { return tr('ui.options.barbellPlates', 'Barbell & plates') } },
  { value: 'machines',        get label() { return tr('ui.options.resistanceMachines', 'Resistance machines') } },
  { value: 'cables',          get label() { return tr('ui.options.cableMachine', 'Cable machine') } },
  { value: 'kettlebell',      get label() { return tr('ui.options.kettlebells', 'Kettlebells') } },
  { value: 'resistance_bands', get label() { return tr('ui.options.resistanceBands', 'Resistance bands') } },
  { value: 'cardio_machines', get label() { return tr('ui.options.cardioMachines', 'Cardio machines') } },
  { value: 'jump_rope',       get label() { return tr('ui.options.jumpRope', 'Jump rope') } },
  { value: 'pool',            get label() { return tr('ui.options.pool', 'Pool') } },
];

// The set/rep scheme each goal implies, used to preselect `training_style` the
// way the yoga picker preselects a session length: the pairing is the default,
// not a restriction. General Fitness maps to nothing — its own balanced scheme is
// the answer — so it clears the field rather than borrowing another goal's.
// Keep in step with `_STYLE_SCHEME` / `_GOAL_SCHEME` in gym_plan_engine.py.
// Injuries and joint problems. The profile has had `injuries_or_limitations`
// since the start and no screen ever asked for it, so every shoulder, knee and
// wrist restriction in the exercise library was reachable by nobody. Values must
// stay in step with the server's GYM_INJURY_OPTIONS.
// Optional anchors for the load model. Without them every weight in the plan is
// inferred from bodyweight and a self-rated level — fine on average, and well off
// for any one lifter. Each one rescales the movements that share its pattern.
export const KNOWN_LIFTS = [
  { value: 'squat',          get label() { return tr('ui.options.squat', 'Squat') } },
  { value: 'deadlift',       get label() { return tr('ui.options.deadlift', 'Deadlift') } },
  { value: 'bench',          get label() { return tr('ui.options.benchPress', 'Bench press') } },
  { value: 'overhead_press', get label() { return tr('ui.options.overheadPress', 'Overhead press') } },
  { value: 'row',            get label() { return tr('ui.options.barbellOrDumbbellRow', 'Barbell or dumbbell row') } },
]

// Shared by the gym and yoga forms; both engines read the union of the two
// answers, so an injury ticked once reaches both plans.
export const INJURIES = [
  { value: 'knee',              get label() { return tr('ui.options.knee', 'Knee') } },
  { value: 'knee_replacement',  get label() { return tr('ui.options.kneeReplacement', 'Knee replacement') } },
  { value: 'lower_back',        get label() { return tr('ui.options.lowerBack', 'Lower back') } },
  { value: 'disc',              get label() { return tr('ui.options.slippedHerniatedDisc', 'Slipped / herniated disc') } },
  { value: 'shoulder',          get label() { return tr('ui.options.shoulder', 'Shoulder') } },
  { value: 'elbow',             get label() { return tr('ui.options.elbow', 'Elbow') } },
  { value: 'wrist',             get label() { return tr('ui.options.wrist', 'Wrist') } },
  { value: 'neck',              get label() { return tr('ui.options.neck', 'Neck') } },
  { value: 'hip',               get label() { return tr('ui.options.hip', 'Hip') } },
  { value: 'hip_replacement',   get label() { return tr('ui.options.hipReplacement', 'Hip replacement') } },
  { value: 'ankle',             get label() { return tr('ui.options.ankle', 'Ankle') } },
  { value: 'hernia',            get label() { return tr('ui.options.hernia', 'Hernia') } },
  { value: 'abdominal_surgery', get label() { return tr('ui.options.recentAbdominalSurgeryOrC', 'Recent abdominal surgery or C-section') } },
];

export const GYM_SUGGESTED_STYLE = {
  fat_loss:        'circuit',
  muscle_gain:     'hypertrophy',
  endurance:       'endurance',
  strength:        'strength',
  general_fitness: '',
};

export const YOGA_SESSION_MINUTES = [30, 45, 60];
export const YOGA_SUGGESTED_MINUTES = {
  none:         30,
  beginner:     30,
  intermediate: 45,
  advanced:     60,
};

// Every session carries five to ten minutes of breathwork — the engine's
// `_PRANAYAMA_MIN_MINUTES` floor over the KB's per-level rating, so a beginner
// gets five rather than the three the technique alone would give. Shown in the
// picker because the breathwork share is most of what distinguishes the tiers.
// Keep in step with `pranayama_minutes()` in yoga_plan_engine.py.
export const YOGA_PRANAYAMA_MINUTES = { none: 5, beginner: 5, intermediate: 5, advanced: 10 };

// The two the food library can actually serve. All 150 authored rows in
// diet_foods.json are vegetarian, so the 708 (condition, food) claims that gate the
// plan said nothing about any egg, fish or meat dish — a non-vegetarian meal passed
// that layer unscreened, and the rule-engine fallback answered a muscle-support goal
// with black beans. Offering a choice the data cannot honour is worse than not
// offering it. Saved preferences using the withdrawn values are coerced server-side,
// never rejected.
export const DIETARY_TYPES = [
  { value: 'vegetarian', get label() { return tr('ui.options.vegetarian', 'Vegetarian') } },
  { value: 'vegan', get label() { return tr('ui.options.vegan', 'Vegan') } }
];

// Saved preferences in the shape the form edits them. The form keeps a few
// answers as comma-separated text and a few as a single choice the schema stores
// as a list; each is undone here so the saved answer shows, and so submitting it
// unchanged writes back what was there.
export const joinList = (v) => (Array.isArray(v) ? v.join(', ') : (v || ''));

export function savedToForm(typeId, saved) {
  const form = { ...saved };
  if (typeId === 'gym') {
    form.available_equipment = (saved.available_equipment || []).filter(e => e !== 'bodyweight');
    form.likes = joinList(saved.exercise_preferences?.likes);
    form.dislikes = joinList(saved.exercise_preferences?.dislikes);
    delete form.exercise_preferences;
    form.training_style = saved.training_style || '';
    form.known_lifts = saved.known_lifts || {};
  } else if (typeId === 'yoga') {
    const style = saved.yoga_style_preference;
    form.yoga_style_preference = Array.isArray(style) ? (style[0] || '') : (style || '');
    if (saved.time_available_minutes) form.time_available_minutes = String(saved.time_available_minutes);
  } else if (typeId === 'diet' || typeId === 'routine') {
    form.fasting_days = joinList(saved.fasting_days);
    if (typeId === 'diet') form.food_dislikes = joinList(saved.food_dislikes);
  } else if (typeId === 'panchakarma') {
    form.current_ayurvedic_medicines = joinList(saved.current_ayurvedic_medicines);
  } else if (typeId === 'remedies' || typeId === 'medicines') {
    form.previous_ayurvedic_medicines = joinList(saved.previous_ayurvedic_medicines);
    form.current_ayurvedic_medicines = joinList(saved.current_ayurvedic_medicines);
  }
  // A select bound to null shows nothing and submits nothing; '' is the same
  // answer in the form's terms.
  Object.keys(form).forEach(k => { if (form[k] === null) delete form[k]; });
  return form;
}
