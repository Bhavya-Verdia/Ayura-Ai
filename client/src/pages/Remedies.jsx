import { useContext, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { m, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { toast } from 'sonner'
import { plansAPI, preferencesAPI } from '../api/client'
import { AuthContext } from '../providers/AuthContext'
import PreferencesModal from '../components/PreferencesModal'
import { RemedyView } from '../components/planViews/RemedyView'
import { MedicineView } from '../components/planViews/MedicineView'
import {
  Soup, Pill, Stethoscope, TriangleAlert, X, SlidersHorizontal, Sparkles, RefreshCw, Check,
} from 'lucide-react'
import '../components/PlanViewer.css'   // rv-* / mv-* styles for the shared plan views
import './Remedies.css'

// This page is the canonical home for remedies + medicines. It renders the SAME
// RemedyView / MedicineView that PlanViewer uses, so there is one renderer per
// feature and no second, thinner copy to drift out of sync — the previous
// bespoke card set silently dropped doctor referrals, recovery guidelines and
// the dosage schedule. What this page adds on top is the symptom picker (the
// only place symptoms can be chosen — /plans/remedies 422s without them) and
// aggregation: the newest remedies plan and the newest medicines plan side by
// side, which a single-plan view cannot show.

const SEVERITIES = [
  { id: 'mild',     label: 'Mild' },
  { id: 'moderate', label: 'Moderate' },
  { id: 'severe',   label: 'Severe' },
]

const DURATIONS = [
  { id: 'recent', label: 'A few days' },
  { id: 'weeks',  label: 'Weeks' },
  { id: 'months', label: 'Months' },
  { id: 'chronic',label: 'Chronic' },
]

// Covers every `symptom_category` in the remedy KB; anything new falls back to
// the raw id with underscores stripped.
const CATEGORY_LABELS = {
  digestive: 'Digestion', pain: 'Pain', skin: 'Skin & Hair', respiratory: 'Respiratory',
  immunity: 'Immunity', energy: 'Energy & Sleep', mental: 'Mind & Mood',
  womens_health: "Women's Health", general: 'General',
}

const asList = (v) => (Array.isArray(v) ? v : [])

// The per-feature endpoints are inconsistent about wrapping: /plans/medicines
// stores `plan_data = { medicines: {...} }` while /plans/remedies stores the plan
// flat, and a holistic plan nests both under `home_remedies` / `medicines`. Try
// the envelope first, then accept a flat body — using the same field guards
// PlanViewer uses to decide a dedicated view can render it.
function unwrap(planData, key) {
  const inner = planData?.[key]
  if (inner && typeof inner === 'object' && !Array.isArray(inner)) return inner
  return null
}

// ─── Symptom picker ────────────────────────────────────────────────────────
function SymptomPicker({ options, selected, severity, duration, onToggle, onSeverity, onDuration, onGenerate, generating, hasPlan }) {
  const grouped = useMemo(() => {
    const by = {}
    for (const o of options) (by[o.category] ||= []).push(o)
    return Object.entries(by)
  }, [options])

  const byId = useMemo(() => Object.fromEntries(options.map(o => [o.id, o])), [options])

  return (
    <m.div
      className="rem-picker"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      style={{ overflow: 'hidden' }}
    >
      <div className="rem-picker-inner">
        <div className="rem-picker-head">
          <h2 className="rem-picker-title">What would you like remedies for?</h2>
          <p className="rem-picker-sub">
            Pick your symptoms, then set how strong and how long-standing each one is —
            severity and duration change which remedy you get, and severe symptoms are
            referred to a doctor instead.
          </p>
        </div>

        {grouped.map(([cat, items]) => (
          <div key={cat} className="rem-picker-group">
            <p className="rem-picker-group-label">{CATEGORY_LABELS[cat] || cat.replace(/_/g, ' ')}</p>
            <div className="rem-picker-chips">
              {items.map(o => {
                const on = selected.includes(o.id)
                return (
                  <button
                    key={o.id}
                    type="button"
                    className={`rem-filter-chip${on ? ' active' : ''}`}
                    aria-pressed={on}
                    onClick={() => onToggle(o.id)}
                  >
                    {on && <Check size={13} strokeWidth={2.5} />} {o.display}
                  </button>
                )
              })}
            </div>
          </div>
        ))}

        {selected.length > 0 && (
          <div className="rem-picker-detail">
            <p className="rem-picker-group-label">Tell us about each one</p>
            {selected.map(id => (
              <div key={id} className="rem-picker-row">
                <span className="rem-picker-row-name">{byId[id]?.display || id}</span>
                <div className="rem-picker-row-controls">
                  <div className="rem-seg" role="group" aria-label={`Severity for ${byId[id]?.display || id}`}>
                    {SEVERITIES.map(s => (
                      <button
                        key={s.id}
                        type="button"
                        className={`rem-seg-btn${(severity[id] || 'mild') === s.id ? ' active' : ''}`}
                        aria-pressed={(severity[id] || 'mild') === s.id}
                        onClick={() => onSeverity(id, s.id)}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                  <select
                    className="rem-picker-select"
                    aria-label={`Duration for ${byId[id]?.display || id}`}
                    value={duration[id] || 'recent'}
                    onChange={(e) => onDuration(id, e.target.value)}
                  >
                    {DURATIONS.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
                  </select>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="rem-picker-actions">
          <m.button
            type="button"
            className="btn btn-primary"
            disabled={selected.length === 0 || generating}
            onClick={onGenerate}
            whileHover={selected.length ? { scale: 1.03, y: -1 } : undefined}
            whileTap={selected.length ? { scale: 0.98 } : undefined}
          >
            {generating
              ? <><RefreshCw size={15} strokeWidth={2} className="rem-spin" /> Building your remedies…</>
              : <><Sparkles size={15} strokeWidth={2} /> {hasPlan ? 'Rebuild remedies' : 'Get my remedies'}</>}
          </m.button>
          {selected.length > 0 && (
            <span className="rem-picker-count">{selected.length} selected</span>
          )}
        </div>
      </div>
    </m.div>
  )
}

// ─── Empty state ───────────────────────────────────────────────────────────
function EmptyState({ tab, onAction, busy }) {
  return (
    <m.div
      className="rem-empty"
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="rem-empty-emoji">
        {tab === 'remedies' ? <Soup size={34} strokeWidth={1.7} /> : <Pill size={34} strokeWidth={1.7} />}
      </div>
      <h3 className="rem-empty-title">
        {tab === 'remedies' ? 'No home remedies yet' : 'No medicines yet'}
      </h3>
      <p className="rem-empty-sub">
        {tab === 'remedies'
          ? 'Tell us what is bothering you and we will build kitchen remedies matched to your dosha, conditions and medications.'
          : 'Generate a classical formulation plan matched to your Vikriti, Agni and current medications.'}
      </p>
      <m.button
        className="btn btn-primary"
        onClick={onAction}
        disabled={busy}
        whileHover={{ scale: 1.04, y: -2 }}
        whileTap={{ scale: 0.97 }}
      >
        {busy
          ? <><RefreshCw size={15} strokeWidth={2} className="rem-spin" /> Working…</>
          : tab === 'remedies'
            ? <><SlidersHorizontal size={15} strokeWidth={2} /> Choose symptoms</>
            : <><Sparkles size={15} strokeWidth={2} /> Generate medicines</>}
      </m.button>
    </m.div>
  )
}

function SkeletonBlock() {
  return (
    <div className="rem-skeleton-card">
      <div className="rem-skeleton-header">
        <div className="skeleton rem-skel-title" />
        <div className="skeleton rem-skel-badge" />
      </div>
      <div className="skeleton rem-skel-body" />
      <div className="skeleton rem-skel-body short" />
    </div>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────
const Remedies = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  // `user` is a slim mapping (id/name/dosha); the full record with
  // current_symptoms lives on `profile`.
  const { profile } = useContext(AuthContext)
  const [searchParams, setSearchParams] = useSearchParams()

  const activeTab = searchParams.get('tab') === 'medicines' ? 'medicines' : 'remedies'
  const [filter, setFilter] = useState('')
  const [pickerOpen, setPickerOpen] = useState(false)
  const [errorDismissed, setErrorDismissed] = useState(false)
  const [prefModalOpen, setPrefModalOpen] = useState(false)
  // Picker state is DERIVED from the seed below until the user touches it —
  // `null` means "still following the seed". Syncing it in an effect instead
  // would be a cascading render (and is banned by the compiler lint).
  const [pickedIds, setPickedIds] = useState(null)
  const [severityEdits, setSeverityEdits] = useState({})
  const [durationEdits, setDurationEdits] = useState({})

  const { data, isLoading: loading, error: queryError } = useQuery({
    queryKey: ['remedies-source-plans'],
    queryFn: async () => {
      const res = await plansAPI.getHistory(50)
      const items = asList(res.data?.items ?? res.data)
      const newestData = (type) =>
        items
          .filter((i) => i.plan_type === type)
          .sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)))[0]?.plan_data
      const remedyPd   = newestData('remedies')
      const medicinePd = newestData('medicines')
      const holisticPd = newestData('holistic')
      return {
        remedyPlan:
          unwrap(remedyPd, 'home_remedies') ||
          (remedyPd?.symptoms_addressed || remedyPd?.doctor_referrals ? remedyPd : null) ||
          unwrap(holisticPd, 'home_remedies'),
        medicinePlan:
          unwrap(medicinePd, 'medicines') ||
          (medicinePd?.primary_formulations || medicinePd?.supporting_formulations ? medicinePd : null) ||
          unwrap(holisticPd, 'medicines'),
      }
    },
    retry: false,
  })

  const { data: symptomOptions = [] } = useQuery({
    queryKey: ['remedy-symptoms'],
    queryFn: async () => asList((await plansAPI.getRemedySymptoms()).data?.items),
    staleTime: 24 * 60 * 60 * 1000,   // static KB vocabulary
    retry: false,
  })

  const remedyPlan   = data?.remedyPlan || null
  const medicinePlan = data?.medicinePlan || null

  const addressed = useMemo(() => asList(remedyPlan?.symptoms_addressed), [remedyPlan])
  const medicineCount = useMemo(
    () => asList(medicinePlan?.primary_formulations).length + asList(medicinePlan?.supporting_formulations).length,
    [medicinePlan]
  )

  // Seed the picker from the last plan when there is one, otherwise from the
  // symptoms captured at onboarding/check-in — but only ids the engine can
  // actually match, since those pickers use a plain-language vocabulary.
  const seed = useMemo(() => {
    const valid = new Set(symptomOptions.map(o => o.id))
    const previous = addressed.filter(e => valid.has(e.symptom_id))
    if (previous.length > 0) {
      return {
        ids: previous.map(e => e.symptom_id),
        severity: Object.fromEntries(previous.map(e => [e.symptom_id, e.severity || 'mild'])),
      }
    }
    return { ids: asList(profile?.current_symptoms).filter(id => valid.has(id)), severity: {} }
  }, [symptomOptions, addressed, profile?.current_symptoms])

  const selected = pickedIds ?? seed.ids
  const severity = useMemo(() => ({ ...seed.severity, ...severityEdits }), [seed.severity, severityEdits])
  const duration = durationEdits

  const invalidatePlans = () => {
    queryClient.invalidateQueries({ queryKey: ['remedies-source-plans'] })
    queryClient.invalidateQueries({ queryKey: ['plans-history'] })   // Dashboard cards
  }

  const remedyMutation = useMutation({
    mutationFn: () => plansAPI.generateRemedies({ symptoms: selected, severity, duration }),
    onSuccess: () => {
      invalidatePlans()
      setPickerOpen(false)
      setFilter('')
      toast.success('Your remedies are ready ✦')
    },
    onError: (err) => {
      if (err.response?.status === 429) {
        toast.error('Rate limit reached — wait a minute before requesting another medical plan.')
        return
      }
      toast.error(err.response?.data?.detail || 'Could not build your remedies. Please try again.')
    },
  })

  const medicineMutation = useMutation({
    mutationFn: async (forceRegenerate = false) => {
      // Medicines are driven by saved preferences (allopathic meds, Ama, access),
      // not symptoms — collect them first, exactly like the Dashboard flow.
      const prefRes = await preferencesAPI.getFeature('medicines')
      if (!prefRes.data.is_set) {
        const err = new Error('PREF_REQUIRED')
        err.prefRequired = true
        throw err
      }
      return plansAPI.generateMedicines(forceRegenerate)
    },
    onSuccess: () => {
      invalidatePlans()
      toast.success('Your medicines plan is ready ✦')
    },
    onError: (err) => {
      if (err.prefRequired) {
        setPrefModalOpen(true)
        return
      }
      if (err.response?.status === 429) {
        toast.error('Rate limit reached — wait a minute before requesting another medical plan.')
        return
      }
      toast.error(err.response?.data?.detail || 'Could not generate your medicines plan. Please try again.')
    },
  })

  const error = queryError && !errorDismissed
    ? (queryError.response?.data?.detail || 'Could not load your plans.')
    : null

  // Filter chips act on the remedy list only — doctor referrals stay visible
  // whatever is filtered, since they are the "see someone about this" signal.
  const symptomFilters = useMemo(
    () => [...new Set(addressed.map(e => e.symptom_display).filter(Boolean))],
    [addressed]
  )

  const shownRemedyPlan = useMemo(() => {
    if (!remedyPlan || !filter) return remedyPlan
    return { ...remedyPlan, symptoms_addressed: addressed.filter(e => e.symptom_display === filter) }
  }, [remedyPlan, addressed, filter])

  const setTab = (tab) => {
    setFilter('')
    setSearchParams(tab === 'medicines' ? { tab: 'medicines' } : {}, { replace: true })
  }

  const toggleSymptom = (id) =>
    setPickedIds(selected.includes(id) ? selected.filter(s => s !== id) : [...selected, id])

  const busy = activeTab === 'remedies' ? remedyMutation.isPending : medicineMutation.isPending

  return (
    <>
      <Helmet>
        <title>Remedies &amp; Medicines | Ayura AI</title>
        <meta name="description" content="Your personalized Ayurvedic home remedies and classical medicines — matched to your dosha, conditions and current medications." />
      </Helmet>

      <PreferencesModal
        isOpen={prefModalOpen}
        typeId="medicines"
        onClose={() => setPrefModalOpen(false)}
        onSubmitSuccess={() => {
          setPrefModalOpen(false)
          medicineMutation.mutate(false)
        }}
      />

      <div className="rem-root">
        <div className="rem-bg-orb rem-orb-1" aria-hidden />
        <div className="rem-bg-orb rem-orb-2" aria-hidden />

        <div className="rem-container">

          {/* ── Page header ── */}
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
                <p className="rem-page-sub">Your personal Ayurvedic medicine cabinet</p>
              </div>
            </div>
            <div className="rem-header-right">
              {activeTab === 'remedies' ? (
                <button
                  className="btn btn-secondary btn-sm rem-regen-btn"
                  onClick={() => setPickerOpen(o => !o)}
                  aria-expanded={pickerOpen}
                >
                  <SlidersHorizontal size={14} strokeWidth={2} />
                  {pickerOpen ? 'Hide symptoms' : remedyPlan ? 'Update symptoms' : 'Choose symptoms'}
                </button>
              ) : (
                <button
                  className="btn btn-secondary btn-sm rem-regen-btn"
                  onClick={() => medicineMutation.mutate(!!medicinePlan)}
                  disabled={medicineMutation.isPending}
                >
                  {medicineMutation.isPending
                    ? <><RefreshCw size={14} strokeWidth={2} className="rem-spin" /> Generating…</>
                    : <><RefreshCw size={14} strokeWidth={2} /> {medicinePlan ? 'Regenerate' : 'Generate'}</>}
                </button>
              )}
            </div>
          </m.div>

          {/* ── Disclaimer ── */}
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

          {/* ── Error bar ── */}
          <AnimatePresence>
            {error && (
              <m.div
                className="rem-error-bar"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <TriangleAlert size={15} strokeWidth={2} /> {error}
                </span>
                <button onClick={() => setErrorDismissed(true)} aria-label="Dismiss"><X size={14} strokeWidth={2} /></button>
              </m.div>
            )}
          </AnimatePresence>

          {/* ── Tabs ── */}
          <m.div
            className="rem-tabs-wrapper"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.4 }}
          >
            <div className="tabs rem-tabs" role="tablist">
              <button
                className={`tab${activeTab === 'remedies' ? ' active' : ''}`}
                onClick={() => setTab('remedies')}
                role="tab"
                aria-selected={activeTab === 'remedies'}
              >
                <Soup size={15} strokeWidth={2} /> Home Remedies
                {!loading && addressed.length > 0 && <span className="rem-tab-count">{addressed.length}</span>}
              </button>
              <button
                className={`tab${activeTab === 'medicines' ? ' active' : ''}`}
                onClick={() => setTab('medicines')}
                role="tab"
                aria-selected={activeTab === 'medicines'}
              >
                <Pill size={15} strokeWidth={2} /> Ayurvedic Medicines
                {!loading && medicineCount > 0 && <span className="rem-tab-count">{medicineCount}</span>}
              </button>
            </div>
          </m.div>

          {/* ── Symptom picker (remedies only) ── */}
          <AnimatePresence>
            {activeTab === 'remedies' && pickerOpen && symptomOptions.length > 0 && (
              <SymptomPicker
                options={symptomOptions}
                selected={selected}
                severity={severity}
                duration={duration}
                onToggle={toggleSymptom}
                onSeverity={(id, v) => setSeverityEdits(s => ({ ...s, [id]: v }))}
                onDuration={(id, v) => setDurationEdits(d => ({ ...d, [id]: v }))}
                onGenerate={() => remedyMutation.mutate()}
                generating={remedyMutation.isPending}
                hasPlan={!!remedyPlan}
              />
            )}
          </AnimatePresence>

          {/* ── Symptom filter (remedies only) ── */}
          <AnimatePresence mode="wait">
            {activeTab === 'remedies' && !loading && symptomFilters.length > 1 && (
              <m.div
                key="filters"
                className="rem-filter-bar"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                <button
                  className={`rem-filter-chip${filter === '' ? ' active' : ''}`}
                  onClick={() => setFilter('')}
                >
                  All
                </button>
                {symptomFilters.map(s => (
                  <button
                    key={s}
                    className={`rem-filter-chip${filter === s ? ' active' : ''}`}
                    onClick={() => setFilter(s)}
                  >
                    {s}
                  </button>
                ))}
              </m.div>
            )}
          </AnimatePresence>

          {/* ── Content ── */}
          <AnimatePresence mode="wait">
            {loading ? (
              <m.div key="skeletons" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
                {[1, 2, 3].map(i => <SkeletonBlock key={i} />)}
              </m.div>
            ) : activeTab === 'remedies' ? (
              shownRemedyPlan ? (
                <m.div
                  key={'remedies-' + filter}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                >
                  <RemedyView plan={shownRemedyPlan} />
                </m.div>
              ) : (
                <m.div key="empty-remedies" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <EmptyState tab="remedies" busy={busy} onAction={() => setPickerOpen(true)} />
                </m.div>
              )
            ) : medicinePlan ? (
              <m.div
                key="medicines"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              >
                <MedicineView plan={medicinePlan} />
              </m.div>
            ) : (
              <m.div key="empty-medicines" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <EmptyState tab="medicines" busy={busy} onAction={() => medicineMutation.mutate(false)} />
              </m.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  )
}

export default Remedies
