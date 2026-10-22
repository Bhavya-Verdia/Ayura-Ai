import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { FlaskConical, Plus, X, Trash2, ChevronDown, ChevronUp, TriangleAlert } from 'lucide-react'
import { labsAPI } from '../api/client'
import LabReportUpload from './LabReportUpload'
import { tr } from '../lib/tr'
import { Trans } from 'react-i18next'
import './LabResults.css'

// Lab results the patient enters from their report. The band each value is read
// against comes from the server (services/lab_results.py), never from here, so the
// two cannot disagree. No analytics event is sent from this component: a test name
// alone (HbA1c, TSH) says which condition someone is being checked for.

const STATUS_TEXT = { normal: 'Normal', borderline: 'Borderline', low: 'Low', high: 'High', unclassified: 'Not classified' }
const today = () => new Date().toLocaleDateString('en-CA') // YYYY-MM-DD, local

function ResultRow({ r, onDelete, deleting }) {
  return (
    <li className="lab-history-row">
      <span>{r.taken_on}</span>
      <span className="lab-history-val">{r.value} {r.unit}</span>
      <span className={`lab-pill lab-pill--${r.status}`}>{STATUS_TEXT[r.status]}</span>
      <button type="button" className="lab-icon-btn" aria-label={tr('ui.labResults.deleteResultFrom', 'Delete {{label}} result from {{taken_on}}', { label: r.label, taken_on: r.taken_on })}
        disabled={deleting} onClick={() => onDelete(r.id)}>
        <Trash2 size={14} />
      </button>
    </li>
  )
}

