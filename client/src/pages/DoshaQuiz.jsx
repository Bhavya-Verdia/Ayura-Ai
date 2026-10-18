import { useState, useEffect, useLayoutEffect, useMemo, Suspense, useRef } from 'react'
import { m, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../providers/AuthContext'
import { profileAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import { Search, Leaf, Zap, TriangleAlert, ScrollText } from 'lucide-react'
import React from 'react'
import { CONDITION_CATEGORIES, conditionLabel } from '../constants/conditions'
import { track, trackSync, EVENTS } from '../lib/analytics'
import { useTranslation } from 'react-i18next'
import './DoshaQuiz.css'
import { TRAIT_QUESTIONS, SYMPTOM_CLUSTERS, CLARIFY_QUESTIONS, MANASA_TRAIT_IDS, localiseQuestions, localiseSymptoms } from './doshaQuiz/questions'
import { DOSHA_COLORS, DOSHA_LABELS, DOSHA_ICONS, DOSHA_GUNAS, CHARAKA_REFS, CLASSICAL_TYPE_DISPLAY, AMA_COLORS } from './doshaQuiz/doshaDisplay'
import { SpectrumSection, TraitBreakdown } from './doshaQuiz/ResultParts'
import TongueUploader from './doshaQuiz/TongueUploader'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

// ── Option ordering ───────────────────────────────────────────────────────────
// Every question used to list its options in the same order — Vata first in all
// 20 dosha questions, Satva first in all 5 Manasa ones — each rendered with an
// A/B/C badge. Anyone satisficing (tap the first plausible option, move on) was
// therefore pushed toward Vata and Satva systematically, which on a 26-question
// quiz is the default behaviour rather than the exception.
//
// The order is now permuted per user per question. Seeded rather than random so
// a given user always sees the same layout — going Back must not reshuffle the
// options under them — while the bias cancels across the user base instead of
// accumulating in one direction. It also defuses straight-lining: tapping
// position A every time no longer yields a single dosha, it yields noise, which
// the confidence gap then correctly reports as an unclear reading.
function hashSeed(str) {
  let h = 2166136261
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

function seededShuffle(items, seedStr) {
  let s = hashSeed(seedStr) || 1
  const next = () => {
    // mulberry32
    s = (s + 0x6D2B79F5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  const out = items.slice()
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

const LOADING_STEPS = [
  'Analyzing your physical constitution…',
  'Reading your mental and behavioral patterns…',
  'Cross-referencing with classical Ayurvedic texts…',
  'Mapping Prakriti and current Vikriti state…',
]

const stepVariants = {
  enter: (d) => ({ x: d > 0 ? 56 : -56, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (d) => ({ x: d > 0 ? -56 : 56, opacity: 0 }),
}

// Grace window after the first tap in which a second tap records a blend.
// This was 650ms, which is less time than it takes to read the hint explaining
// that blending exists — so in practice nobody could reach the feature and
// almost every answer came back as a single dosha. The hint is now shown before
// any selection too, and "Next →" skips the wait for anyone who doesn't want it.
const BLEND_WINDOW_MS = 2000

function detectContradiction(traits) {
  const PHYSICAL_TRAITS = ['body_frame', 'skin', 'digestion', 'sleep', 'temperature', 'hair', 'energy']
  const MENTAL_TRAITS = ['stress_response', 'memory', 'decision_making', 'speech', 'emotional_nature']
  const doshTraits = Object.fromEntries(Object.entries(traits).filter(([k]) => !MANASA_TRAIT_IDS.includes(k)))
  // A trait value may be a blend ("vata+pitta") — count by its primary dosha.
  const primaryOf = (v) => (v ? v.split('+')[0] : undefined)
  const physCounts = { vata: 0, pitta: 0, kapha: 0 }
  const mentCounts = { vata: 0, pitta: 0, kapha: 0 }
  PHYSICAL_TRAITS.forEach(t => { const d = primaryOf(doshTraits[t]); if (d in physCounts) physCounts[d]++ })
  MENTAL_TRAITS.forEach(t => { const d = primaryOf(doshTraits[t]); if (d in mentCounts) mentCounts[d]++ })
  const physDom = Object.entries(physCounts).sort((a, b) => b[1] - a[1])[0]?.[0]
  const mentDom = Object.entries(mentCounts).sort((a, b) => b[1] - a[1])[0]?.[0]
  return physDom && mentDom && physDom !== mentDom
}

export default function DoshaQuiz() {
  const [phase, setPhase] = useState('traits') // traits | symptoms | loading | clarify | confirm | result
  const [traitIndex, setTraitIndex] = useState(0)
  const [direction, setDirection] = useState(1)
  const [traits, setTraits] = useState({})
  const [symptoms, setSymptoms] = useState([])
  const [loadingStep, setLoadingStep] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [rejectedSignals, setRejectedSignals] = useState([])
  const [clarifyAnswers, setClarifyAnswers] = useState({})
  const { updateProfile, user } = useAuth()
  const navigate = useNavigate()
  // Holds the pending auto-advance so a second tap (to add a blend) can cancel it.
  const advanceTimerRef = useRef(null)
  // The question on screen now. The counter above the card moves the moment the
  // index does, while the old card is still sliding out (mode="wait", 300ms), and
  // a tap on that outgoing card ran its stale handlers: it answered the old
  // question again and advanced a second time, so the next question was never
  // shown. Mind questions auto-advance 220ms after a pick, which puts the whole
  // window inside a quick double-tap. A layout effect, so it is current before
  // the browser can deliver the next tap.
  const shownIndexRef = useRef(0)
  useLayoutEffect(() => { shownIndexRef.current = traitIndex }, [traitIndex])

  // ── Funnel instrumentation ─────────────────────────────────────────────────
  // Mirrors of state for the unmount handler: a cleanup closure created on mount
  // would otherwise report whatever the values were on mount, i.e. always
  // question 1, which is exactly the number we're trying to measure.
  const startedAtRef = useRef(Date.now())
  const questionStartRef = useRef(Date.now())
  const reachedResultRef = useRef(false)
  const abandonReportedRef = useRef(false)
  const progressRef = useRef({ phase: 'traits', index: 0, answered: 0 })
  const secondsSince = (ref) => Math.round((Date.now() - ref.current) / 1000)

  // Medical conditions — PREFILLED from the stored profile, fully editable here.
  // They feed the current-imbalance (Vikriti) reading and rare ones are LLM-classified.
  const [conditions, setConditions] = useState(() => [...(user?.medical_history || [])])
  const [condSearch, setCondSearch] = useState('')
  const [otherCond, setOtherCond] = useState('')
  const [showCondPicker, setShowCondPicker] = useState(false)
  const condTouched = useRef(false)
  // If the profile loads after mount, seed the prefill once (unless already edited).
  useEffect(() => {
    if (!condTouched.current && user?.medical_history?.length && conditions.length === 0) {
      setConditions([...user.medical_history])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.medical_history])

  function toggleCondition(id) {
    condTouched.current = true
    setConditions((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]))
  }
  function addOtherConditions() {
    const parsed = otherCond
      .split(',')
      .map((s) => s.trim().toLowerCase().replace(/\s+/g, '_'))
      .filter(Boolean)
    if (parsed.length) {
      condTouched.current = true
      setConditions((prev) => [...new Set([...prev, ...parsed])])
      setOtherCond('')
    }
  }

  const { t } = useTranslation()
  const traitQuestions = useMemo(() => localiseQuestions(t, TRAIT_QUESTIONS, 'trait'), [t])
  const clarifyQuestions = useMemo(() => localiseQuestions(t, CLARIFY_QUESTIONS, 'clarify'), [t])
  const symptomClusters = useMemo(() => localiseSymptoms(t, SYMPTOM_CLUSTERS), [t])
  const currentTraitQ = traitQuestions[traitIndex]
  const traitProgress = (traitIndex / TRAIT_QUESTIONS.length) * 100

  // Cycle loading messages during assessment
  useEffect(() => {
    if (phase !== 'loading') return
    const interval = setInterval(() => {
      setLoadingStep((s) => (s + 1) % LOADING_STEPS.length)
    }, 1500)
    return () => clearInterval(interval)
  }, [phase])

  // Never let a pending auto-advance fire after the component unmounts.
  useEffect(() => () => { if (advanceTimerRef.current) clearTimeout(advanceTimerRef.current) }, [])

  // Keep the unmount mirror current.
  useEffect(() => {
    progressRef.current = {
      phase,
      index: traitIndex,
      answered: Object.keys(traits).length,
    }
  }, [phase, traitIndex, traits])

  // Leaving before the result is the number that matters: it is the only way to
  // see whether 27 auto-advancing questions with no save/resume are costing
  // completions, and which question is where people give up.
  function reportAbandon(exit) {
    if (reachedResultRef.current || abandonReportedRef.current) return
    const { phase: lastPhase, index, answered } = progressRef.current
    // React's development StrictMode mounts, unmounts and remounts, which fired a
    // phantom abandonment at question 1 with nothing answered — and, worse, then
    // suppressed the real one via the guard below. Nobody answers a question or
    // spends a second inside that window, so requiring either is enough to tell
    // the two apart. The cost is not counting sub-second bounces, which is a fair
    // description of "never really started".
    if (answered === 0 && Date.now() - startedAtRef.current < 1000) return
    abandonReportedRef.current = true
    // Synchronous where possible: on the pagehide path an awaited send is lost.
    const send = trackSync(EVENTS.ASSESSMENT_ABANDONED, {
      phase: lastPhase,
      exit,
      last_question_index: index,
      last_question_id: TRAIT_QUESTIONS[index]?.id ?? null,
      questions_answered: answered,
      total_questions: TRAIT_QUESTIONS.length,
      seconds_spent: secondsSince(startedAtRef),
    })
    if (send === false) {
      // SDK still loading — an unmount this early can afford the async path.
      track(EVENTS.ASSESSMENT_ABANDONED, {
        phase: lastPhase,
        exit,
        last_question_index: index,
        last_question_id: TRAIT_QUESTIONS[index]?.id ?? null,
        questions_answered: answered,
        total_questions: TRAIT_QUESTIONS.length,
        seconds_spent: secondsSince(startedAtRef),
      })
    }
  }

  useEffect(() => {
    // Cleared here so the StrictMode remount restores a usable guard.
    abandonReportedRef.current = false
    startedAtRef.current = Date.now()
    questionStartRef.current = Date.now()
    track(EVENTS.ASSESSMENT_STARTED, {
      total_questions: TRAIT_QUESTIONS.length,
      // A retake by someone already assessed behaves differently from a first
      // run and shouldn't be averaged in with it.
      is_retake: Boolean(user?.prakriti_locked),
      is_rescore: Boolean(user?.prakriti_recompute_available),
    })

    // React cleanup only runs on an in-app unmount. Closing the tab, reloading,
    // or typing a new URL is almost certainly the *common* way to quit a long
    // form, and none of those unmount anything — so without this listener the
    // abandonment number would silently exclude most of the abandonment.
    // Best effort by nature: the SDK may not flush before the page dies.
    const onPageHide = () => reportAbandon('pagehide')
    window.addEventListener('pagehide', onPageHide)
    return () => {
      window.removeEventListener('pagehide', onPageHide)
      reportAbandon('unmount')
    }
    // Once per mount — a retake resets state in place rather than remounting, and
    // is reported separately via ASSESSMENT_RETAKE_STARTED.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    // Past this point the assessment is saved server-side, so leaving is not a
    // drop-off — ASSESSMENT_COMPLETED has already fired.
    if (phase === 'confirm' || phase === 'result') reachedResultRef.current = true
    if (phase === 'traits') return  // covered by ASSESSMENT_STARTED
    track(EVENTS.ASSESSMENT_PHASE_REACHED, {
      phase,
      seconds_spent: secondsSince(startedAtRef),
    })
  }, [phase])

  const isManasaQ = MANASA_TRAIT_IDS.includes(currentTraitQ.id)

  // Stable per user + question, so Back/Next never reshuffles under the user.
  // Falls back to the question id alone for the rare pre-auth render.
  const orderSeed = `${user?.id || 'anon'}:${currentTraitQ.id}`
  const traitOptions = useMemo(
    () => seededShuffle(currentTraitQ.options, orderSeed),
    [currentTraitQ, orderSeed],
  )

  // `recorded` is threaded in from selectTrait rather than read off state: this
  // runs from a timeout created in the same tick as setTraits, so the closure's
  // copy of `traits` predates the answer it is reporting on. The Next button
  // passes nothing and reads state, which is current by then.
  function advanceNow(recorded) {
    if (traitIndex !== shownIndexRef.current) return   // from the card sliding out
    if (advanceTimerRef.current) clearTimeout(advanceTimerRef.current)
    const answer = recorded ?? traits[currentTraitQ.id] ?? ''
    track(EVENTS.ASSESSMENT_STEP_COMPLETED, {
      question_index: traitIndex,
      question_id: currentTraitQ.id,
      is_manasa: isManasaQ,
      // Whether the two-tap blend is actually being used now that it is
      // reachable — the 650ms window made it effectively invisible before.
      is_blend: String(answer).includes('+'),
      seconds_on_question: secondsSince(questionStartRef),
    })
    questionStartRef.current = Date.now()
    if (traitIndex < TRAIT_QUESTIONS.length - 1) {
      setDirection(1)
      setTraitIndex((i) => i + 1)
    } else {
      setPhase('symptoms')
    }
  }

  function scheduleAdvance(delay, recorded) {
    if (advanceTimerRef.current) clearTimeout(advanceTimerRef.current)
    advanceTimerRef.current = setTimeout(() => advanceNow(recorded), delay)
  }

  function selectTrait(value) {
    if (traitIndex !== shownIndexRef.current) return   // from the card sliding out
    // Manasa (Triguna) answers are scored by exact string count — no blending.
    if (isManasaQ) {
      setTraits((prev) => ({ ...prev, [currentTraitQ.id]: value }))
      scheduleAdvance(220, value)
      return
    }

    // Deha traits support an optional "primary+secondary" blend: the first tap
    // sets the primary and opens a short grace window; tapping a *different*
    // option within it records the blend, tapping the same one confirms a single.
    const current = traits[currentTraitQ.id] || ''
    const [primary, secondary] = current.split('+')
    let next
    let delay
    if (!primary) {
      next = value                     // first pick → primary, wait for optional blend
      delay = BLEND_WINDOW_MS
    } else if (value === primary) {
      next = primary                   // re-tap primary → confirm single, go now
      delay = 180
    } else if (value === secondary) {
      next = primary                   // re-tap secondary → remove the blend
      delay = BLEND_WINDOW_MS
    } else {
      next = `${primary}+${value}`     // tap a second → blend, advance shortly
      delay = 380
    }
    setTraits((prev) => ({ ...prev, [currentTraitQ.id]: next }))
    scheduleAdvance(delay, next)
  }

  function goBackTrait() {
    if (advanceTimerRef.current) clearTimeout(advanceTimerRef.current)
    questionStartRef.current = Date.now()
    if (traitIndex > 0) {
      setDirection(-1)
      setTraitIndex((i) => i - 1)
    }
  }

  function toggleSymptom(id) {
    setSymptoms((prev) => {
      if (id === 'feeling_balanced') return ['feeling_balanced']
      const withoutBalanced = prev.filter((s) => s !== 'feeling_balanced')
      return withoutBalanced.includes(id)
        ? withoutBalanced.filter((s) => s !== id)
        : [...withoutBalanced, id]
    })
  }

  // Bands the 0-100 confidence score. The band is a property of the reading's
  // clarity, not of the person — unlike the dosha it applies to, which stays out
  // of analytics entirely.
  function confidenceBand(score) {
    if (score == null) return 'unknown'
    if (score >= 75) return 'high'
    if (score >= 45) return 'medium'
    return 'low'
  }

  async function runAssessment() {
    setError('')
    setPhase('loading')
    setLoadingStep(0)
    const blendCount = Object.entries(traits)
      .filter(([k, v]) => !MANASA_TRAIT_IDS.includes(k) && String(v).includes('+')).length
    track(EVENTS.ASSESSMENT_SUBMITTED, {
      questions_answered: Object.keys(traits).length,
      total_questions: TRAIT_QUESTIONS.length,
      blend_count: blendCount,
      // Counts only. Which symptoms and conditions were selected is health data.
      symptom_count: symptoms.length,
      condition_count: conditions.length,
      seconds_spent: secondsSince(startedAtRef),
    })
    try {
      const dehaTraits = {}
      const manasaTraits = {}
      for (const [k, v] of Object.entries(traits)) {
        if (MANASA_TRAIT_IDS.includes(k)) manasaTraits[k] = v
        else dehaTraits[k] = v
      }
      const response = await profileAPI.doshaAssessment({
        physical_traits: dehaTraits,
        current_symptoms: symptoms,
        manasa_traits: Object.keys(manasaTraits).length > 0 ? manasaTraits : undefined,
        // Edited (or prefilled-unchanged) conditions — persisted + fed into Vikriti.
        medical_history: conditions,
      })
      const assessResult = response.data
      // Saved server-side from here on, so leaving is no longer abandonment —
      // the optional clarify follow-up that may come next must not re-count it.
      reachedResultRef.current = true
      setResult(assessResult)
      await updateProfile({})
      // The API returns dosha_confidence as a 0-100 score and dosha_contradictions
      // as a list — derive the qualitative state from those (not the non-existent
      // `confidence`/`contradictions` fields). When the read is shaky — conflicting
      // trait groups or low confidence — we ask two clarifying follow-ups rather
      // than commit to an uncertain constitution.
      const isLowConfidence = (assessResult.dosha_confidence ?? 0) < 45
      const hasContradiction = detectContradiction(traits) || (assessResult.dosha_contradictions?.length > 0)
      track(EVENTS.ASSESSMENT_COMPLETED, {
        confidence_band: confidenceBand(assessResult.dosha_confidence),
        // How often the reading is shaky enough to need follow-ups is a quality
        // measure of the instrument itself.
        needed_clarify: Boolean(hasContradiction || isLowConfidence),
        had_contradiction: Boolean(hasContradiction),
        blend_count: blendCount,
        symptom_count: symptoms.length,
        seconds_spent: secondsSince(startedAtRef),
        is_retake: Boolean(user?.prakriti_locked),
      })
      if (hasContradiction || isLowConfidence) {
        setPhase('clarify')
      } else {
        setPhase('confirm')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Assessment failed. Please try again.')
      // A failure here is indistinguishable from a drop-off in the funnel unless
      // it is reported: the user answered everything and still got nothing.
      track(EVENTS.ASSESSMENT_ABANDONED, {
        phase: 'submit_failed',
        status: err.response?.status ?? 0,
        questions_answered: Object.keys(traits).length,
        total_questions: TRAIT_QUESTIONS.length,
        seconds_spent: secondsSince(startedAtRef),
      })
      setPhase('symptoms')
    }
  }

  function retake() {
    track(EVENTS.ASSESSMENT_RETAKE_STARTED, {
      seconds_spent: secondsSince(startedAtRef),
      is_rescore: Boolean(user?.prakriti_recompute_available),
    })
    startedAtRef.current = Date.now()
    questionStartRef.current = Date.now()
    reachedResultRef.current = false
    abandonReportedRef.current = false
    setPhase('traits')
    setTraitIndex(0)
    setDirection(1)
    setTraits({})
    setSymptoms([])
    setResult(null)
    setError('')
    setRejectedSignals([])
    setClarifyAnswers({})
  }

  // ── Clarify phase ────────────────────────────────────────────────────────────
  if (phase === 'clarify') {
    const allAnswered = clarifyQuestions.every(q => clarifyAnswers[q.id])
    return (
      <div className="da-root">
        <Helmet><title>Clarify Your Profile | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <div className="da-orb da-orb-b" />
        <m.div
          className="da-shell"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="da-clarify-header">
            <span className="da-clarify-icon"><Search size={18} strokeWidth={2} /></span>
            <h2 className="da-clarify-title">A couple of follow-up questions</h2>
            <p className="da-clarify-sub">
              Your physical and mental signals show some contrast — these two questions help us resolve the pattern accurately.
            </p>
          </div>

          {clarifyQuestions.map((q) => (
            <div key={q.id} className="da-clarify-section">
              <h3 className="da-question">{q.question}</h3>
              <p className="da-hint">{q.hint}</p>
              <div className="da-trait-options">
                {/* Same per-user permutation as the trait questions — these are
                    the tie-breakers for an already-unclear reading, so a
                    position bias here would land squarely on the ambiguous cases. */}
                {seededShuffle(q.options, `${user?.id || 'anon'}:${q.id}`).map((opt, optIdx) => {
                  const selected = clarifyAnswers[q.id] === opt.value
                  return (
                    <m.button
                      key={opt.value}
                      type="button"
                      className={`da-trait-card ${selected ? 'selected' : ''}`}
                      onClick={() => setClarifyAnswers(prev => ({ ...prev, [q.id]: opt.value }))}
                      whileHover={{ scale: 1.015 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <span className="da-trait-icon" aria-hidden="true">{String.fromCharCode(65 + optIdx)}</span>
                      <span className="da-trait-label">{opt.label}</span>
                      <span className="da-trait-desc">{opt.desc}</span>
                      {selected && <span className="da-trait-check">✓</span>}
                    </m.button>
                  )
                })}
              </div>
            </div>
          ))}

          <div className="da-confirm-actions" style={{ marginTop: 24 }}>
            <m.button
              className="btn btn-primary btn-lg"
              disabled={!allAnswered}
              onClick={() => {
                if (result) {
                  const boost = { vata: 0, pitta: 0, kapha: 0 }
                  Object.values(clarifyAnswers).forEach(v => { if (boost[v] !== undefined) boost[v] += 8 })
                  const newVikriti = { ...result.vikriti_scores }
                  Object.entries(boost).forEach(([d, b]) => {
                    newVikriti[d] = Math.min(70, (newVikriti[d] || 33) + b)
                  })
                  const total = Object.values(newVikriti).reduce((s, v) => s + v, 0) || 1
                  const norm = Object.fromEntries(Object.entries(newVikriti).map(([d, v]) => [d, Math.round(v / total * 100)]))
                  const diff = 100 - Object.values(norm).reduce((s, v) => s + v, 0)
                  if (diff !== 0) norm[Object.entries(norm).sort((a, b) => b[1] - a[1])[0][0]] += diff
                  setResult(prev => ({
                    ...prev,
                    vikriti_scores: norm,
                    vikriti_dominant: Object.entries(norm).sort((a, b) => b[1] - a[1])[0][0],
                    dosha_confidence: Math.min(85, (prev.dosha_confidence || 35) + 15),
                  }))
                }
                setPhase('confirm')
              }}
              whileTap={{ scale: 0.97 }}
            >
              Continue →
            </m.button>
            <m.button
              className="btn btn-secondary"
              onClick={() => setPhase('confirm')}
              whileTap={{ scale: 0.97 }}
            >
              Skip — use initial result
            </m.button>
          </div>
        </m.div>
      </div>
    )
  }

  // ── Loading phase ────────────────────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <div className="da-root">
        <Helmet><title>Analyzing Your Dosha | Ayura AI</title></Helmet>
        <Suspense fallback={null}><LazyParticleField count={30} spread={18} style={{ opacity: 0.2 }} /></Suspense>
        <div className="da-shell da-shell-loading">
          <div className="da-loading-orb">
            <div className="da-loading-ring" />
            <div className="da-loading-ring da-loading-ring-2" />
            <span className="da-loading-icon"><Leaf size={20} strokeWidth={2} /></span>
          </div>
          <AnimatePresence mode="wait">
            <m.p
              key={loadingStep}
              className="da-loading-text"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.4 }}
            >
              {LOADING_STEPS[loadingStep]}
            </m.p>
          </AnimatePresence>
          <p className="da-loading-sub">Scoring your constitution with a deterministic Ashtavidha Pareeksha engine — AI writes the explanation.</p>
        </div>
      </div>
    )
  }

  // ── Confirm phase ────────────────────────────────────────────────────────────
  if (phase === 'confirm' && result) {
    const vikritiDominant = result.vikriti_dominant
    const keySignals = result.dosha_key_signals || []
    const constitutionType = result.dosha_constitution_type || result.dominant_dosha || ''

    return (
      <div className="da-root">
        <Helmet><title>Confirm Your Results | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <Suspense fallback={null}><LazyParticleField count={30} spread={18} style={{ opacity: 0.2 }} /></Suspense>
        <m.div
          className="da-shell"
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="da-confirm-header">
            <span className="da-confirm-icon"><Leaf size={20} strokeWidth={2} /></span>
            <h2 className="da-confirm-title">Your Vaidya Assessment</h2>
            <p className="da-confirm-sub">
              Based on your {TRAIT_QUESTIONS.length} constitutional traits (Shareera + Manas Prakriti) and current symptoms:
            </p>
          </div>

          <div className="da-confirm-constitution">
            <span style={{ opacity: 0.7, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Constitution</span>
            <strong style={{ fontSize: '1.1rem' }}>
              {constitutionType.replace(/_/g, '–').replace(/\b\w/g, (c) => c.toUpperCase())}
            </strong>
          </div>

          {vikritiDominant && (
            <div className="da-confirm-imbalance" style={{ borderColor: DOSHA_COLORS[vikritiDominant] }}>
              <span style={{ display: 'inline-flex', color: DOSHA_COLORS[vikritiDominant] }}>
                {(() => { const DI = DOSHA_ICONS[vikritiDominant]; return DI ? <DI size={22} strokeWidth={2} /> : null })()}
              </span>
              <div>
                <span style={{ opacity: 0.7, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Primary imbalance right now</span>
                <strong style={{ display: 'block', color: DOSHA_COLORS[vikritiDominant], fontSize: '1.05rem' }}>
                  {DOSHA_LABELS[vikritiDominant]} excess
                </strong>
              </div>
            </div>
          )}

          {keySignals.length > 0 && (
            <div className="da-confirm-signals">
              <span className="da-confirm-signals-label">Tap to dismiss signals that don't apply to you</span>
              <div className="da-confirm-chips">
                {keySignals.slice(0, 6).map((sig, i) => {
                  const rejected = rejectedSignals.includes(sig)
                  return (
                    <m.button
                      key={i}
                      type="button"
                      className={`da-confirm-chip${rejected ? ' rejected' : ''}`}
                      onClick={() => setRejectedSignals(prev =>
                        rejected ? prev.filter(s => s !== sig) : [...prev, sig]
                      )}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.05 + i * 0.06 }}
                    >
                      {rejected ? '✕' : '✓'} {sig}
                    </m.button>
                  )
                })}
              </div>
              {rejectedSignals.length > 0 && (
                <p className="da-confirm-adjust-note">
                  {rejectedSignals.length} signal{rejectedSignals.length > 1 ? 's' : ''} dismissed — scores will adjust when you confirm.
                </p>
              )}
            </div>
          )}

          <div className="da-confirm-actions">
            <m.button
              className="btn btn-primary btn-lg"
              onClick={() => {
                if (rejectedSignals.length > 0 && result) {
                  const vikriti = { ...result.vikriti_scores }
                  const dominant = result.vikriti_dominant
                  const reduction = Math.min(rejectedSignals.length * 4, 15)
                  if (dominant && vikriti[dominant] !== undefined) {
                    vikriti[dominant] = Math.max(10, vikriti[dominant] - reduction)
                    const others = Object.keys(vikriti).filter(d => d !== dominant)
                    const perOther = Math.floor(reduction / others.length)
                    others.forEach(d => { vikriti[d] = (vikriti[d] || 0) + perOther })
                    const total = Object.values(vikriti).reduce((a, b) => a + b, 0)
                    Object.keys(vikriti).forEach(d => { vikriti[d] = Math.round(vikriti[d] / total * 100) })
                    const diff = 100 - Object.values(vikriti).reduce((a, b) => a + b, 0)
                    if (diff !== 0) vikriti[dominant] += diff
                    setResult(prev => ({
                      ...prev,
                      vikriti_scores: vikriti,
                      vikriti_dominant: Object.entries(vikriti).sort((a, b) => b[1] - a[1])[0][0],
                      dosha_key_signals: (prev?.dosha_key_signals || []).filter(s => !rejectedSignals.includes(s)),
                    }))
                  }
                }
                setPhase('result')
              }}
              whileTap={{ scale: 0.97 }}
            >
              Yes, this looks right →
            </m.button>
            <m.button
              className="btn btn-secondary"
              onClick={retake}
              whileTap={{ scale: 0.97 }}
            >
              Not quite — retake
            </m.button>
          </div>
        </m.div>
      </div>
    )
  }

  // ── Result phase ─────────────────────────────────────────────────────────────
  if (phase === 'result' && result) {
    const prakriti = result.dosha_scores || {}
    const vikriti = result.vikriti_scores || {}
    const vikritiDominant = result.vikriti_dominant
    const constitutionType = result.dosha_constitution_type || result.dominant_dosha || ''
    const explanation = result.dosha_explanation
    const immediateFocus = result.dosha_immediate_focus
    const keySignals = result.dosha_key_signals || []
    const unmappedConditions = result.dosha_unmapped_conditions || []
    const confidence = result.dosha_confidence >= 70 ? 'high' : result.dosha_confidence >= 45 ? 'medium' : 'low'

    function handleTongueResult(tongueData) {
      setResult((r) => ({
        ...r,
        vikriti_scores: tongueData.vikriti_scores,
        vikriti_dominant: tongueData.vikriti_dominant,
      }))
    }

    return (
      <div className="da-root">
        <Helmet><title>Your Ayurvedic Profile | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <div className="da-orb da-orb-b" />
        <Suspense fallback={null}><LazyParticleField count={40} spread={18} style={{ opacity: 0.25 }} /></Suspense>

        <m.div
          className="da-shell"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          {/* A stale-scoring result is the one case where the lock does NOT hold,
              so saying "set for life" here would be wrong — the retake below will
              genuinely recompute it. */}
          {user?.prakriti_recompute_available ? (
            <div className="da-prakriti-lock-notice da-prakriti-recompute-notice">
              <strong>We've corrected how constitutions are scored.</strong> Your Prakriti was calculated with an earlier version that could overstate a secondary dosha. Retaking the assessment will recalculate it — normally Prakriti is fixed for life, so this is a one-time update.
            </div>
          ) : user?.prakriti_locked && (
            <div className="da-prakriti-lock-notice">
              <strong>Prakriti already determined.</strong> Your constitutional type is set for life — only your Vikriti (current imbalance) has been updated from this session.
            </div>
          )}
          <div className="da-result-header">
            <h1 className="da-result-title">Your Ayurvedic Profile</h1>
            <span className="da-constitution-badge">
              {CLASSICAL_TYPE_DISPLAY[result.prakriti_classical_type || constitutionType] ||
               constitutionType.replace(/_/g, '-').replace(/\b\w/g, c => c.toUpperCase()) + ' Prakriti'}
            </span>
          </div>

          <div className="da-result-dual">
            <SpectrumSection
              title="Constitution (Prakriti)"
              scores={prakriti}
              highlightDominant={false}
              capped
              footnote="A relative weighting across the three doshas, not a percentage of you — everyone carries all three. A self-assessment can't justify a reading above 55, so that's the top of this scale."
            />
            <SpectrumSection
              title="Current Imbalance (Vikriti)"
              scores={vikriti}
              highlightDominant={true}
            />
          </div>

          <TraitBreakdown traits={traits} />

          {/* ── Guna Profile ─────────────────────────────────── */}
          {(() => {
            const gunas = result.primary_gunas?.length
              ? result.primary_gunas
              : (DOSHA_GUNAS[result.dominant_dosha || result.vikriti_dominant] || [])
            if (!gunas.length) return null
            return (
              <div className="da-guna-profile">
                <span className="da-guna-title">Your Dominant Gunas (Qualities)</span>
                <div className="da-guna-tags">
                  {gunas.map((g, i) => (
                    <span key={i} className="da-guna-tag">{g}</span>
                  ))}
                </div>
                <span className="da-guna-ref">Per Charaka Sutrasthana 1.59–61 (Vimshatika Guna)</span>
              </div>
            )
          })()}

          {/* ── Manas Prakriti ─────────────────────────────────── */}
          {result.manasa_prakriti && typeof result.manasa_prakriti === 'object' ? (
            <div className="da-manas-box">
              <span className="da-manas-label">Manasa Prakriti — Triguna Balance</span>
              <span className="da-manas-ref">Charaka Samhita Shareera Sthana 4 — Triguna Prakriti</span>
              <div className="da-manas-guna-badge" style={{ color: DOSHA_COLORS[result.manasa_prakriti.dominant_guna] }}>
                {result.manasa_prakriti.label} ({result.manasa_prakriti.dominant_guna?.charAt(0).toUpperCase() + result.manasa_prakriti.dominant_guna?.slice(1)} dominant)
              </div>
              {['satva', 'rajas', 'tamas'].map(guna => (
                <div key={guna} className="da-dosha-bar-row">
                  <span className="da-dosha-bar-label" style={{ color: DOSHA_COLORS[guna] }}>
                    {guna.charAt(0).toUpperCase() + guna.slice(1)}
                  </span>
                  <div className="da-dosha-bar-track">
                    <m.div
                      className="da-dosha-bar-fill"
                      style={{ background: DOSHA_COLORS[guna] }}
                      initial={{ width: 0 }}
                      animate={{ width: `${result.manasa_prakriti[guna] || 0}%` }}
                      transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                  <span className="da-dosha-bar-pct">{result.manasa_prakriti[guna] || 0}%</span>
                </div>
              ))}
              <p className="da-manas-text">{result.manasa_prakriti.description}</p>
            </div>
          ) : result.manas_prakriti ? (
            <div className="da-manas-box">
              <span className="da-manas-label">Manas Prakriti (Mental Constitution)</span>
              <p className="da-manas-text">{result.manas_prakriti}</p>
            </div>
          ) : null}

          {/* ── Ama Score ─────────────────────────────────────────── */}
          {result.ama_indicator && result.ama_indicator !== 'none' && (
            <div className="da-ama-row">
              <span className="da-ama-label">Ama Level</span>
              <span
                className="da-ama-badge"
                style={{ color: AMA_COLORS[result.ama_indicator] || AMA_COLORS.mild }}
              >
                {result.ama_indicator.charAt(0).toUpperCase() + result.ama_indicator.slice(1)}
              </span>
              <span className="da-ama-hint">
                {result.ama_indicator === 'high'
                  ? '— Digestive toxins significantly indicated. Prioritise Agni kindling and light diet.'
                  : result.ama_indicator === 'moderate'
                  ? '— Some Ama accumulation. Support digestion and avoid heavy foods.'
                  : '— Mild Ama present. Monitor with weekly check-ins.'}
              </span>
            </div>
          )}

          {result.dosha_contradictions?.length > 0 && (
            <div className="da-contradiction-note">
              <span className="da-contradiction-icon"><Zap size={16} strokeWidth={2} /></span>
              <div>
                <strong>Mixed signals detected</strong>
                <p>{result.dosha_contradictions[0]}</p>
                <p className="da-contradiction-hint">Weekly check-ins will resolve this over time as more data accumulates.</p>
              </div>
            </div>
          )}

          {vikritiDominant && (
            <div className="da-vikriti-note" style={{ borderColor: DOSHA_COLORS[vikritiDominant] }}>
              <span className="da-vikriti-icon" style={{ color: DOSHA_COLORS[vikritiDominant], display: 'inline-flex' }}><TriangleAlert size={16} strokeWidth={2} /></span>
              <span>Your current <strong style={{ color: DOSHA_COLORS[vikritiDominant] }}>{DOSHA_LABELS[vikritiDominant]}</strong> imbalance is the primary focus for your wellness plans.</span>
            </div>
          )}

          {explanation && (
            <div className="da-explanation-box">
              <p className="da-explanation-text">{explanation}</p>
            </div>
          )}

          {immediateFocus && (
            <div className="da-focus-box">
              <span className="da-focus-label">What your plans will target</span>
              <p className="da-focus-text">{immediateFocus}</p>
            </div>
          )}

          {keySignals.length > 0 && (
            <div className="da-key-signals">
              <span className="da-signals-label">Key signals from your assessment</span>
              <ul className="da-signals-list">
                {keySignals.map((sig, i) => (
                  <m.li
                    key={i}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 + i * 0.1 }}
                  >
                    {sig}
                  </m.li>
                ))}
              </ul>
            </div>
          )}

          {unmappedConditions.length > 0 && (
            <div className="da-unmapped-note">
              <span className="da-unmapped-icon" aria-hidden="true"><TriangleAlert size={16} strokeWidth={2} /></span>
              <div className="da-unmapped-body">
                <span className="da-unmapped-label">Conditions we couldn't classify</span>
                <p className="da-unmapped-list">{unmappedConditions.join(', ')}</p>
                <p className="da-unmapped-hint">
                  These fall outside our classical dosha mapping, so they weren't scored — but they're
                  noted and factored into your guidance. Share them with a qualified Vaidya for a full reading.
                </p>
              </div>
            </div>
          )}

          <TongueUploader onResult={handleTongueResult} />

          <div className="da-confidence-row">
            <span className="da-confidence-label">Assessment confidence</span>
            <span className={`da-confidence-badge da-confidence-${confidence}`}>
              {confidence.charAt(0).toUpperCase() + confidence.slice(1)}
            </span>
          </div>

          <div className="da-classical-ref">
            <span className="da-classical-ref-icon"><ScrollText size={16} strokeWidth={2} /></span>
            <span>
              {CHARAKA_REFS[result.prakriti_classical_type] || CHARAKA_REFS[result.dominant_dosha] || 'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana'}
            </span>
          </div>

          <div className="da-result-actions">
            <m.button
              className="btn btn-primary btn-lg"
              onClick={() => navigate('/dashboard')}
              whileTap={{ scale: 0.97 }}
            >
              Generate My Plans →
            </m.button>
            <m.button
              className="btn btn-secondary"
              onClick={retake}
              whileTap={{ scale: 0.97 }}
            >
              Retake Assessment
            </m.button>
          </div>

          <div className="da-disclaimer-block">
            <p className="da-disclaimer">
              This assessment follows the CCRAS (Central Council for Research in Ayurvedic Sciences) Prakriti evaluation framework, adapted for digital self-screening. It is a wellness guidance tool — not a clinical diagnosis or a replacement for examination by a qualified Vaidya.
            </p>
            <p className="da-disclaimer da-disclaimer-nadi">
              Note: Classical Nadi Pareeksha (pulse examination) requires physical assessment by a qualified Ayurvedic practitioner and cannot be fully replicated through self-report. For definitive Prakriti determination, consult a trained Vaidya.
            </p>
          </div>
        </m.div>
      </div>
    )
  }

  // ── Symptom phase ────────────────────────────────────────────────────────────
  if (phase === 'symptoms') {
    return (
      <div className="da-root">
        <Helmet><title>Current Symptoms | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <Suspense fallback={null}><LazyParticleField count={25} spread={20} style={{ opacity: 0.2 }} /></Suspense>

        <m.div
          className="da-shell"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="da-phase-header">
            <button type="button" className="btn btn-secondary da-back-btn" onClick={() => { setPhase('traits'); setTraitIndex(TRAIT_QUESTIONS.length - 1) }}>← Back</button>
            <div className="da-phase-steps">
              <span className="da-step done">Physical Traits</span>
              <span className="da-step-sep">›</span>
              <span className="da-step active">Current State</span>
            </div>
          </div>

          <div className="da-symptom-intro">
            <h2 className="da-question">How are you feeling right now?</h2>
            <p className="da-hint">Select everything that applies over the past few weeks. Pick as many as you like — or choose "Feeling balanced" if things are good.</p>
          </div>

          <div className="da-symptom-grid">
            {symptomClusters.map((cluster) => {
              const selected = symptoms.includes(cluster.id)
              return (
                <m.button
                  key={cluster.id}
                  type="button"
                  className={`da-symptom-chip ${selected ? 'selected' : ''}`}
                  onClick={() => toggleSymptom(cluster.id)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                >
                  <span className="da-chip-label">{cluster.label}</span>
                  <span className="da-chip-desc">{cluster.desc}</span>
                  {selected && <span className="da-chip-check">✓</span>}
                </m.button>
              )
            })}
          </div>

          <div className="da-cond-section">
            <h3 className="da-cond-title">Medical conditions</h3>
            <p className="da-hint">
              Prefilled from your profile — add or remove anything. These sharpen your current-imbalance
              (Vikriti) reading; conditions we don't recognise are interpreted by AI, never ignored.
            </p>

            {conditions.length > 0 && (
              <div className="da-cond-chips">
                {conditions.map((id) => (
                  <button
                    key={id}
                    type="button"
                    className="da-cond-chip selected"
                    onClick={() => toggleCondition(id)}
                    title="Remove"
                  >
                    {conditionLabel(id)} <span className="da-cond-x" aria-hidden="true">×</span>
                  </button>
                ))}
              </div>
            )}

            <button
              type="button"
              className="da-cond-toggle"
              onClick={() => setShowCondPicker((v) => !v)}
            >
              {showCondPicker ? 'Done adding' : (conditions.length ? '+ Add / edit conditions' : '+ Add a condition')}
            </button>

            {showCondPicker && (
              <div className="da-cond-picker">
                <input
                  className="da-cond-search"
                  type="text"
                  placeholder="Search conditions…"
                  value={condSearch}
                  onChange={(e) => setCondSearch(e.target.value)}
                />
                {CONDITION_CATEGORIES.map((cat) => {
                  const q = condSearch.trim().toLowerCase()
                  const visible = q ? cat.items.filter(({ label }) => label.toLowerCase().includes(q)) : cat.items
                  if (visible.length === 0) return null
                  return (
                    <div key={cat.label} className="da-cond-cat">
                      <span className="da-cond-cat-label">{cat.label}</span>
                      <div className="da-cond-chips">
                        {visible.map(({ id, label }) => (
                          <button
                            key={id}
                            type="button"
                            className={`da-cond-chip ${conditions.includes(id) ? 'selected' : ''}`}
                            onClick={() => toggleCondition(id)}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )
                })}
                <div className="da-cond-other">
                  <input
                    className="da-cond-search"
                    type="text"
                    placeholder="Not listed? e.g. sarcoidosis, lyme disease"
                    value={otherCond}
                    onChange={(e) => setOtherCond(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addOtherConditions() } }}
                  />
                  <button type="button" className="btn btn-secondary" onClick={addOtherConditions}>Add</button>
                </div>
              </div>
            )}
          </div>

          {error && (
            <m.div className="da-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              {error}
            </m.div>
          )}

          <div className="da-symptom-footer">
            <m.button
              type="button"
              className="btn btn-primary btn-lg"
              onClick={runAssessment}
              whileTap={{ scale: 0.97 }}
            >
              Assess My Dosha →
            </m.button>
            <p className="da-symptom-note">Your answers are scored by a deterministic classical Ayurvedic engine — AI only writes your personalised explanation.</p>
          </div>
        </m.div>
      </div>
    )
  }

  // ── Traits phase ─────────────────────────────────────────────────────────────
  return (
    <div className="da-root">
      <Helmet><title>Dosha Assessment | Ayura AI</title></Helmet>
      <div className="da-orb da-orb-a" />
      <div className="da-orb da-orb-b" />
      <Suspense fallback={null}><LazyParticleField count={25} spread={20} style={{ opacity: 0.2 }} /></Suspense>

      <m.div
        className="da-shell"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="da-phase-header">
          <button
            type="button"
            className="btn btn-secondary da-back-btn"
            onClick={traitIndex > 0 ? goBackTrait : () => navigate(-1)}
          >
            ← Back
          </button>
          <div className="da-phase-steps">
            <span className="da-step active">Physical Traits</span>
            <span className="da-step-sep">›</span>
            <span className="da-step">Current State</span>
          </div>
        </div>

        <div className="da-progress-track">
          <m.div
            className="da-progress-fill"
            animate={{ width: `${traitProgress}%` }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        <p className="da-progress-label">Question {traitIndex + 1} of {TRAIT_QUESTIONS.length}</p>

        <div className="da-trait-card-area">
          <AnimatePresence mode="wait" custom={direction}>
            <m.div
              key={traitIndex}
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <h2 className="da-question">{currentTraitQ.question}</h2>
              <p className="da-hint">{currentTraitQ.hint}</p>
              {(() => {
                const [selPrimary, selSecondary] = (traits[currentTraitQ.id] || '').split('+')
                return (
                  <>
                    <div className={`da-trait-options${traitOptions.length === 4 ? ' da-trait-options-4' : ''}`}>
                      {traitOptions.map((opt, optIdx) => {
                        const isPrimary = selPrimary === opt.value
                        const isSecondary = selSecondary === opt.value
                        return (
                          <m.button
                            key={opt.value}
                            type="button"
                            className={`da-trait-card ${isPrimary ? 'selected' : ''} ${isSecondary ? 'selected-secondary' : ''}`}
                            onClick={() => selectTrait(opt.value)}
                            whileHover={{ scale: 1.015 }}
                            whileTap={{ scale: 0.98 }}
                          >
                            <span className="da-trait-icon" aria-hidden="true">{String.fromCharCode(65 + optIdx)}</span>
                            <span className="da-trait-label">{opt.label}</span>
                            <span className="da-trait-desc">{opt.desc}</span>
                            {isPrimary && <span className="da-trait-check">✓</span>}
                            {isSecondary && <span className="da-trait-check da-trait-check-secondary">＋</span>}
                          </m.button>
                        )
                      })}
                    </div>
                    {/* Blend affordance — Prakriti is rarely one pure dosha, so the
                        option to pick two has to be visible BEFORE the first tap.
                        Explaining it only afterwards put the user under a timer to
                        read it, which meant the feature may as well not have existed. */}
                    {!isManasaQ && !selPrimary && (
                      <p className="da-blend-hint">Pick the closest — or tap two options if you're a blend of both.</p>
                    )}
                    {!isManasaQ && selPrimary && !selSecondary && (
                      <p className="da-blend-hint">Mostly this — but a blend? Tap a second option (optional).</p>
                    )}
                    {!isManasaQ && selPrimary && selSecondary && (
                      <p className="da-blend-hint da-blend-hint-active">Blend recorded: mostly {selPrimary}, partly {selSecondary}.</p>
                    )}
                    {/* Lets anyone who doesn't want the blend pause skip it, so the
                        wait reads as deliberate rather than as a laggy interface. */}
                    {selPrimary && (
                      <button type="button" className="btn btn-primary da-next-btn" onClick={() => advanceNow()}>
                        {traitIndex < TRAIT_QUESTIONS.length - 1 ? 'Next →' : 'Continue →'}
                      </button>
                    )}
                  </>
                )
              })()}
            </m.div>
          </AnimatePresence>
        </div>

        <p className="da-disclaimer">
          Answer honestly based on your lifelong patterns — not what you wish were true. This helps build an accurate Ayurvedic profile.
        </p>
      </m.div>
    </div>
  )
}
