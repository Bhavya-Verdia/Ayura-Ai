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
import './Onboarding.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

const STEPS = ['Basics', 'Physical', 'Goals & Dosha']

// Canonical Vikriti symptom clusters — unified with the Dosha Quiz and weekly
// Check-In so stored current_symptoms always match the dosha engine + yoga boosts.
const SYMPTOMS = [
  { id: 'anxiety_worry',          label: 'Anxiety or worry' },
  { id: 'trouble_sleeping',       label: 'Trouble sleeping' },
  { id: 'bloating_gas',           label: 'Bloating or gas' },
  { id: 'dry_skin_constipation',  label: 'Dryness or constipation' },
  { id: 'joint_stiffness',        label: 'Joint or body aches' },
  { id: 'heartburn_acidity',      label: 'Acidity or inflammation' },
  { id: 'irritability',           label: 'Irritability' },
  { id: 'skin_rashes',            label: 'Skin flare-ups' },
  { id: 'weight_gain',            label: 'Weight gain or heaviness' },
  { id: 'low_energy',             label: 'Low energy or fatigue' },
  { id: 'congestion',             label: 'Congestion or mucus' },
  { id: 'brain_fog',              label: 'Brain fog' },
]

const GOALS = [
  { id: 'weight_loss',     label: 'Weight Loss',      Icon: Scale },
  { id: 'muscle_gain',     label: 'Muscle Gain',       Icon: Dumbbell },
  { id: 'flexibility',     label: 'Flexibility',       Icon: PersonStanding },
  { id: 'detox',           label: 'Detox and Cleanse', Icon: FlaskConical },
  { id: 'general_wellness',label: 'General Wellness',  Icon: Sparkles },
  { id: 'balance',         label: 'Dosha Balance',     Icon: Orbit }
]

const DOSHA_INFO = {
  vata:  { Icon: Wind,  desc: 'Air & Space · Creative, energetic, variable' },
  pitta: { Icon: Flame, desc: 'Fire & Water · Sharp, intense, goal-driven' },
  kapha: { Icon: Waves, desc: 'Earth & Water · Calm, steady, nurturing' },
}

