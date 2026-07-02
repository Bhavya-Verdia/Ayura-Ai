import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router-dom'
import { m, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { plansAPI } from '../api/client'
import { Soup, Pill, Leaf, TriangleAlert, Stethoscope, X } from 'lucide-react'
import './Remedies.css'


// ─── Safety rating config ──────────────────────────────────────────────────
const SAFETY_CONFIG = {
  safe_for_all: {
    label: 'Safe for All',
    color: 'var(--sage)',
    bg: 'rgba(16,185,129,0.12)',
    border: 'rgba(16,185,129,0.3)',
    borderLeft: '#10B981',
    dot: '#10B981',
  },
  safe_for_most: {
    label: 'Safe for Most',
    color: 'var(--primary-light)',
    bg: 'rgba(92,171,116,0.10)',
    border: 'rgba(92,171,116,0.25)',
    borderLeft: '#5cab74',
    dot: '#5cab74',
  },
  generally_safe: {
    label: 'Generally Safe',
    color: 'var(--accent)',
    bg: 'rgba(245,158,11,0.10)',
    border: 'rgba(245,158,11,0.25)',
    borderLeft: '#F59E0B',
    dot: '#F59E0B',
  },
  consult_doctor: {
    label: 'Consult Doctor',
    color: 'var(--rose)',
    bg: 'rgba(244,63,94,0.10)',
    border: 'rgba(244,63,94,0.25)',
    borderLeft: '#F43F5E',
    dot: '#F43F5E',
  },
}

function getSafety(key) {
  return SAFETY_CONFIG[key] || SAFETY_CONFIG.generally_safe
}

// ─── Animation variants ────────────────────────────────────────────────────
const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
}

const cardVariants = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
}



// ─── Skeleton card ─────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="rem-skeleton-card">
      <div className="rem-skeleton-header">
        <div className="skeleton rem-skel-title" />
        <div className="skeleton rem-skel-badge" />
      </div>
      <div className="skeleton rem-skel-sub" />
      <div className="rem-skel-chips">
        {[1, 2, 3].map(i => <div key={i} className="skeleton rem-skel-chip" />)}
      </div>
      <div className="skeleton rem-skel-body" />
      <div className="skeleton rem-skel-body short" />
    </div>
  )
}

