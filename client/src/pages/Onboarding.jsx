import { useState, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, m } from 'framer-motion'
import { useAuth } from '../providers/AuthContext'
import {
  Scale, Dumbbell, PersonStanding, FlaskConical, Sparkles, Orbit,
  Wind, Flame, Waves, Mars, Venus, Transgender, Ban, Baby, Sprout, Zap, Lock,
} from 'lucide-react'
import React from 'react'
import { CONDITION_CATEGORIES } from '../constants/conditions'
import { track, EVENTS } from '../lib/analytics'
import { reportError } from '../lib/errorReporting'
import { tr } from '../lib/tr'
import { Trans } from 'react-i18next'
import './Onboarding.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

const STEPS = ['Basics', 'Physical', 'Goals & Dosha']

// Canonical Vikriti symptom clusters — unified with the Dosha Quiz and weekly
// Check-In so stored current_symptoms always match the dosha engine + yoga boosts.
// The canonical keys of `FOOD_ALLERGIES` in preferences_schema, which is also what
// `ALLERGEN_TERMS` in ahara_safety expands. One vocabulary, so an allergy declared
// here is enforceable everywhere rather than being a free-text string that substring
// matching cannot see through.
const FOOD_ALLERGIES = [
  { id: 'dairy',      get label() { return tr('ui.onboarding.dairy', 'Dairy') } },
  { id: 'gluten',     get label() { return tr('ui.onboarding.glutenWheat', 'Gluten / wheat') } },
  { id: 'nuts_tree',  get label() { return tr('ui.onboarding.treeNuts', 'Tree nuts') } },
  { id: 'peanuts',    get label() { return tr('ui.onboarding.peanuts', 'Peanuts') } },
  { id: 'soy',        get label() { return tr('ui.onboarding.soy', 'Soy') } },
  { id: 'eggs',       get label() { return tr('ui.onboarding.eggs', 'Eggs') } },
  { id: 'fish',       get label() { return tr('ui.onboarding.fish', 'Fish') } },
  { id: 'shellfish',  get label() { return tr('ui.onboarding.shellfish', 'Shellfish') } },
  { id: 'sesame',     get label() { return tr('ui.onboarding.sesame', 'Sesame') } },
  { id: 'mustard',    get label() { return tr('ui.onboarding.mustard', 'Mustard') } },
]

const SYMPTOMS = [
  { id: 'anxiety_worry',          get label() { return tr('ui.onboarding.anxietyOrWorry', 'Anxiety or worry') } },
  { id: 'trouble_sleeping',       get label() { return tr('ui.onboarding.troubleSleeping', 'Trouble sleeping') } },
  { id: 'bloating_gas',           get label() { return tr('ui.onboarding.bloatingOrGas', 'Bloating or gas') } },
  { id: 'dry_skin_constipation',  get label() { return tr('ui.onboarding.drynessOrConstipation', 'Dryness or constipation') } },
  { id: 'joint_stiffness',        get label() { return tr('ui.onboarding.jointOrBodyAches', 'Joint or body aches') } },
  { id: 'heartburn_acidity',      get label() { return tr('ui.onboarding.acidityOrInflammation', 'Acidity or inflammation') } },
  { id: 'irritability',           get label() { return tr('ui.onboarding.irritability', 'Irritability') } },
  { id: 'skin_rashes',            get label() { return tr('ui.onboarding.skinFlareUps', 'Skin flare-ups') } },
  { id: 'weight_gain',            get label() { return tr('ui.onboarding.weightGainOrHeaviness', 'Weight gain or heaviness') } },
  { id: 'low_energy',             get label() { return tr('ui.onboarding.lowEnergyOrFatigue', 'Low energy or fatigue') } },
  { id: 'congestion',             get label() { return tr('ui.onboarding.congestionOrMucus', 'Congestion or mucus') } },
  { id: 'brain_fog',              get label() { return tr('ui.onboarding.brainFog', 'Brain fog') } },
]