export default function LabResults() {
  const qc = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [open, setOpen] = useState(null)
  const [form, setForm] = useState({ test: '', value: '', taken_on: today(), note: '' })
  const [error, setError] = useState('')

  // Both payloads are guarded: an error body or a cached junk value must reach the
  // empty state, not throw and take the whole Progress page into the error boundary.
  const { data: catalogue = [] } = useQuery({
    queryKey: ['labs-catalogue'],
    queryFn: () => labsAPI.catalogue().then(r => r.data),
    select: (d) => (Array.isArray(d) ? d : []),
    staleTime: 24 * 60 * 60 * 1000,
  })
  const { data, isLoading } = useQuery({
    queryKey: ['labs'],
    queryFn: () => labsAPI.list().then(r => r.data),
    staleTime: 60 * 1000,
  })
  const latest = Array.isArray(data?.latest) ? data.latest : []
  const history = Array.isArray(data?.history) ? data.history : []

  const groups = useMemo(() => {
    const out = {}
    for (const t of catalogue) (out[t.group] ||= []).push(t)
    return out
  }, [catalogue])
  const spec = catalogue.find(t => t.key === form.test)

  const add = useMutation({
    mutationFn: (payload) => labsAPI.add(payload),
    onSuccess: ({ data: r }) => {
      qc.invalidateQueries({ queryKey: ['labs'] })
      setForm({ test: '', value: '', taken_on: today(), note: '' })
      setAdding(false)
      setError('')
      if (r.urgent) toast.warning(`${r.label}: ${r.advice}`, { duration: 10000 })
      else toast.success(tr('ui.labResults.resultSaved', 'Result saved'))
    },
    onError: (e) => setError(e.response?.data?.detail?.toString?.() || 'Could not save that result.'),
  })
  const remove = useMutation({
    mutationFn: (id) => labsAPI.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['labs'] }),
    onError: () => toast.error(tr('ui.labResults.couldNotDeleteThatResult', 'Could not delete that result.')),
  })

  function submit(e) {
    e.preventDefault()
    setError('')
    const value = parseFloat(form.value)
    if (!form.test || Number.isNaN(value)) { setError(tr('ui.labResults.chooseATestAndEnter', 'Choose a test and enter its value.')); return }
    if (spec && (value < spec.min || value > spec.max)) {
      setError(tr('ui.labResults.isUsuallyBetweenAndPlease', '{{label}} is usually between {{min}} and {{max}} {{unit}} — please check the value and the unit on your report.', { label: spec.label, min: spec.min, max: spec.max, unit: spec.unit }))
      return
    }
    add.mutate({ test: form.test, value, taken_on: form.taken_on, note: form.note || undefined })
  }

  return (
    <section className="lab-section" aria-labelledby="lab-title">
      <div className="lab-head">
        <h2 id="lab-title" className="lab-title"><FlaskConical size={18} />{' '}{tr('ui.labResults.labResults', 'Lab results')}</h2>
        <button type="button" className="btn btn-secondary lab-add-btn" onClick={() => { setAdding(v => !v); setError('') }}>
          {adding ? <><X size={15} />{' '}{tr('ui.labResults.cancel', 'Cancel')}</> : <><Plus size={15} />{' '}{tr('ui.labResults.addAResult', 'Add a result')}</>}
        </button>
      </div>
      <p className="lab-sub">
        {tr('ui.labResults.uploadYourLabReportOr', 'Upload your lab report or add results by hand. Each one is shown against its published range and goes into the summary you can share with your Vaidya. They do not change your plans.')}
      </p>

      {!adding && <LabReportUpload />}

      {adding && (
        <form className="lab-form" onSubmit={submit}>
          <div className="input-group">
            <label htmlFor="lab-test">{tr('ui.labResults.test', 'Test')}</label>
            <select id="lab-test" value={form.test} onChange={e => setForm(f => ({ ...f, test: e.target.value }))} required>
              <option value="">{tr('ui.labResults.chooseATest', 'Choose a test…')}</option>
              {Object.entries(groups).map(([g, tests]) => (
                <optgroup key={g} label={g}>
                  {tests.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="lab-form-row">
            <div className="input-group">
              <label htmlFor="lab-value"><Trans i18nKey="ui.labResults.value" defaults={"Value{{value}}"} values={{ value: spec ? ` (${spec.unit})` : '' }} /></label>
              {/* No min/max here: the browser's own range popup would block the
                  submit before the message below, which names the unit, could show. */}
              <input id="lab-value" type="number" step="any" inputMode="decimal" required
                value={form.value} onChange={e => setForm(f => ({ ...f, value: e.target.value }))} />
            </div>
            <div className="input-group">
              <label htmlFor="lab-date">{tr('ui.labResults.dateOfTheTest', 'Date of the test')}</label>
              <input id="lab-date" type="date" required max={today()}
                value={form.taken_on} onChange={e => setForm(f => ({ ...f, taken_on: e.target.value }))} />
            </div>
          </div>
          {spec && <p className="lab-unit-hint"><Trans i18nKey="ui.labResults.enterItInAsPrinted" defaults={"Enter it in {{unit}}, as printed on your report."} values={{ unit: spec.unit }} /></p>}
          <div className="input-group">
            <label htmlFor="lab-note">{tr('ui.labResults.noteOptional', 'Note (optional)')}</label>
            <input id="lab-note" type="text" maxLength={200} placeholder={tr('ui.labResults.eGFastingAfterStarting', 'e.g. fasting, after starting a new medicine')}
              value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} />
          </div>
          {error && <p className="lab-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn-primary" disabled={add.isPending}>
            {add.isPending ? tr('ui.labResults.saving', 'Saving…') : tr('ui.labResults.saveResult', 'Save result')}
          </button>
        </form>
      )}

      {!isLoading && latest.length === 0 && !adding && (
        <p className="lab-empty">{tr('ui.labResults.noResultsYetHba1cTsh', 'No results yet. HbA1c, TSH, haemoglobin, cholesterol and blood pressure are good ones to start with.')}</p>
      )}

      {latest.length > 0 && (
        <ul className="lab-list">
          {latest.map(r => {
            const rows = history.filter(h => h.test === r.test)
            const isOpen = open === r.test
            return (
              <li key={r.test} className={`lab-card${r.urgent ? ' is-urgent' : ''}`}>
                <div className="lab-card-main">
                  <div>
                    <div className="lab-card-name">{r.label}</div>
                    <div className="lab-card-date">{r.taken_on}</div>
                  </div>
                  <div className="lab-card-right">
                    <div className="lab-card-val">{r.value} <span>{r.unit}</span></div>
                    <span className={`lab-pill lab-pill--${r.status}`}>{STATUS_TEXT[r.status]}</span>
                  </div>
                </div>
                <p className="lab-card-reading">{r.reading}</p>
                {r.advice && (
                  <p className={`lab-card-advice${r.urgent ? ' is-urgent' : ''}`}>
                    {r.urgent && <TriangleAlert size={13} />} {r.advice}
                  </p>
                )}
                {rows.length > 0 && (
                  <button type="button" className="lab-toggle" aria-expanded={isOpen}
                    onClick={() => setOpen(isOpen ? null : r.test)}>
                    {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />} {rows.length === 1 ? tr('ui.labResults.n1Result', '1 result') : `${rows.length} results`}
                  </button>
                )}
                {isOpen && (
                  <ul className="lab-history">
                    {rows.map(h => <ResultRow key={h.id} r={h} onDelete={id => remove.mutate(id)} deleting={remove.isPending} />)}
                  </ul>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

