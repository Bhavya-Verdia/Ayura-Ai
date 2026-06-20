import { useState, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useAuth } from '../providers/AuthContext'
import React from 'react'
import './Onboarding.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

const STEPS = ['Basics', 'Physical', 'Goals & Dosha']

const CONDITION_CATEGORIES = [
  {
    label: 'Musculoskeletal',
    items: [
      { id: 'arthritis', label: 'Arthritis' },
      { id: 'osteoarthritis', label: 'Osteoarthritis' },
      { id: 'rheumatoid_arthritis', label: 'Rheumatoid Arthritis' },
      { id: 'ankylosing_spondylitis', label: 'Ankylosing Spondylitis' },
      { id: 'gout', label: 'Gout' },
      { id: 'fibromyalgia', label: 'Fibromyalgia' },
      { id: 'osteoporosis', label: 'Osteoporosis' },
      { id: 'sciatica', label: 'Sciatica' },
      { id: 'cervical_spondylosis', label: 'Cervical Spondylosis' },
      { id: 'lumbar_spondylosis', label: 'Lumbar Spondylosis' },
    ],
  },
  {
    label: 'Neurological',
    items: [
      { id: 'migraine', label: 'Migraine' },
      { id: 'epilepsy', label: 'Epilepsy' },
      { id: 'parkinson', label: "Parkinson's" },
      { id: 'multiple_sclerosis', label: 'Multiple Sclerosis' },
      { id: 'tinnitus', label: 'Tinnitus' },
      { id: 'vertigo', label: 'Vertigo' },
      { id: 'chronic_fatigue_syndrome', label: 'Chronic Fatigue' },
      { id: 'peripheral_neuropathy', label: 'Peripheral Neuropathy' },
    ],
  },
  {
    label: 'Mental Health',
    items: [
      { id: 'anxiety', label: 'Anxiety Disorder' },
      { id: 'depression', label: 'Depression' },
      { id: 'bipolar', label: 'Bipolar Disorder' },
      { id: 'ocd', label: 'OCD' },
      { id: 'ptsd', label: 'PTSD' },
      { id: 'adhd', label: 'ADHD' },
      { id: 'insomnia', label: 'Chronic Insomnia' },
    ],
  },
  {
    label: 'Cardiovascular',
    items: [
      { id: 'hypertension', label: 'Hypertension' },
      { id: 'heart_disease', label: 'Heart Disease' },
      { id: 'atrial_fibrillation', label: 'Atrial Fibrillation' },
      { id: 'anemia', label: 'Anaemia' },
      { id: 'varicose_veins', label: 'Varicose Veins' },
      { id: 'low_blood_pressure', label: 'Low Blood Pressure' },
    ],
  },
  {
    label: 'Respiratory',
    items: [
      { id: 'asthma', label: 'Asthma' },
      { id: 'copd', label: 'COPD' },
      { id: 'allergic_rhinitis', label: 'Allergic Rhinitis' },
      { id: 'sinusitis', label: 'Chronic Sinusitis' },
      { id: 'sleep_apnea', label: 'Sleep Apnea' },
      { id: 'chronic_bronchitis', label: 'Chronic Bronchitis' },
    ],
  },
  {
    label: 'Digestive',
    items: [
      { id: 'acid_reflux', label: 'Acid Reflux / GERD' },
      { id: 'ibs', label: 'IBS' },
      { id: 'ibd_crohns', label: "Crohn's Disease" },
      { id: 'ulcerative_colitis', label: 'Ulcerative Colitis' },
      { id: 'fatty_liver', label: 'Fatty Liver' },
      { id: 'gallstones', label: 'Gallstones' },
      { id: 'constipation_chronic', label: 'Chronic Constipation' },
      { id: 'celiac', label: 'Celiac Disease' },
      { id: 'hemorrhoids', label: 'Haemorrhoids' },
    ],
  },
  {
    label: 'Endocrine & Metabolic',
    items: [
      { id: 'diabetes_type2', label: 'Type 2 Diabetes' },
      { id: 'diabetes_type1', label: 'Type 1 Diabetes' },
      { id: 'hypothyroidism', label: 'Hypothyroidism' },
      { id: 'hyperthyroidism', label: 'Hyperthyroidism' },
      { id: 'pcos', label: 'PCOS' },
      { id: 'high_cholesterol', label: 'High Cholesterol' },
      { id: 'obesity', label: 'Obesity (BMI > 30)' },
      { id: 'metabolic_syndrome', label: 'Metabolic Syndrome' },
      { id: 'hashimoto', label: "Hashimoto's Thyroiditis" },
    ],
  },
  {
    label: 'Skin',
    items: [
      { id: 'psoriasis', label: 'Psoriasis' },
      { id: 'eczema', label: 'Eczema' },
      { id: 'acne_severe', label: 'Severe Acne' },
      { id: 'vitiligo', label: 'Vitiligo' },
      { id: 'rosacea', label: 'Rosacea' },
      { id: 'urticaria', label: 'Urticaria / Hives' },
      { id: 'alopecia', label: 'Alopecia' },
    ],
  },
  {
    label: 'Urological & Reproductive',
    items: [
      { id: 'kidney_stones', label: 'Kidney Stones' },
      { id: 'recurrent_uti', label: 'Recurrent UTIs' },
      { id: 'endometriosis', label: 'Endometriosis' },
      { id: 'uterine_fibroids', label: 'Uterine Fibroids' },
      { id: 'dysmenorrhea', label: 'Painful Periods' },
      { id: 'menorrhagia', label: 'Heavy Periods' },
    ],
  },
  {
    label: 'Autoimmune',
    items: [
      { id: 'lupus', label: 'Lupus (SLE)' },
      { id: 'scleroderma', label: 'Scleroderma' },
      { id: 'rheumatoid_arthritis', label: 'Rheumatoid Arthritis' },
    ],
  },
]

