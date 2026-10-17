import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { mealsAPI, plansAPI } from '../../../api/client'
import {
  Languages, RefreshCw, ClipboardCheck, ShieldAlert, Check, X,
} from 'lucide-react'

// What a dietitian asks at each review and the meal log cannot know: hunger, how
// digestion went, which food disagreed, and the signs no menu answers. It proposes;
// the weeks still to come are rebuilt only when the patient asks
// (server/services/diet_checkin.py).
const HUNGER = [
  { value: 'hungry', label: 'Hungry between meals', i18n: 'diet.hungerHungry' },
  { value: 'right', label: 'About right', i18n: 'diet.hungerRight' },
  { value: 'too_much', label: 'More than I could eat', i18n: 'diet.hungerTooMuch' },
]
const DIGESTION = [
  { value: 'bloating', label: 'Bloating or gas', i18n: 'diet.digBloating' },
  { value: 'acidity', label: 'Acidity or heartburn', i18n: 'diet.digAcidity' },
  { value: 'constipation', label: 'Constipation', i18n: 'diet.digConstipation' },
  { value: 'loose_stools', label: 'Loose stools', i18n: 'diet.digLoose' },
]
const PROBLEMS = [
  { value: 'bloating', label: 'Bloating', i18n: 'diet.probBloating' },
  { value: 'acidity', label: 'Acidity', i18n: 'diet.probAcidity' },
  { value: 'loose_stools', label: 'Loose stools', i18n: 'diet.probLoose' },
  { value: 'nausea', label: 'Nausea', i18n: 'diet.probNausea' },
  { value: 'itching_rash', label: 'Itching or a rash', i18n: 'diet.probRash' },
  { value: 'did_not_like', label: 'Did not like it', i18n: 'diet.probDislike' },
]
// None of these is answered by a different menu.
const DIET_RED_FLAGS = [
  { value: 'swelling', label: 'Swelling of the lips, face or tongue', i18n: 'diet.flagSwelling' },
  { value: 'breathing', label: 'Wheezing or a tight throat', i18n: 'diet.flagBreathing' },
  { value: 'hives', label: 'Hives over much of the body', i18n: 'diet.flagHives' },
  { value: 'vomiting', label: 'Vomiting again and again', i18n: 'diet.flagVomiting' },
  { value: 'blood_in_stool', label: 'Blood in the stool, or black stool', i18n: 'diet.flagBlood' },
]
const ALLERGY_LABELS = [
  { value: 'dairy', label: 'Dairy', i18n: 'diet.allergyDairy' },
  { value: 'gluten', label: 'Gluten', i18n: 'diet.allergyGluten' },
  { value: 'nuts_tree', label: 'Tree nuts', i18n: 'diet.allergyTreeNuts' },
  { value: 'peanuts', label: 'Peanuts', i18n: 'diet.allergyPeanuts' },
  { value: 'soy', label: 'Soy', i18n: 'diet.allergySoy' },
  { value: 'sesame', label: 'Sesame', i18n: 'diet.allergySesame' },
]
const MAX_TROUBLE = 8
const toggle = (list, v) => (list.includes(v) ? list.filter(x => x !== v) : [...list, v])

function CheckinChanges({ proposal }) {
  const { t } = useTranslation()
  const lines = (proposal?.changes || []).map(c => {
    if (c.kind === 'exclude') return t('diet.ciExclude', '{{foods}} left out', { foods: c.foods.join(', ') })
    if (c.kind === 'digestion') {
      const d = DIGESTION.find(x => x.value === c.condition)
      return t('diet.ciDigestion', 'every meal built for {{condition}}', { condition: d ? t(d.i18n, d.label).toLowerCase() : c.condition })
    }
    if (c.kind === 'light_meals') return t('diet.ciLight', 'light, warm, well-cooked meals')
    if (c.kind === 'energy') return t('diet.ciEnergy', 'energy {{kcal}} kcal a day', { kcal: `${c.kcal > 0 ? '+' : ''}${c.kcal}` })
    return null
  }).filter(Boolean)
  if (!lines.length) return null
  return <ul className="diet-checkin-changes">{lines.map(l => <li key={l}>{l}</li>)}</ul>
}