const GOALS = [
  { id: 'weight_loss',     get label() { return tr('ui.onboarding.weightLoss', 'Weight Loss') },      Icon: Scale },
  { id: 'muscle_gain',     get label() { return tr('ui.onboarding.muscleGain', 'Muscle Gain') },       Icon: Dumbbell },
  { id: 'flexibility',     get label() { return tr('ui.onboarding.flexibility', 'Flexibility') },       Icon: PersonStanding },
  { id: 'detox',           get label() { return tr('ui.onboarding.detoxAndCleanse', 'Detox and Cleanse') }, Icon: FlaskConical },
  { id: 'general_wellness',get label() { return tr('ui.onboarding.generalWellness', 'General Wellness') },  Icon: Sparkles },
  { id: 'balance',         get label() { return tr('ui.onboarding.doshaBalance', 'Dosha Balance') },     Icon: Orbit }
]

const DOSHA_INFO = {
  vata:  { Icon: Wind,  get desc() { return tr('ui.onboarding.airSpaceCreativeEnergeticVariable', 'Air & Space · Creative, energetic, variable') } },
  pitta: { Icon: Flame, get desc() { return tr('ui.onboarding.fireWaterSharpIntenseGoal', 'Fire & Water · Sharp, intense, goal-driven') } },
  kapha: { Icon: Waves, get desc() { return tr('ui.onboarding.earthWaterCalmSteadyNurturing', 'Earth & Water · Calm, steady, nurturing') } },
}