const SYMPTOMS = [
  'acidity', 'bloating', 'constipation', 'insomnia', 'joint_pain', 'fatigue',
  'anxiety', 'dry_skin', 'skin_rash', 'weight_gain', 'hair_loss',
  'irregular_periods', 'headache', 'cough', 'cold'
]

const GOALS = [
  { id: 'weight_loss',     label: 'Weight Loss',      icon: '⚖️' },
  { id: 'muscle_gain',     label: 'Muscle Gain',       icon: '💪' },
  { id: 'flexibility',     label: 'Flexibility',       icon: '🤸' },
  { id: 'detox',           label: 'Detox and Cleanse', icon: '🧪' },
  { id: 'general_wellness',label: 'General Wellness',  icon: '✨' },
  { id: 'balance',         label: 'Dosha Balance',     icon: '☯️' }
]

const DOSHA_INFO = {
  vata:  { emoji: '💨', desc: 'Air & Space · Creative, energetic, variable' },
  pitta: { emoji: '🔥', desc: 'Fire & Water · Sharp, intense, goal-driven' },
  kapha: { emoji: '🌊', desc: 'Earth & Water · Calm, steady, nurturing' },
}

function titleCaseSlug(value) {
  return value.replace(/_/g, ' ')
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
        fitness_level:  fitnessLevel  || 'beginner',
        activity_level: 'moderate',
        satmya: satmya || undefined,
      })
      navigate('/dashboard')
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

      <motion.div
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
            <motion.div
              key={label}
              className={`onb-step ${index === step ? 'active' : ''} ${index < step ? 'done' : ''}`}
              title={label}
              animate={index === step ? { scale: [1, 1.2, 1] } : {}}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          ))}
        </div>

        <div className="onb-progress-track">
          <motion.div
            className="onb-progress-fill"
            animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        <section className="onb-card">
          <AnimatePresence mode="wait">
            {error ? (
              <motion.div
                className="onb-error"
                key="error"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                {error}
              </motion.div>
            ) : null}
          </AnimatePresence>

          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
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
                        <motion.button
                          key={entry} type="button"
                          onClick={() => setGender(entry)}
                          className={`onb-tile ${gender === entry ? 'selected' : ''}`}
                          whileTap={{ scale: 0.95 }}
                        >
                          <span className="onb-tile-emoji">
                            {entry === 'male' ? '♂️' : entry === 'female' ? '♀️' : '⚧️'}
                          </span>
                          {entry.charAt(0).toUpperCase() + entry.slice(1)}
                        </motion.button>
                      ))}
                    </div>
                  </div>
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
                        { id: 'beginner',  label: 'Beginner',     emoji: '🌱' },
                        { id: 'intermediate', label: 'Intermediate', emoji: '💪' },
                        { id: 'advanced',  label: 'Advanced',     emoji: '⚡' },
                      ].map(f => (
                        <motion.button
                          key={f.id} type="button"
                          onClick={() => setFitnessLevel(f.id)}
                          className={`onb-tile ${fitnessLevel === f.id ? 'selected' : ''}`}
                          whileTap={{ scale: 0.95 }}
                        >
                          <span className="onb-tile-emoji">{f.emoji}</span>
                          {f.label}
                        </motion.button>
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
                      {SYMPTOMS.map(sym => (
                        <button
                          key={sym} type="button"
                          onClick={() => toggleItem(symptoms, setSymptoms, sym)}
                          className={`onb-chip ${symptoms.includes(sym) ? 'selected' : ''}`}
                        >
                          {titleCaseSlug(sym)}
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
                        <motion.button
                          key={g.id} type="button"
                          onClick={() => setGoal(g.id)}
                          className={`onb-tile ${goal === g.id ? 'selected' : ''}`}
                          whileTap={{ scale: 0.94 }}
                          whileHover={{ scale: 1.02 }}
                          animate={goal === g.id ? { scale: [1, 1.06, 1] } : { scale: 1 }}
                          transition={{ type: 'spring', stiffness: 420, damping: 22 }}
                        >
                          <span className="onb-tile-emoji">{g.icon}</span>
                          {g.label}
                        </motion.button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label>Your Dominant Dosha</label>
                    <p className="onb-help">Hover over a dosha to learn more. Not sure? Pick the one that resonates most.</p>
                    <div className="onb-grid-3" style={{ marginTop: 10 }}>
                      {Object.entries(DOSHA_INFO).map(([key, info]) => (
                        <motion.button
                          key={key} type="button"
                          onClick={() => setDosha(key)}
                          className={`onb-tile ${dosha === key ? 'selected' : ''}`}
                          whileTap={{ scale: 0.94 }}
                          whileHover={{ scale: 1.02 }}
                          animate={dosha === key ? { scale: [1, 1.07, 1] } : { scale: 1 }}
                          transition={{ type: 'spring', stiffness: 420, damping: 22 }}
                        >
                          <span className="onb-tile-emoji">{info.emoji}</span>
                          {key.charAt(0).toUpperCase() + key.slice(1)}
                          <span className="onb-tile-desc">{info.desc}</span>
                        </motion.button>
                      ))}
                    </div>
                  </div>
                  <p className="onb-help" style={{ fontSize: '0.78rem', marginTop: 4 }}>
                    🔒 We take your privacy seriously — your health data is encrypted and never sold.
                  </p>
                </div>
              ) : null}
            </motion.div>
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
      </motion.div>
    </div>
  )
}