// ─── Remedy Card ───────────────────────────────────────────────────────────
function RemedyCard({ remedy }) {
  const [expanded, setExpanded] = useState(false)
  const safety = getSafety(remedy.safety_rating)
  const ingredients = Array.isArray(remedy.ingredients) ? remedy.ingredients : []
  const warnings = Array.isArray(remedy.warnings) ? remedy.warnings : []

  return (
    <m.div
      className="rem-card"
      variants={cardVariants}
      style={{ '--border-left-color': safety.borderLeft }}
      layout
    >
      {/* Header */}
      <div className="rem-card-header">
        <div className="rem-card-title-row">
          <span className="rem-card-icon"><Soup size={20} strokeWidth={2} /></span>
          <div>
            <h3 className="rem-card-name">{remedy.remedy_name || 'Unnamed Remedy'}</h3>
            {remedy.symptom_addressed && (
              <p className="rem-card-symptom">For: {remedy.symptom_addressed}</p>
            )}
          </div>
        </div>
        <div className="rem-safety-badge" style={{ background: safety.bg, border: `1px solid ${safety.border}`, color: safety.color }}>
          <span className="rem-safety-dot" style={{ background: safety.dot }} />
          {safety.label}
        </div>
      </div>

      {/* Ingredients chips */}
      {ingredients.length > 0 && (
        <div className="rem-section">
          <p className="rem-label">Ingredients</p>
          <div className="rem-chips">
            {ingredients.map((ing, i) => (
              <span key={i} className="rem-chip">{ing}</span>
            ))}
          </div>
        </div>
      )}

      {/* Info grid */}
      <div className="rem-info-grid">
        {remedy.dosage && (
          <div className="rem-info-item">
            <span className="rem-info-label">Dosage</span>
            <span className="rem-info-val">{remedy.dosage}</span>
          </div>
        )}
        {remedy.frequency && (
          <div className="rem-info-item">
            <span className="rem-info-label">Frequency</span>
            <span className="rem-info-val">{remedy.frequency}</span>
          </div>
        )}
      </div>

      {/* Preparation — collapsible */}
      {remedy.preparation && (
        <div className="rem-section">
          <p className="rem-label">Preparation</p>
          <p className="rem-text">{remedy.preparation}</p>
        </div>
      )}

      {/* Expand button */}
      <button
        className="rem-expand-btn"
        onClick={() => setExpanded(prev => !prev)}
        aria-expanded={expanded}
      >
        {expanded ? 'Hide details ↑' : 'View details ↓'}
      </button>

      <AnimatePresence>
        {expanded && (
          <m.div
            key="details"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            {remedy.ayurvedic_rationale && (
              <div className="rem-section rem-rationale">
                <p className="rem-label"><Leaf size={14} strokeWidth={2} /> Ayurvedic Rationale</p>
                <p className="rem-text">{remedy.ayurvedic_rationale}</p>
              </div>
            )}

            {warnings.length > 0 && (
              <div className="rem-section rem-warnings-section">
                <p className="rem-label rem-warn-label"><TriangleAlert size={14} strokeWidth={2} /> Warnings</p>
                <ul className="rem-warnings">
                  {warnings.map((w, i) => (
                    <li key={i} className="rem-warning-item">{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </m.div>
        )}
      </AnimatePresence>
    </m.div>
  )
}

// ─── Medicine Card ─────────────────────────────────────────────────────────
function MedicineCard({ medicine }) {
  const [expanded, setExpanded] = useState(false)
  const safety = getSafety(medicine.safety_rating)
  const warnings = Array.isArray(medicine.warnings) ? medicine.warnings : []

  return (
    <m.div
      className="rem-card rem-medicine-card"
      variants={cardVariants}
      style={{ '--border-left-color': safety.borderLeft }}
      layout
    >
      {/* Header */}
      <div className="rem-card-header">
        <div className="rem-card-title-row">
          <span className="rem-card-icon"><Pill size={20} strokeWidth={2} /></span>
          <div>
            <h3 className="rem-card-name">{medicine.medicine_name || 'Unnamed Medicine'}</h3>
            {medicine.symptom_addressed && (
              <p className="rem-card-symptom">For: {medicine.symptom_addressed}</p>
            )}
          </div>
        </div>
        <div className="rem-card-badges">
          {medicine.type && (
            <span className="rem-type-badge">{medicine.type}</span>
          )}
          <div className="rem-safety-badge" style={{ background: safety.bg, border: `1px solid ${safety.border}`, color: safety.color }}>
            <span className="rem-safety-dot" style={{ background: safety.dot }} />
            {safety.label}
          </div>
        </div>
      </div>

      {/* Info grid */}
      <div className="rem-info-grid">
        {medicine.dosage && (
          <div className="rem-info-item">
            <span className="rem-info-label">Dosage</span>
            <span className="rem-info-val">{medicine.dosage}</span>
          </div>
        )}
        {medicine.anupana && (
          <div className="rem-info-item">
            <span className="rem-info-label">Anupana</span>
            <span className="rem-info-val">{medicine.anupana}</span>
          </div>
        )}
      </div>

      {/* Expand */}
      {(warnings.length > 0 || medicine.description) && (
        <button
          className="rem-expand-btn"
          onClick={() => setExpanded(prev => !prev)}
          aria-expanded={expanded}
        >
          {expanded ? 'Hide details ↑' : 'View details ↓'}
        </button>
      )}

      <AnimatePresence>
        {expanded && (
          <m.div
            key="med-details"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            {medicine.description && (
              <div className="rem-section">
                <p className="rem-label">Description</p>
                <p className="rem-text">{medicine.description}</p>
              </div>
            )}
            {warnings.length > 0 && (
              <div className="rem-section rem-warnings-section">
                <p className="rem-label rem-warn-label"><TriangleAlert size={14} strokeWidth={2} /> Warnings</p>
                <ul className="rem-warnings">
                  {warnings.map((w, i) => (
                    <li key={i} className="rem-warning-item">{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </m.div>
        )}
      </AnimatePresence>
    </m.div>
  )
}

// ─── Empty State ───────────────────────────────────────────────────────────
function EmptyState({ tab }) {
  const navigate = useNavigate()
  return (
    <m.div
      className="rem-empty"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="rem-empty-emoji">{tab === 'remedies' ? <Soup size={34} strokeWidth={1.7} /> : <Pill size={34} strokeWidth={1.7} />}</div>
      <h3 className="rem-empty-title">No {tab === 'remedies' ? 'home remedies' : 'medicines'} generated yet</h3>
      <p className="rem-empty-sub">
        Head to your Dashboard and generate a personalized Ayurvedic plan to unlock your custom remedy cabinet.
      </p>
      <m.button
        className="btn btn-primary"
        onClick={() => navigate('/dashboard')}
        whileHover={{ scale: 1.04, y: -2 }}
        whileTap={{ scale: 0.97 }}
      >
        ✦ Go to Dashboard
      </m.button>
    </m.div>
  )
}

// ─── Filter bar ────────────────────────────────────────────────────────────
function FilterBar({ symptoms, activeFilter, onFilter }) {
  if (symptoms.length === 0) return null
  return (
    <div className="rem-filter-bar">
      <button
        className={`rem-filter-chip${activeFilter === '' ? ' active' : ''}`}
        onClick={() => onFilter('')}
      >
        All
      </button>
      {symptoms.map(s => (
        <button
          key={s}
          className={`rem-filter-chip${activeFilter === s ? ' active' : ''}`}
          onClick={() => onFilter(s)}
        >
          {s}
        </button>
      ))}
    </div>
  )
}

// ─── Main Remedies Page ────────────────────────────────────────────────────
const Remedies = () => {
  const navigate = useNavigate()
  const { data, isLoading: loading, error: queryError } = useQuery({
    queryKey: ['latest-plan'],
    queryFn: async () => {
      const res = await plansAPI.getLatest()
      return res.data?.plan_data || {}
    },
    retry: false
  })

  const [activeTab, setActiveTab] = useState('remedies')
  const [filter, setFilter]       = useState('')
  const [errorDismissed, setErrorDismissed] = useState(false)

  const homeRemedies = useMemo(() => Array.isArray(data?.home_remedies) ? data.home_remedies : [], [data])
  const medicines = useMemo(() => Array.isArray(data?.medicines) ? data.medicines : [], [data])
  const error = queryError && !errorDismissed ? (queryError.response?.data?.detail || 'Could not load your latest plan.') : null

  // Collect unique symptoms for filter
  const remedySymptoms = useMemo(() => [
    ...new Set(homeRemedies.map(r => r.symptom_addressed).filter(Boolean))
  ], [homeRemedies])

  const medicineSymptoms = useMemo(() => [
    ...new Set(medicines.map(m => m.symptom_addressed).filter(Boolean))
  ], [medicines])

  const filteredRemedies = useMemo(() =>
    filter ? homeRemedies.filter(r => r.symptom_addressed === filter) : homeRemedies,
    [homeRemedies, filter]
  )

  const filteredMedicines = useMemo(() =>
    filter ? medicines.filter(m => m.symptom_addressed === filter) : medicines,
    [medicines, filter]
  )

  const currentSymptoms = activeTab === 'remedies' ? remedySymptoms : medicineSymptoms
  const currentItems    = activeTab === 'remedies' ? filteredRemedies : filteredMedicines
  const totalItems      = activeTab === 'remedies' ? homeRemedies.length : medicines.length

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    setFilter('')
  }

  return (
    <>
      <Helmet>
        <title>Remedies &amp; Medicines | Ayura AI</title>
        <meta name="description" content="Your personalized Ayurvedic home remedies and classical medicines from your latest wellness plan." />
      </Helmet>

      <div className="rem-root">
        {/* ── Background orbs ─────────────────── */}
        <div className="rem-bg-orb rem-orb-1" aria-hidden />
        <div className="rem-bg-orb rem-orb-2" aria-hidden />

        <div className="rem-container">

          {/* ── Page header ─────────────────────── */}
          <m.div
            className="rem-page-header"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="rem-header-left">
              <button
                className="rem-back-btn"
                onClick={() => navigate('/dashboard')}
                aria-label="Back to dashboard"
              >
                ← Back
              </button>
              <div>
                <h1 className="rem-page-title">
                  <span className="gradient-text">Remedies</span> &amp; Medicines
                </h1>
                <p className="rem-page-sub">Your personal Ayurvedic natural medicine cabinet</p>
              </div>
            </div>
            <div className="rem-header-right">
              <Link to="/dashboard" className="btn btn-secondary btn-sm rem-regen-btn">
                ↻ Regenerate from Dashboard
              </Link>
            </div>
          </m.div>

          {/* ── Disclaimer banner ───────────────── */}
          <m.div
            className="disclaimer rem-disclaimer"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.35 }}
          >
            <span style={{ display: 'inline-flex', flexShrink: 0 }}><Stethoscope size={16} strokeWidth={2} /></span>
            <span>
              These recommendations are AI-generated based on Ayurvedic principles.
              Always consult a qualified healthcare provider before starting any new treatment.
            </span>
          </m.div>

          {/* ── Error bar ───────────────────────── */}
          <AnimatePresence>
            {error && (
              <m.div
                className="rem-error-bar"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><TriangleAlert size={15} strokeWidth={2} /> {error}</span>
                <button onClick={() => setErrorDismissed(true)} aria-label="Dismiss"><X size={14} strokeWidth={2} /></button>
              </m.div>
            )}
          </AnimatePresence>

          {/* ── Tabs ────────────────────────────── */}
          <m.div
            className="rem-tabs-wrapper"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.4 }}
          >
            <div className="tabs rem-tabs" role="tablist">
              <button
                className={`tab${activeTab === 'remedies' ? ' active' : ''}`}
                onClick={() => handleTabChange('remedies')}
                role="tab"
                aria-selected={activeTab === 'remedies'}
              >
                <Soup size={15} strokeWidth={2} /> Home Remedies
                {!loading && homeRemedies.length > 0 && (
                  <span className="rem-tab-count">{homeRemedies.length}</span>
                )}
              </button>
              <button
                className={`tab${activeTab === 'medicines' ? ' active' : ''}`}
                onClick={() => handleTabChange('medicines')}
                role="tab"
                aria-selected={activeTab === 'medicines'}
              >
                <Pill size={15} strokeWidth={2} /> Ayurvedic Medicines
                {!loading && medicines.length > 0 && (
                  <span className="rem-tab-count">{medicines.length}</span>
                )}
              </button>
            </div>
          </m.div>

          {/* ── Filter bar ──────────────────────── */}
          <AnimatePresence mode="wait">
            {!loading && currentSymptoms.length > 0 && (
              <m.div
                key={activeTab + '-filters'}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                <FilterBar
                  symptoms={currentSymptoms}
                  activeFilter={filter}
                  onFilter={setFilter}
                />
              </m.div>
            )}
          </AnimatePresence>

          {/* ── Content area ────────────────────── */}
          <AnimatePresence mode="wait">
            {loading ? (
              <m.div
                key="skeletons"
                className="rem-cards-grid"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
              </m.div>
            ) : totalItems === 0 ? (
              <m.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <EmptyState tab={activeTab} />
              </m.div>
            ) : (
              <m.div
                key={activeTab + '-' + filter}
                className="rem-cards-grid"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0 }}
              >
                <AnimatePresence>
                  {activeTab === 'remedies'
                    ? filteredRemedies.map((remedy, i) => (
                        <RemedyCard key={remedy.remedy_name + i} remedy={remedy} index={i} />
                      ))
                    : filteredMedicines.map((med, i) => (
                        <MedicineCard key={med.medicine_name + i} medicine={med} index={i} />
                      ))
                  }
                </AnimatePresence>

                {/* No results for filter */}
                {currentItems.length === 0 && filter && (
                  <m.div
                    className="rem-no-filter-results"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <p>No {activeTab === 'remedies' ? 'remedies' : 'medicines'} found for "{filter}".</p>
                    <button className="rem-filter-chip active" onClick={() => setFilter('')}>
                      Clear filter
                    </button>
                  </m.div>
                )}
              </m.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  )
}

export default Remedies