// NO filter/blur in step transitions — a lingering blur(0px) keeps the step
// in a filtered render surface forever, which flashes empty on invalidation.
const stepVariants = {
  enter:  (d) => ({ x: d > 0 ? 60 : -60, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit:   (d) => ({ x: d > 0 ? -60 : 60, opacity: 0 }),
}

export default function Onboarding() {
  const [step, setStep]           = useState(0)
  const [direction, setDirection] = useState(1)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')
  const { updateProfile, logout } = useAuth()
  const navigate                  = useNavigate()

  const [name, setName]                   = useState('')
  const [gender, setGender]               = useState('')
  const [pregnancyOrNursing, setPregnancyOrNursing] = useState(false)
  // Pregnancy and nursing restrict practice very differently, and the trimester
  // changes it again — so we ask which, rather than filtering everyone who
  // answers "yes" as though they were in the third trimester.
  const [pregnancyStatus, setPregnancyStatus]       = useState('')
  const [pregnancyTrimester, setPregnancyTrimester] = useState('')
  const [age, setAge]                     = useState('')
  const [height, setHeight]               = useState('')
  const [weight, setWeight]               = useState('')
  const [conditions, setConditions]       = useState([])
  const [conditionSearch, setConditionSearch] = useState('')
  const [otherCondition, setOtherCondition]   = useState('')
  const [satmya, setSatmya]               = useState('')
  const [symptoms, setSymptoms]           = useState([])
  const [medications, setMedications]     = useState('')
  const [fitnessLevel, setFitnessLevel]   = useState('')
  // How much the patient MOVES, which is a different question from how trained they
  // are. It was hardcoded to 'moderate' below and is the largest single lever in the
  // diet plan: same body, same goal, the target runs 2040 kcal at `sedentary` and
  // 3220 at `very_active`. A sedentary desk worker was being prescribed 2630.
  const [activityLevel, setActivityLevel] = useState('')
  // Read by the remedies safety filter, the chat agent's system prompt and the Vaidya
  // PDF export — and collected by no screen, so it was null for every user in
  // production and none of those three had ever seen one.
  const [allergies, setAllergies] = useState([])
  const [goal, setGoal]                   = useState('')
  const [dosha, setDosha]                 = useState('')

  function toggleItem(list, setList, item) {
    setList(prev => prev.includes(item) ? prev.filter(e => e !== item) : [...prev, item])
  }

  const parsedAge    = Number.parseInt(age, 10)
  const parsedHeight = Number.parseFloat(height)
  const parsedWeight = Number.parseFloat(weight)
  const hasValidAge  = Number.isFinite(parsedAge)    && parsedAge    >= 10  && parsedAge    <= 120
  const hasValidPhysicalStats =
    Number.isFinite(parsedHeight) && parsedHeight >= 50  && parsedHeight <= 300 &&
    Number.isFinite(parsedWeight) && parsedWeight >= 20  && parsedWeight <= 500

  const bmi = hasValidPhysicalStats
    ? (parsedWeight / ((parsedHeight / 100) ** 2)).toFixed(1)
    : null

  async function handleFinish() {
    setError('')
    if (!hasValidPhysicalStats || !hasValidAge) {
      setError(tr('ui.onboarding.pleaseEnterValidAgeHeight', 'Please enter valid age, height, and weight values.'))
      return
    }
    // The per-step rules are enforced by "Continue" — which the LAST step never
    // shows, so goal and dosha were the only required answers nothing checked.
    // Unanswered, they went to the API as "" and failed its enum patterns: a 422
    // that saved nothing and (before the detail flattening in api/client.js) blew
    // the page away. Run the same rules here before sending anything.
    for (const s of STEPS.keys()) {
      const stepMsg = getStepValidationMessage(s)
      if (stepMsg) {
        setError(stepMsg)
        setDirection(s > step ? 1 : -1)
        setStep(s)
        return
      }
    }
    setSaving(true)
    try {
      await updateProfile({
        name, gender, age: parsedAge, height_cm: parsedHeight, weight_kg: parsedWeight,
        medical_history: [
          ...conditions,
          ...otherCondition.split(',').map(s => s.trim().toLowerCase().replace(/\s+/g, '_')).filter(Boolean),
        ],
        current_symptoms: symptoms,
        allergies,
        current_medications: medications
          ? medications.split(',').map(e => e.trim()).filter(Boolean)
          : [],
        // Omit rather than send "" — every one of these is an optional field with
        // a strict enum pattern server-side, where an empty string is a 422, not
        // a "not answered".
        goal: goal || undefined,
        dominant_dosha: dosha || undefined,
        pregnancy_or_nursing: gender === 'female' ? pregnancyOrNursing : false,
        pregnancy_status: gender === 'female' && pregnancyOrNursing
          ? (pregnancyStatus || undefined) : undefined,
        pregnancy_trimester: gender === 'female' && pregnancyStatus === 'pregnant'
          ? (Number(pregnancyTrimester) || undefined) : undefined,
        fitness_level:  fitnessLevel  || 'beginner',
        activity_level: activityLevel || 'moderate',
        satmya: satmya || undefined,
        // Device IANA timezone — lets the backend seed the default morning
        // reminder at the user's local 07:00 (and future local-time features).
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || undefined,
      })
      // Counts only — never the conditions, symptoms or dosha themselves.
      // This is the launch drop-off question: how many who start onboarding
      // actually reach the assessment.
      track(EVENTS.ONBOARDING_COMPLETED, {
        condition_count: conditions.length,
        symptom_count: symptoms.length,
        has_goal: Boolean(goal),
      })
      // Route into the real Prakriti assessment so first plans are built on an
      // assessed constitution (Vikriti, Agni, dosha %) — not just the quick pick.
      navigate('/dosha-quiz')
    } catch (err) {
      const detail = err.response?.data?.detail
      // Every signup from 2026-09-22 to 2026-10-18 stalled on this form, and
      // nothing recorded what they were shown, so the cause could not be found.
      // Status and the server's own message only — never an answer on the form.
      reportError(err, {
        flow: 'onboarding',
        extra: {
          status: err.response?.status ?? 'network',
          detail: typeof detail === 'string' ? detail.slice(0, 300) : null,
          step,
        },
        noReplay: true,
      })
      setError(detail || 'Failed to save profile. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  function getStepValidationMessage(which = step) {
    if (which === 0) {
      if (!name)         return 'Please enter your name.'
      if (!hasValidAge)  return 'Please enter a valid age.'
      if (!gender)       return 'Please select your gender.'
    }
    if (which === 1) {
      if (!hasValidPhysicalStats) return 'Please enter valid height and weight values.'
      // Asked rather than assumed: it sets the calorie target the diet plan calls
      // "a clinical target, not a suggestion".
      if (!activityLevel) return 'Please choose how active your usual week is.'
    }
    if (which === 2) {
      if (!goal)  return 'Please choose your primary wellness goal.'
      if (!dosha) return 'Please select your dosha.'
    }
    return ''
  }

  async function handleContinue() {
    const msg = getStepValidationMessage()
    if (msg) { setError(msg); return }
    setError('')
    setDirection(1)
    setStep(prev => prev + 1)
  }

  function handleBack() {
    setDirection(-1)
    setStep(prev => prev - 1)
  }

  function handleSwitchAccount() { logout(); navigate('/login') }

  return (
    <div className="onb-page" data-step={step}>
      <Suspense fallback={null}>
        <LazyParticleField count={300} spread={25} style={{ opacity: 0.35 }} />
      </Suspense>

      <div className="onb-orb onb-orb-a" />
      <div className="onb-orb onb-orb-b" />

      <m.div
        className="onb-shell"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        <header className="onb-header">
          <div className="onb-brand">
            <img src="/favicon.svg" alt="" className="onb-brand-mark" />
            <span className="onb-brand-text">{tr('ui.onboarding.ayuraAi', 'Ayura AI')}</span>
          </div>
          <div className="onb-header-actions">
            <button type="button" className="onb-switch-account" onClick={handleSwitchAccount}>
              {tr('ui.onboarding.switchAccount', 'Switch Account')}
            </button>
          </div>
          <h1>{tr('ui.onboarding.setUpYourHealthProfile', 'Set up your health profile')}</h1>
          <p className="onb-subtitle"><Trans i18nKey="ui.onboarding.stepOf" defaults={"Step {{value}} of {{length}}: {{step}}"} values={{ value: step + 1, length: STEPS.length, step: STEPS[step] }} /></p>
        </header>

        <div className="onb-steps">
          {STEPS.map((label, index) => (
            <m.div
              key={label}
              className={`onb-step ${index === step ? 'active' : ''} ${index < step ? 'done' : ''}`}
              title={label}
              animate={index === step ? { scale: [1, 1.2, 1] } : {}}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          ))}
        </div>

        <div className="onb-progress-track">
          <m.div
            className="onb-progress-fill"
            animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        <section className="onb-card">
          <AnimatePresence mode="wait">
            {error ? (
              <m.div
                className="onb-error"
                key="error"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                {error}
              </m.div>
            ) : null}
          </AnimatePresence>

          <AnimatePresence mode="wait" custom={direction}>
            <m.div
              key={step}
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
            >
              {/* ── STEP 0: BASICS ── */}
              {step === 0 ? (
                <div className="onb-stage">
                  <h3 className="onb-title">{tr('ui.onboarding.basicInformation', 'Basic Information')}</h3>
                  <div className="input-group">
                    <label htmlFor="onb-name">{tr('ui.onboarding.yourName', 'Your Name')}</label>
                    <input id="onb-name" value={name} onChange={e => setName(e.target.value)} placeholder={tr('ui.onboarding.eGMaya', 'e.g. Maya')} />
                  </div>
                  <div className="input-group">
                    <label htmlFor="onb-age">{tr('ui.onboarding.age', 'Age')}</label>
                    <input id="onb-age" type="number" value={age} onChange={e => setAge(e.target.value)} placeholder="e.g. 28" min="10" max="120" />
                  </div>
                  <div>
                    <label>{tr('ui.onboarding.whatIsYourGender', 'What is your gender?')}</label>
                    <p className="onb-help">{tr('ui.onboarding.thisHelpsWithBaselineCalorie', 'This helps with baseline calorie estimation.')}</p>
                    <div className="onb-grid-3">
                      {['male', 'female', 'other'].map(entry => (
                        <m.button
                          key={entry} type="button"
                          onClick={() => setGender(entry)}
                          className={`onb-tile ${gender === entry ? 'selected' : ''}`}
                          whileTap={{ scale: 0.95 }}
                        >
                          <span className="onb-tile-emoji">
                            {entry === 'male' ? <Mars size={22} strokeWidth={2} /> : entry === 'female' ? <Venus size={22} strokeWidth={2} /> : <Transgender size={22} strokeWidth={2} />}
                          </span>
                          {entry.charAt(0).toUpperCase() + entry.slice(1)}
                        </m.button>
                      ))}
                    </div>
                  </div>

                  {gender === 'female' && (
                    <div className="input-group">
                      <label>{tr('ui.onboarding.areYouCurrentlyPregnantOr', 'Are you currently pregnant or nursing?')}</label>
                      <p className="onb-help">{tr('ui.onboarding.importantForYourSafetySeveral', 'Important for your safety — several therapies, medicines, and poses are adjusted or excluded during this time.')}</p>
                      <div className="onb-grid-2">
                        {[{ v: false, l: 'No', E: Ban }, { v: true, l: 'Yes', E: Baby }].map(opt => (
                          <m.button
                            key={String(opt.v)} type="button"
                            onClick={() => {
                              setPregnancyOrNursing(opt.v)
                              if (!opt.v) { setPregnancyStatus(''); setPregnancyTrimester('') }
                            }}
                            className={`onb-tile ${pregnancyOrNursing === opt.v ? 'selected' : ''}`}
                            whileTap={{ scale: 0.95 }}
                          >
                            <span className="onb-tile-emoji"><opt.E size={22} strokeWidth={2} /></span>
                            {opt.l}
                          </m.button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Which of the two, and how far along. Pregnancy and nursing
                      restrict practice very differently, and each trimester
                      differs again — without this we have to assume the most
                      restrictive case for everyone who answered yes. */}
                  {gender === 'female' && pregnancyOrNursing && (
                    <div className="input-group">
                      <label>{tr('ui.onboarding.whichAppliesToYou', 'Which applies to you?')}</label>
                      <p className="onb-help">{tr('ui.onboarding.nursingCarriesAlmostNoRestrictions', 'Nursing carries almost no restrictions on yoga. Pregnancy changes what is safe considerably, and it changes again each trimester.')}</p>
                      <div className="onb-grid-2">
                        {[{ v: 'pregnant', l: 'Pregnant' }, { v: 'nursing', l: 'Nursing' }].map(opt => (
                          <m.button
                            key={opt.v} type="button"
                            onClick={() => {
                              setPregnancyStatus(opt.v)
                              if (opt.v !== 'pregnant') setPregnancyTrimester('')
                            }}
                            className={`onb-tile ${pregnancyStatus === opt.v ? 'selected' : ''}`}
                            whileTap={{ scale: 0.95 }}
                          >
                            {opt.l}
                          </m.button>
                        ))}
                      </div>
                    </div>
                  )}

                  {gender === 'female' && pregnancyStatus === 'pregnant' && (
                    <div className="input-group">
                      <label>{tr('ui.onboarding.whichTrimester', 'Which trimester?')}</label>
                      <p className="onb-help">{tr('ui.onboarding.ifYouWouldRatherNot', 'If you would rather not say, we will plan for the third trimester, which is the most cautious.')}</p>
                      <div className="onb-grid-3">
                        {[{ v: '1', l: 'First' }, { v: '2', l: 'Second' }, { v: '3', l: 'Third' }].map(opt => (
                          <m.button
                            key={opt.v} type="button"
                            onClick={() => setPregnancyTrimester(opt.v)}
                            className={`onb-tile ${pregnancyTrimester === opt.v ? 'selected' : ''}`}
                            whileTap={{ scale: 0.95 }}
                          >
                            {opt.l}
                          </m.button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}

              {/* ── STEP 1: PHYSICAL ── */}
              {step === 1 ? (
                <div className="onb-stage">
                  <h3 className="onb-title">{tr('ui.onboarding.physicalStats', 'Physical Stats')}</h3>
                  <p className="onb-help">{tr('ui.onboarding.usedToCalculateBmiAnd', 'Used to calculate BMI and calibrate your fitness plans.')}</p>
                  <div className="onb-grid-2">
                    <div className="input-group">
                      <label htmlFor="onb-height">{tr('ui.onboarding.heightCm', 'Height (cm)')}</label>
                      <input id="onb-height" type="number" value={height} onChange={e => setHeight(e.target.value)} placeholder="e.g. 168" min="50" max="300" />
                    </div>
                    <div className="input-group">
                      <label htmlFor="onb-weight">{tr('ui.onboarding.weightKg', 'Weight (kg)')}</label>
                      <input id="onb-weight" type="number" value={weight} onChange={e => setWeight(e.target.value)} placeholder="e.g. 65" min="20" max="500" />
                    </div>
                  </div>
                  {bmi && (
                    <div className="onb-bmi">
                      <div className="onb-bmi-value">BMI {bmi}</div>
                      <p className="onb-bmi-note">
                        {parseFloat(bmi) < 18.5 ? tr('ui.onboarding.underweight', 'Underweight') : parseFloat(bmi) < 25 ? tr('ui.onboarding.healthyWeight', 'Healthy weight') : parseFloat(bmi) < 30 ? tr('ui.onboarding.overweight', 'Overweight') : tr('ui.onboarding.obese', 'Obese')}
                      </p>
                    </div>
                  )}
                  <div>
                    <label>{tr('ui.onboarding.fitnessLevel', 'Fitness Level')}</label>
                    <div className="onb-grid-3" style={{ marginTop: 8 }}>
                      {[
                        { id: 'beginner',  label: tr('ui.onboarding.beginner', 'Beginner'),     Icon: Sprout },
                        { id: 'intermediate', label: tr('ui.onboarding.intermediate', 'Intermediate'), Icon: Dumbbell },
                        { id: 'advanced',  label: tr('ui.onboarding.advanced', 'Advanced'),     Icon: Zap },
                      ].map(f => (
                        <m.button
                          key={f.id} type="button"
                          onClick={() => setFitnessLevel(f.id)}
                          className={`onb-tile ${fitnessLevel === f.id ? 'selected' : ''}`}
                          whileTap={{ scale: 0.95 }}
                        >
                          <span className="onb-tile-emoji"><f.Icon size={22} strokeWidth={2} /></span>
                          {f.label}
                        </m.button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label>{tr('ui.onboarding.howActiveIsYourUsual', 'How active is your usual week?')}</label>
                    <p className="onb-field-note">
                      {tr('ui.onboarding.notHowFitYouAre', 'Not how fit you are — how much you move. This sets your daily calorie target.')}
                    </p>
                    <div className="onb-grid-3" style={{ marginTop: 8 }}>
                      {[
                        { id: 'sedentary',   label: tr('ui.onboarding.deskBound', 'Desk-bound'),  note: tr('ui.onboarding.littleOrNoExercise', 'little or no exercise') },
                        { id: 'light',       label: tr('ui.onboarding.light', 'Light'),       note: tr('ui.onboarding.n12DaysAWeek', '1–2 days a week') },
                        { id: 'moderate',    label: tr('ui.onboarding.moderate', 'Moderate'),    note: tr('ui.onboarding.n35DaysAWeek', '3–5 days a week') },
                        { id: 'active',      label: tr('ui.onboarding.active', 'Active'),      note: tr('ui.onboarding.n67DaysAWeek', '6–7 days a week') },
                        { id: 'very_active', label: tr('ui.onboarding.veryActive', 'Very active'),  note: tr('ui.onboarding.physicalJobOrTwiceDaily', 'physical job or twice daily') },
                      ].map(a => (
                        <m.button
                          key={a.id} type="button"
                          onClick={() => setActivityLevel(a.id)}
                          className={`onb-tile ${activityLevel === a.id ? 'selected' : ''}`}
                          whileTap={{ scale: 0.95 }}
                        >
                          {a.label}
                          <span className="onb-tile-note">{a.note}</span>
                        </m.button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label>{tr('ui.onboarding.medicalConditionsOptional', 'Medical Conditions (optional)')}</label>
                    <input
                      className="onb-condition-search"
                      type="text"
                      placeholder={tr('ui.onboarding.searchConditions', 'Search conditions…')}
                      value={conditionSearch}
                      onChange={e => setConditionSearch(e.target.value)}
                    />
                    {CONDITION_CATEGORIES.map(cat => {
                      const q = conditionSearch.trim().toLowerCase()
                      const visible = q
                        ? cat.items.filter(({ label }) => label.toLowerCase().includes(q))
                        : cat.items
                      if (visible.length === 0) return null
                      return (
                        <div key={cat.label} className="onb-condition-category">
                          <span className="onb-condition-cat-label">{cat.label}</span>
                          <div className="onb-chip-wrap">
                            {visible.map(({ id, label }) => (
                              <button
                                key={id} type="button"
                                onClick={() => toggleItem(conditions, setConditions, id)}
                                className={`onb-chip ${conditions.includes(id) ? 'selected' : ''}`}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                    <div className="onb-other-condition">
                      <label className="onb-condition-cat-label" style={{ marginTop: 10 }}>
                        {tr('ui.onboarding.notListedAddHereComma', 'Not listed? Add here (comma-separated)')}
                      </label>
                      <input
                        className="onb-condition-search"
                        type="text"
                        placeholder={tr('ui.onboarding.eGSarcoidosisHemophilia', 'e.g. sarcoidosis, hemophilia')}
                        value={otherCondition}
                        onChange={e => setOtherCondition(e.target.value)}
                      />
                    </div>
                  </div>
                  <div>
                    <label>{tr('ui.onboarding.currentSymptomsOptional', 'Current Symptoms (optional)')}</label>
                    <div className="onb-chip-wrap">
                      {SYMPTOMS.map(({ id, label }) => (
                        <button
                          key={id} type="button"
                          onClick={() => toggleItem(symptoms, setSymptoms, id)}
                          className={`onb-chip ${symptoms.includes(id) ? 'selected' : ''}`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label>{tr('ui.onboarding.foodAllergiesOptional', 'Food Allergies (optional)')}</label>
                    <p className="onb-field-note">
                      {tr('ui.onboarding.theseAreWithheldFromEvery', 'These are withheld from every meal, remedy and recommendation we generate for you.')}
                    </p>
                    <div className="onb-chip-wrap">
                      {FOOD_ALLERGIES.map(({ id, label }) => (
                        <button
                          key={id} type="button"
                          onClick={() => toggleItem(allergies, setAllergies, id)}
                          className={`onb-chip ${allergies.includes(id) ? 'selected' : ''}`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="input-group">
                    <label>{tr('ui.onboarding.howLongHaveYouFollowed', 'How long have you followed your current diet & lifestyle? (Satmya)')}</label>
                    <div className="onb-chip-wrap">
                      {[
                        { id: 'less_than_1y', label: tr('ui.onboarding.lessThan1Year', 'Less than 1 year') },
                        { id: '1_to_5y', label: tr('ui.onboarding.n15Years', '1–5 years') },
                        { id: 'over_5y', label: tr('ui.onboarding.moreThan5Years', 'More than 5 years') },
                      ].map(({ id, label }) => (
                        <button key={id} type="button"
                          onClick={() => setSatmya(id)}
                          className={`onb-chip ${satmya === id ? 'selected' : ''}`}
                        >{label}</button>
                      ))}
                    </div>
                  </div>
                  <div className="input-group">
                    <label htmlFor="onb-meds">{tr('ui.onboarding.currentMedicationsCommaSeparated', 'Current Medications (comma-separated)')}</label>
                    <input id="onb-meds" value={medications} onChange={e => setMedications(e.target.value)} placeholder={tr('ui.onboarding.eGMetforminAspirin', 'e.g. metformin, aspirin')} />
                  </div>
                </div>
              ) : null}

              {/* ── STEP 2: GOALS & DOSHA ── */}
              {step === 2 ? (
                <div className="onb-stage">
                  <h3 className="onb-title">{tr('ui.onboarding.goalsDoshaType', 'Goals & Dosha Type')}</h3>
                  <div>
                    <label>{tr('ui.onboarding.primaryWellnessGoal', 'Primary Wellness Goal')}</label>
                    <div className="onb-grid-2" style={{ marginTop: 10 }}>
                      {GOALS.map(g => (
                        <m.button
                          key={g.id} type="button"
                          onClick={() => setGoal(g.id)}
                          className={`onb-tile ${goal === g.id ? 'selected' : ''}`}
                          whileTap={{ scale: 0.94 }}
                          whileHover={{ scale: 1.02 }}
                          animate={goal === g.id ? { scale: [1, 1.06, 1] } : { scale: 1 }}
                          transition={{ type: 'spring', stiffness: 420, damping: 22 }}
                        >
                          <span className="onb-tile-emoji"><g.Icon size={22} strokeWidth={2} /></span>
                          {g.label}
                        </m.button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label>{tr('ui.onboarding.yourDominantDoshaAQuick', 'Your Dominant Dosha — a quick start')}</label>
                    <p className="onb-help">{tr('ui.onboarding.justYourBestGuessFor', 'Just your best guess for now — right after this, a short Prakriti assessment confirms your true constitution, current imbalance (Vikriti), and Agni.')}</p>
                    <div className="onb-grid-3" style={{ marginTop: 10 }}>
                      {Object.entries(DOSHA_INFO).map(([key, info]) => (
                        <m.button
                          key={key} type="button"
                          onClick={() => setDosha(key)}
                          className={`onb-tile ${dosha === key ? 'selected' : ''}`}
                          whileTap={{ scale: 0.94 }}
                          whileHover={{ scale: 1.02 }}
                          animate={dosha === key ? { scale: [1, 1.07, 1] } : { scale: 1 }}
                          transition={{ type: 'spring', stiffness: 420, damping: 22 }}
                        >
                          <span className="onb-tile-emoji"><info.Icon size={22} strokeWidth={2} /></span>
                          {key.charAt(0).toUpperCase() + key.slice(1)}
                          <span className="onb-tile-desc">{info.desc}</span>
                        </m.button>
                      ))}
                    </div>
                  </div>
                  <p className="onb-help" style={{ fontSize: '0.78rem', marginTop: 4, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <Lock size={13} strokeWidth={2} />{' '}{tr('ui.onboarding.weTakeYourPrivacySeriously', 'We take your privacy seriously — your health data is encrypted and never sold.')}
                  </p>
                </div>
              ) : null}
            </m.div>
          </AnimatePresence>
        </section>

        <div className="onb-nav">
          {step > 0 ? (
            <button type="button" className="btn btn-secondary" onClick={handleBack}>
              {tr('ui.onboarding.back', 'Back')}
            </button>
          ) : null}

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              className="btn btn-accent btn-full"
              onClick={handleContinue}
            >
              {tr('ui.onboarding.continue', 'Continue →')}
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-accent btn-full"
              onClick={handleFinish}
              disabled={saving}
            >
              {saving ? (
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}><Trans i18nKey="ui.onboarding.n0BuildingYourProfile" defaults={"<0/> Building your profile…"} components={[<span className="spinner onb-spinner" />]} /></span>
              ) : tr('ui.onboarding.completeSetup', 'Complete Setup →')}
            </button>
          )}
        </div>

        <p className="onb-disclaimer">
          {tr('ui.onboarding.byContinuingYouAgreeTo', 'By continuing, you agree to our Terms of Service. Ayura AI provides wellness guidance for informational purposes only and does not replace professional medical advice.')}
        </p>
      </m.div>
    </div>
  )
}