const stepVariants = {
  enter:  (d) => ({ x: d > 0 ? 60 : -60, opacity: 0, filter: 'blur(4px)' }),
  center: { x: 0, opacity: 1, filter: 'blur(0px)' },
  exit:   (d) => ({ x: d > 0 ? -60 : 60, opacity: 0, filter: 'blur(4px)' }),
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
      setError('Please enter valid age, height, and weight values.')
      return
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
        current_medications: medications
          ? medications.split(',').map(e => e.trim()).filter(Boolean)
          : [],
        goal, dominant_dosha: dosha,
        pregnancy_or_nursing: gender === 'female' ? pregnancyOrNursing : false,
        fitness_level:  fitnessLevel  || 'beginner',
        activity_level: 'moderate',
        satmya: satmya || undefined,
      })
      // Route into the real Prakriti assessment so first plans are built on an
      // assessed constitution (Vikriti, Agni, dosha %) — not just the quick pick.
      navigate('/dosha-quiz')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  function getStepValidationMessage() {
    if (step === 0) {
      if (!name)         return 'Please enter your name.'
      if (!hasValidAge)  return 'Please enter a valid age.'
      if (!gender)       return 'Please select your gender.'
    }
    if (step === 1 && !hasValidPhysicalStats) return 'Please enter valid height and weight values.'
    if (step === 2) {
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
            <img src="/favicon.svg" alt="Ayura AI Logo" className="onb-brand-mark" />
            <span className="onb-brand-text">Ayura AI</span>
          </div>
          <div className="onb-header-actions">
            <button type="button" className="onb-switch-account" onClick={handleSwitchAccount}>
              Switch Account
            </button>
          </div>
          <h2>Set up your health profile</h2>
          <p className="onb-subtitle">Step {step + 1} of {STEPS.length}: {STEPS[step]}</p>
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
                  <h3 className="onb-title">Basic Information</h3>
                  <div className="input-group">
                    <label htmlFor="onb-name">Your Name</label>
                    <input id="onb-name" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Maya" />
                  </div>
                  <div className="input-group">
                    <label htmlFor="onb-age">Age</label>
                    <input id="onb-age" type="number" value={age} onChange={e => setAge(e.target.value)} placeholder="e.g. 28" min="10" max="120" />
                  </div>
                  <div>
                    <label>What is your gender?</label>
                    <p className="onb-help">This helps with baseline calorie estimation.</p>
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
                      <label>Are you currently pregnant or nursing?</label>
                      <p className="onb-help">Important for your safety — several therapies, medicines, and poses are adjusted or excluded during this time.</p>
                      <div className="onb-grid-2">
                        {[{ v: false, l: 'No', E: Ban }, { v: true, l: 'Yes', E: Baby }].map(opt => (
                          <m.button
                            key={String(opt.v)} type="button"
                            onClick={() => setPregnancyOrNursing(opt.v)}
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
                </div>
              ) : null}

              {/* ── STEP 1: PHYSICAL ── */}
              {step === 1 ? (
                <div className="onb-stage">
                  <h3 className="onb-title">Physical Stats</h3>
                  <p className="onb-help">Used to calculate BMI and calibrate your fitness plans.</p>
                  <div className="onb-grid-2">
                    <div className="input-group">
                      <label htmlFor="onb-height">Height (cm)</label>
                      <input id="onb-height" type="number" value={height} onChange={e => setHeight(e.target.value)} placeholder="e.g. 168" min="50" max="300" />
                    </div>
                    <div className="input-group">
                      <label htmlFor="onb-weight">Weight (kg)</label>
                      <input id="onb-weight" type="number" value={weight} onChange={e => setWeight(e.target.value)} placeholder="e.g. 65" min="20" max="500" />
                    </div>
                  </div>
                  {bmi && (
                    <div className="onb-bmi">
                      <div className="onb-bmi-value">BMI {bmi}</div>
                      <p className="onb-bmi-note">
                        {parseFloat(bmi) < 18.5 ? 'Underweight' : parseFloat(bmi) < 25 ? 'Healthy weight' : parseFloat(bmi) < 30 ? 'Overweight' : 'Obese'}
                      </p>
                    </div>
                  )}
                  <div>
                    <label>Fitness Level</label>
                    <div className="onb-grid-3" style={{ marginTop: 8 }}>
                      {[
                        { id: 'beginner',  label: 'Beginner',     Icon: Sprout },
                        { id: 'intermediate', label: 'Intermediate', Icon: Dumbbell },
                        { id: 'advanced',  label: 'Advanced',     Icon: Zap },
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
                    <label>Medical Conditions (optional)</label>
                    <input
                      className="onb-condition-search"
                      type="text"
                      placeholder="Search conditions…"
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
                        Not listed? Add here (comma-separated)
                      </label>
                      <input
                        className="onb-condition-search"
                        type="text"
                        placeholder="e.g. sarcoidosis, hemophilia"
                        value={otherCondition}
                        onChange={e => setOtherCondition(e.target.value)}
                      />
                    </div>
                  </div>
                  <div>
                    <label>Current Symptoms (optional)</label>
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
                  <div className="input-group">
                    <label>How long have you followed your current diet &amp; lifestyle? (Satmya)</label>
                    <div className="onb-chip-wrap">
                      {[
                        { id: 'less_than_1y', label: 'Less than 1 year' },
                        { id: '1_to_5y', label: '1–5 years' },
                        { id: 'over_5y', label: 'More than 5 years' },
                      ].map(({ id, label }) => (
                        <button key={id} type="button"
                          onClick={() => setSatmya(id)}
                          className={`onb-chip ${satmya === id ? 'selected' : ''}`}
                        >{label}</button>
                      ))}
                    </div>
                  </div>
                  <div className="input-group">
                    <label htmlFor="onb-meds">Current Medications (comma-separated)</label>
                    <input id="onb-meds" value={medications} onChange={e => setMedications(e.target.value)} placeholder="e.g. metformin, aspirin" />
                  </div>
                </div>
              ) : null}

              {/* ── STEP 2: GOALS & DOSHA ── */}
              {step === 2 ? (
                <div className="onb-stage">
                  <h3 className="onb-title">Goals & Dosha Type</h3>
                  <div>
                    <label>Primary Wellness Goal</label>
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
                    <label>Your Dominant Dosha — a quick start</label>
                    <p className="onb-help">Just your best guess for now — right after this, a short Prakriti assessment confirms your true constitution, current imbalance (Vikriti), and Agni.</p>
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
                    <Lock size={13} strokeWidth={2} /> We take your privacy seriously — your health data is encrypted and never sold.
                  </p>
                </div>
              ) : null}
            </m.div>
          </AnimatePresence>
        </section>

        <div className="onb-nav">
          {step > 0 ? (
            <button type="button" className="btn btn-secondary" onClick={handleBack}>
              Back
            </button>
          ) : null}

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              className="btn btn-accent btn-full"
              onClick={handleContinue}
            >
              Continue →
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-accent btn-full"
              onClick={handleFinish}
              disabled={saving}
            >
              {saving ? (
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                  <span className="spinner onb-spinner" />
                  Building your profile…
                </span>
              ) : 'Complete Setup →'}
            </button>
          )}
        </div>

        <p className="onb-disclaimer">
          By continuing, you agree to our Terms of Service. Ayura AI provides wellness guidance for informational purposes only and does not replace professional medical advice.
        </p>
      </m.div>
    </div>
  )
}
