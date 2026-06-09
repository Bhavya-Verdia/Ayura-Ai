import { useState, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../providers/AuthContext'
import { profileAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import React from 'react'
import './DoshaQuiz.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

// ── 20 classical dosha quiz questions ──────────────────────────────────────
// Rating scale: 1-2 = Vata leaning, 3 = Pitta leaning, 4-5 = Kapha leaning
const QUESTIONS = [
  {
    id: 1,
    category: 'Body',
    question: 'How would you describe your body frame?',
    options: [
      { value: 1, label: 'Thin, light, difficult to gain weight' },
      { value: 3, label: 'Medium, muscular, athletic build' },
      { value: 5, label: 'Larger frame, tendency to gain weight easily' },
    ],
  },
  {
    id: 2,
    category: 'Body',
    question: 'How is your skin texture?',
    options: [
      { value: 1, label: 'Dry, rough, or cracked' },
      { value: 3, label: 'Warm, oily, prone to acne or rashes' },
      { value: 5, label: 'Smooth, soft, cool, and moist' },
    ],
  },
  {
    id: 3,
    category: 'Body',
    question: 'How would you describe your hair?',
    options: [
      { value: 1, label: 'Dry, frizzy, thin, or brittle' },
      { value: 3, label: 'Fine, oily, prone to premature graying or thinning' },
      { value: 5, label: 'Thick, wavy, lustrous, and oily' },
    ],
  },
  {
    id: 4,
    category: 'Body',
    question: 'How do you tolerate cold weather?',
    options: [
      { value: 1, label: 'I dislike cold intensely and get cold easily' },
      { value: 3, label: 'I prefer moderate temperatures — not too hot or cold' },
      { value: 5, label: 'I prefer cooler weather and dislike heat' },
    ],
  },
  {
    id: 5,
    category: 'Body',
    question: 'How is your appetite and digestion?',
    options: [
      { value: 1, label: 'Irregular appetite, variable digestion, prone to bloating' },
      { value: 3, label: 'Strong, sharp appetite; irritable when meals are delayed' },
      { value: 5, label: 'Steady, mild appetite; slow digestion; rarely hungry' },
    ],
  },
  {
    id: 6,
    category: 'Mind',
    question: 'How is your sleep pattern?',
    options: [
      { value: 1, label: 'Light sleeper, difficulty falling or staying asleep' },
      { value: 3, label: 'Moderate sleep; can wake easily but fall back asleep' },
      { value: 5, label: 'Deep, prolonged sleep; hard to wake up in the morning' },
    ],
  },
  {
    id: 7,
    category: 'Mind',
    question: 'How is your memory?',
    options: [
      { value: 1, label: 'Quick to learn, quick to forget' },
      { value: 3, label: 'Sharp, clear memory with good recall' },
      { value: 5, label: 'Slow to learn but retains information permanently' },
    ],
  },
  {
    id: 8,
    category: 'Mind',
    question: 'How do you handle stress?',
    options: [
      { value: 1, label: 'Tend to worry, feel anxious, or get overwhelmed' },
      { value: 3, label: 'Become irritated, angry, or intensely focused' },
      { value: 5, label: 'Withdraw, become complacent, or seek comfort in food' },
    ],
  },
  {
    id: 9,
    category: 'Mind',
    question: 'How would you describe your speech?',
    options: [
      { value: 1, label: 'Fast, talkative, jump between topics' },
      { value: 3, label: 'Concise, precise, direct, and persuasive' },
      { value: 5, label: 'Slow, melodious, thoughtful, and deliberate' },
    ],
  },
  {
    id: 10,
    category: 'Mind',
    question: 'How do you make decisions?',
    options: [
      { value: 1, label: 'Quickly and impulsively; change my mind often' },
      { value: 3, label: 'Decisively after quick analysis' },
      { value: 5, label: 'Slowly, after thorough deliberation' },
    ],
  },
  {
    id: 11,
    category: 'Energy',
    question: 'How is your energy level throughout the day?',
    options: [
      { value: 1, label: 'Comes in bursts; get tired quickly' },
      { value: 3, label: 'Steady and strong, especially mid-day' },
      { value: 5, label: 'Slow to start but steady once going; high stamina' },
    ],
  },
  {
    id: 12,
    category: 'Energy',
    question: 'What is your exercise preference?',
    options: [
      { value: 1, label: 'Light, creative movement — dance, yoga, walking' },
      { value: 3, label: 'Competitive, intense sports or workouts' },
      { value: 5, label: 'Steady, endurance activities — hiking, swimming' },
    ],
  },
  {
    id: 13,
    category: 'Energy',
    question: 'How do you respond to routine?',
    options: [
      { value: 1, label: 'I dislike routine; I crave variety and change' },
      { value: 3, label: 'I like structured plans but can adapt quickly' },
      { value: 5, label: 'I thrive on routine and resist change' },
    ],
  },
  {
    id: 14,
    category: 'Emotions',
    question: 'How do you typically feel emotionally when balanced?',
    options: [
      { value: 1, label: 'Creative, enthusiastic, lively, and adaptable' },
      { value: 3, label: 'Confident, passionate, focused, and goal-oriented' },
      { value: 5, label: 'Calm, nurturing, loving, and patient' },
    ],
  },
  {
    id: 15,
    category: 'Emotions',
    question: 'What emotions surface when you are imbalanced?',
    options: [
      { value: 1, label: 'Fear, anxiety, scattered thinking, insomnia' },
      { value: 3, label: 'Anger, judgment, jealousy, inflammation' },
      { value: 5, label: 'Greed, attachment, depression, lethargy' },
    ],
  },
  {
    id: 16,
    category: 'Digestion',
    question: 'How often do you experience digestive issues?',
    options: [
      { value: 1, label: 'Frequently — gas, bloating, constipation, irregularity' },
      { value: 3, label: 'Occasionally — heartburn, acidity, loose stools' },
      { value: 5, label: 'Rarely — digestion is slow but generally stable' },
    ],
  },
  {
    id: 17,
    category: 'Digestion',
    question: 'What foods do you naturally crave?',
    options: [
      { value: 1, label: 'Warm, oily, sweet, salty, or sour foods' },
      { value: 3, label: 'Cool, refreshing, sweet, or bitter foods' },
      { value: 5, label: 'Light, dry, spicy, or pungent foods' },
    ],
  },
  {
    id: 18,
    category: 'Appearance',
    question: 'How are your eyes?',
    options: [
      { value: 1, label: 'Small, active, nervous, or dry' },
      { value: 3, label: 'Bright, sharp, penetrating, or sensitive to light' },
      { value: 5, label: 'Large, calm, moist, and attractive' },
    ],
  },
  {
    id: 19,
    category: 'Appearance',
    question: 'How is your voice?',
    options: [
      { value: 1, label: 'Thin, high-pitched, or tends to crack' },
      { value: 3, label: 'Sharp, clear, commanding' },
      { value: 5, label: 'Deep, resonant, melodious' },
    ],
  },
  {
    id: 20,
    category: 'Lifestyle',
    question: 'How would others generally describe you?',
    options: [
      { value: 1, label: 'Creative, imaginative, talkative, sensitive' },
      { value: 3, label: 'Ambitious, focused, critical, organized' },
      { value: 5, label: 'Calm, steady, loyal, easy-going' },
    ],
  },
]

const CATEGORIES = [...new Set(QUESTIONS.map((q) => q.category))]

const DOSHA_INFO = {
  vata: {
    emoji: '💨',
    color: 'var(--vata-color)',
    title: 'Vata Constitution',
    element: 'Air & Space',
    desc: 'Creative, energetic, and adaptable. Vata governs movement, breathing, and all body systems that involve flow and change. In balance, you are lively, creative, and enthusiastic.',
    balance_tips: ['Maintain regular daily routines', 'Prefer warm, oily, nourishing foods', 'Avoid cold, dry environments', 'Practice grounding yoga and meditation'],
  },
  pitta: {
    emoji: '🔥',
    color: 'var(--pitta-color)',
    title: 'Pitta Constitution',
    element: 'Fire & Water',
    desc: 'Intelligent, focused, and naturally leaders. Pitta governs digestion, metabolism, and transformation. In balance, you are sharp, courageous, and filled with clarity.',
    balance_tips: ['Avoid excessive heat and sun', 'Favour cool, sweet, and bitter foods', 'Practice cooling pranayama', 'Allow time for play and relaxation'],
  },
  kapha: {
    emoji: '🌊',
    color: 'var(--kapha-color)',
    title: 'Kapha Constitution',
    element: 'Earth & Water',
    desc: 'Stable, compassionate, and grounded. Kapha governs structure, lubrication, and stability in the body. In balance, you are patient, loyal, nurturing, and deeply loving.',
    balance_tips: ['Wake early and exercise regularly', 'Favour light, spicy, and bitter foods', 'Embrace new experiences and change', 'Practice energising yoga flows'],
  },
}

const stepVariants = {
  enter: (d) => ({ x: d > 0 ? 60 : -60, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (d) => ({ x: d > 0 ? -60 : 60, opacity: 0 }),
}

export default function DoshaQuiz() {
  const [answers, setAnswers] = useState({})
  const [currentQ, setCurrentQ] = useState(0)
  const [direction, setDirection] = useState(1)
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const { updateProfile } = useAuth()
  const navigate = useNavigate()

  const question = QUESTIONS[currentQ]
  const progress = (currentQ / QUESTIONS.length) * 100
  const isAnswered = answers[question.id] !== undefined

  function handleAnswer(value) {
    setAnswers((prev) => ({ ...prev, [question.id]: value }))
    if (currentQ < QUESTIONS.length - 1) {
      setTimeout(() => {
        setDirection(1)
        setCurrentQ((p) => p + 1)
      }, 200)
    }
  }

  function goBack() {
    if (currentQ > 0) {
      setDirection(-1)
      setCurrentQ((p) => p - 1)
    }
  }

  function computeScores() {
    let vata = 0, pitta = 0, kapha = 0
    for (const v of Object.values(answers)) {
      if (v <= 2) vata++
      else if (v === 3) pitta++
      else kapha++
    }
    const total = vata + pitta + kapha || 1
    return {
      vata: Math.round((vata / total) * 100),
      pitta: Math.round((pitta / total) * 100),
      kapha: Math.round((kapha / total) * 100),
    }
  }

  async function handleSubmit() {
    if (Object.keys(answers).length < QUESTIONS.length) {
      setError('Please answer all questions before submitting.')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      const scores = computeScores()
      // Submit to backend
      await profileAPI.submitQuiz(answers)
      // Also update profile with the scores for immediate local state
      await updateProfile({ dosha_scores: scores })
      const dominant = Object.entries(scores).sort((a, b) => b[1] - a[1])[0][0]
      setResult({ scores, dominant })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save quiz result. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    const info = DOSHA_INFO[result.dominant]
    const secondary = Object.entries(result.scores)
      .sort((a, b) => b[1] - a[1])[1][0]
    return (
      <div className="dq-root">
        <Helmet><title>Your Dosha Result | Ayura AI</title></Helmet>
        <div className="dq-orb dq-orb-a" />
        <div className="dq-orb dq-orb-b" />
        <Suspense fallback={null}><LazyParticleField count={40} spread={18} style={{ opacity: 0.3 }} /></Suspense>

        <motion.div
          className="dq-result-shell"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="dq-result-hero" style={{ '--dosha-color': info.color }}>
            <motion.div
              className="dq-result-emoji"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            >
              {info.emoji}
            </motion.div>
            <h1 className="dq-result-title">
              You are primarily <span style={{ color: info.color }}>{result.dominant.charAt(0).toUpperCase() + result.dominant.slice(1)}</span>
            </h1>
            <p className="dq-result-element">{info.element}</p>
          </div>

          <div className="dq-result-body">
            {/* Score bars */}
            <div className="dq-score-bars">
              {Object.entries(result.scores).map(([dosha, pct]) => (
                <div key={dosha} className="dq-score-row">
                  <span className="dq-score-label">{DOSHA_INFO[dosha].emoji} {dosha.charAt(0).toUpperCase() + dosha.slice(1)}</span>
                  <div className="dq-score-track">
                    <motion.div
                      className="dq-score-fill"
                      style={{ background: DOSHA_INFO[dosha].color }}
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                  <span className="dq-score-pct">{pct}%</span>
                </div>
              ))}
            </div>

            <div className="dq-result-desc">
              <p>{info.desc}</p>
            </div>

            <div className="dq-result-secondary">
              <span className="badge badge-primary">Secondary: {DOSHA_INFO[secondary].emoji} {secondary.charAt(0).toUpperCase() + secondary.slice(1)}</span>
            </div>

            <div className="dq-tips">
              <h3>Balance Tips for {result.dominant.charAt(0).toUpperCase() + result.dominant.slice(1)}</h3>
              <ul>
                {info.balance_tips.map((tip, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + i * 0.1 }}
                  >
                    ✓ {tip}
                  </motion.li>
                ))}
              </ul>
            </div>

            <div className="dq-result-actions">
              <motion.button
                className="btn btn-primary btn-lg"
                onClick={() => navigate('/dashboard')}
                whileTap={{ scale: 0.97 }}
              >
                🌿 Generate My Plans →
              </motion.button>
              <motion.button
                className="btn btn-secondary"
                onClick={() => { setResult(null); setAnswers({}); setCurrentQ(0) }}
                whileTap={{ scale: 0.97 }}
              >
                Retake Quiz
              </motion.button>
            </div>
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="dq-root">
      <Helmet><title>Dosha Constitution Quiz | Ayura AI</title></Helmet>
      <div className="dq-orb dq-orb-a" />
      <div className="dq-orb dq-orb-b" />
      <Suspense fallback={null}><LazyParticleField count={30} spread={20} style={{ opacity: 0.25 }} /></Suspense>

      <motion.div
        className="dq-shell"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        {/* Header */}
        <header className="dq-header">
          <button type="button" className="btn btn-secondary dq-back-btn" onClick={() => navigate(-1)}>← Back</button>
          <div className="dq-header-center">
            <h2 className="dq-quiz-title">Prakriti Constitution Quiz</h2>
            <p className="dq-quiz-sub">Question {currentQ + 1} of {QUESTIONS.length}</p>
          </div>
          <div className="dq-category-badge badge badge-primary">{question.category}</div>
        </header>

        {/* Progress track */}
        <div className="dq-progress-track">
          <motion.div
            className="dq-progress-fill"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        {/* Category dots */}
        <div className="dq-cat-dots">
          {CATEGORIES.map((cat) => {
            const catQs = QUESTIONS.filter((q) => q.category === cat)
            const done = catQs.filter((q) => answers[q.id] !== undefined).length
            return (
              <div key={cat} className={`dq-cat-dot-wrap ${done === catQs.length ? 'done' : done > 0 ? 'partial' : ''}`}>
                <div className="dq-cat-dot" />
                <span className="dq-cat-label">{cat}</span>
              </div>
            )
          })}
        </div>

        {/* Question card */}
        <div className="dq-card">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentQ}
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <h3 className="dq-question">{question.question}</h3>
              <div className="dq-options">
                {question.options.map((opt) => {
                  const selected = answers[question.id] === opt.value
                  const doshaHint = opt.value <= 2 ? 'Vata' : opt.value === 3 ? 'Pitta' : 'Kapha'
                  const doshaEmoji = opt.value <= 2 ? '💨' : opt.value === 3 ? '🔥' : '🌊'
                  return (
                    <motion.button
                      key={opt.value}
                      type="button"
                      className={`dq-option ${selected ? 'selected' : ''}`}
                      onClick={() => handleAnswer(opt.value)}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <span className="dq-option-dosha">{doshaEmoji} {doshaHint}</span>
                      <span className="dq-option-text">{opt.label}</span>
                      {selected && <span className="dq-option-check">✓</span>}
                    </motion.button>
                  )
                })}
              </div>
            </motion.div>
          </AnimatePresence>

          {error && (
            <motion.div
              className="dq-error"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {error}
            </motion.div>
          )}
        </div>

        {/* Navigation */}
        <div className="dq-nav">
          {currentQ > 0 && (
            <motion.button type="button" className="btn btn-secondary" onClick={goBack} whileTap={{ scale: 0.97 }}>
              ← Back
            </motion.button>
          )}

          {currentQ < QUESTIONS.length - 1 ? (
            <motion.button
              type="button"
              className="btn btn-primary"
              style={{ flex: 2 }}
              disabled={!isAnswered}
              onClick={() => { setDirection(1); setCurrentQ((p) => p + 1) }}
              whileTap={{ scale: 0.97 }}
            >
              Next →
            </motion.button>
          ) : (
            <motion.button
              type="button"
              className="btn btn-accent btn-full"
              disabled={submitting || Object.keys(answers).length < QUESTIONS.length}
              onClick={handleSubmit}
              whileTap={{ scale: 0.97 }}
            >
              {submitting
                ? <span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
                : '🧬 Reveal My Dosha →'}
            </motion.button>
          )}
        </div>

        <p className="dq-disclaimer">
          Based on classical Ayurvedic Prakriti assessment. This is for wellness guidance only.
        </p>
      </motion.div>
    </div>
  )
}