export function DietWeekCheckin({ planId, week, data, onSaved, onRebuilt }) {
  const { t } = useTranslation()
  const saved = (data?.checkins || []).find(c => c.week === week)
  const foods = data?.week_foods?.[week] || data?.week_foods?.[String(week)] || []
  const latest = (data?.checkins || []).reduce((a, c) => (!a || c.week > a.week ? c : a), null)
  const proposal = latest?.week === week ? data?.proposal : null
  const [open, setOpen] = useState(false)
  const [hunger, setHunger] = useState('right')
  const [digestion, setDigestion] = useState([])
  const [trouble, setTrouble] = useState([])
  const [flags, setFlags] = useState([])
  const [addAllergies, setAddAllergies] = useState([])
  const [state, setState] = useState('idle')

  if (!planId) return null

  const openForm = () => {
    setHunger(saved?.hunger || 'right')
    setDigestion(saved?.digestion || [])
    setTrouble(saved?.trouble_foods || [])
    setFlags(saved?.red_flags || [])
    setAddAllergies([])
    setState('idle')
    setOpen(true)
  }
  const nameOf = (id) => foods.find(f => f.id === id)?.name || id.replace(/_/g, ' ')
  // A reaction can go onto the allergy list — only when the patient ticks it, and
  // only as an allergy that would actually remove the food.
  const reacted = trouble.filter(x => x.problem === 'itching_rash' || flags.length > 0)
  const offerAllergies = [...new Set(reacted.flatMap(x => foods.find(f => f.id === x.food)?.allergies || []))]
  const save = async () => {
    setState('saving')
    try {
      await mealsAPI.checkin({ plan_id: planId, week, hunger, digestion, trouble_foods: trouble,
        red_flags: flags, add_allergies: addAllergies.filter(a => offerAllergies.includes(a)) })
      await onSaved?.()
      setState('idle')
      setOpen(false)
    } catch {
      setState('error')
    }
  }
  const rebuild = async () => {
    setState('rebuilding')
    try {
      const { data: plan } = await plansAPI.rebuildDiet(planId)
      onRebuilt?.(plan)
      setState('idle')
    } catch {
      setState('rebuildError')
    }
  }

  if (!open) {
    return (
      <div className="gym-checkin gym-checkin-closed diet-checkin">
        <span className="gym-checkin-title">
          <ClipboardCheck size={15} /> {saved
            ? t('diet.ciDone', 'Week {{n}} checked in', { n: week })
            : t('diet.ciAsk', 'How was week {{n}}?', { n: week })}
        </span>
        <span className="gym-checkin-sub">
          {saved
            ? (week < 4
              ? t('diet.ciSubDone', 'What you said shapes the weeks still to come.')
              : t('diet.ciSubDoneLast', 'What you said shapes your next plan.'))
            : t('diet.ciSub', 'Half a minute: hunger, digestion, and any food that disagreed with you.')}
        </span>
        {saved?.red_flags?.length > 0 && (
          <p className="gym-checkin-stop" role="alert">
            <ShieldAlert size={14} /> {t('diet.ciSeeDoctor', 'Please see a doctor about what you reported — a different menu does not answer it. If your lips, face or tongue swell or breathing is hard, call 112 now.')}
          </p>
        )}
        {proposal?.changes?.length > 0 && (
          <div className="diet-checkin-proposal">
            <span>{proposal.from_week <= 4
              ? t('diet.ciWould', 'Weeks {{from}}–4 would change:', { from: proposal.from_week })
              : t('diet.ciNext', 'Your next plan will change:')}</span>
            <CheckinChanges proposal={proposal} />
            {proposal.rebuild_available && (
              <button type="button" className="gym-log-save gym-checkin-rebuild" onClick={rebuild}
                disabled={state === 'rebuilding'}>
                <RefreshCw size={12} /> {state === 'rebuilding'
                  ? t('diet.ciRebuilding', 'Rebuilding…')
                  : t('diet.ciRebuild', 'Rebuild weeks {{from}}–4 around it', { from: proposal.from_week })}
              </button>
            )}
            {proposal.rebuild_available && (
              <span className="gym-checkin-sub">{t('diet.ciRebuildNote', 'The weeks you have eaten stay as they are. This uses one plan generation.')}</span>
            )}
            {state === 'rebuildError' && <p className="gym-log-error">{t('diet.ciRebuildFailed', 'Could not rebuild — your plan is unchanged. Try again in a minute.')}</p>}
          </div>
        )}
        <button type="button" className="gym-log-toggle" onClick={openForm}>
          {saved ? t('diet.ciEdit', 'Edit check-in') : t('diet.ciStart', 'Check in')}
        </button>
      </div>
    )
  }

  const unused = foods.filter(f => !trouble.some(x => x.food === f.id))
  return (
    <div className="gym-checkin diet-checkin" role="group" aria-label={t('diet.ciAsk', 'How was week {{n}}?', { n: week })}>
      <span className="gym-checkin-title"><ClipboardCheck size={15} /> {t('diet.ciAsk', 'How was week {{n}}?', { n: week })}</span>

      <p className="gym-checkin-q">{t('diet.ciHungerQ', 'The amount of food was')}</p>
      <div className="gym-log-effort" role="radiogroup" aria-label={t('diet.ciHungerQ', 'The amount of food was')}>
        {HUNGER.map(o => (
          <button key={o.value} type="button" role="radio" aria-checked={hunger === o.value}
            className={`gym-log-chip${hunger === o.value ? ' active' : ''}`}
            onClick={() => setHunger(o.value)}>{t(o.i18n, o.label)}</button>
        ))}
      </div>

      <p className="gym-checkin-q">{t('diet.ciDigestionQ', 'Did you have any of these this week?')}</p>
      <div className="gym-log-effort">
        {DIGESTION.map(o => (
          <button key={o.value} type="button" aria-pressed={digestion.includes(o.value)}
            className={`gym-log-chip${digestion.includes(o.value) ? ' active' : ''}`}
            onClick={() => setDigestion(d => toggle(d, o.value))}>{t(o.i18n, o.label)}</button>
        ))}
      </div>

      <p className="gym-checkin-q">{t('diet.ciFoodQ', 'Did a food from this week disagree with you?')}</p>
      {trouble.map((x, i) => (
        <div key={x.food} className="diet-checkin-food">
          <span>{nameOf(x.food)}</span>
          <select value={x.problem} aria-label={t('diet.ciWhatHappened', 'What happened')}
            onChange={e => setTrouble(tr => tr.map((y, j) => (j === i ? { ...y, problem: e.target.value } : y)))}>
            {PROBLEMS.map(p => <option key={p.value} value={p.value}>{t(p.i18n, p.label)}</option>)}
          </select>
          <button type="button" className="diet-checkin-remove" aria-label={t('diet.ciRemove', 'Remove')}
            onClick={() => setTrouble(tr => tr.filter((_, j) => j !== i))}><X size={12} /></button>
        </div>
      ))}
      {trouble.length < MAX_TROUBLE && unused.length > 0 && (
        <select className="diet-checkin-add" value="" aria-label={t('diet.ciAddFood', 'Add a food')}
          onChange={e => e.target.value && setTrouble(tr => [...tr, { food: e.target.value, problem: 'bloating' }])}>
          <option value="">{t('diet.ciAddFood', 'Add a food')}</option>
          {unused.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
      )}
      {trouble.length > 0 && (
        <span className="gym-checkin-sub">{t('diet.ciFoodNote', 'A food you name here is left out of the coming weeks and your next plan.')}</span>
      )}

      <p className="gym-checkin-q">{t('diet.ciFlagsQ', 'After eating, did any of these happen?')}</p>
      <div className="gym-log-effort">
        {DIET_RED_FLAGS.map(o => (
          <button key={o.value} type="button" aria-pressed={flags.includes(o.value)}
            className={`gym-log-chip gym-checkin-flag${flags.includes(o.value) ? ' active' : ''}`}
            onClick={() => setFlags(f => toggle(f, o.value))}>{t(o.i18n, o.label)}</button>
        ))}
      </div>
      {flags.length > 0 && (
        <p className="gym-checkin-stop" role="alert">
          <ShieldAlert size={14} /> {t('diet.ciSeeDoctor', 'Please see a doctor about what you reported — a different menu does not answer it. If your lips, face or tongue swell or breathing is hard, call 112 now.')}
        </p>
      )}
      {offerAllergies.map(a => {
        const label = ALLERGY_LABELS.find(x => x.value === a)
        return (
          <label key={a} className="gym-checkin-check">
            <input type="checkbox" checked={addAllergies.includes(a)}
              onChange={() => setAddAllergies(l => toggle(l, a))} />
            {t('diet.ciAddAllergy', 'Add {{allergy}} to my allergies, so no plan includes it', { allergy: label ? t(label.i18n, label.label) : a })}
          </label>
        )
      })}

      <div className="gym-log-actions">
        <button type="button" className="gym-log-cancel" onClick={() => setOpen(false)}>{t('diet.cancel', 'Cancel')}</button>
        <button type="button" className="gym-log-save" onClick={save} disabled={state === 'saving'}>
          {state === 'saving' ? t('diet.saving', 'Saving…') : <><Check size={12} /> {t('diet.save', 'Save')}</>}
        </button>
      </div>
      {state === 'error' && <p className="gym-log-error">{t('diet.ciSaveFailed', 'Could not save — check your connection and try again.')}</p>}
    </div>
  )
}

// Languages the plan can be READ in. The plan is generated and safety-checked in
// English; a translation is an overlay of its display text (services/diet_translate.py)
// and never what the checks read, because they cannot read other scripts.
