import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { FileUp, Check, X, Info } from 'lucide-react'
import { labsAPI } from '../api/client'

import { tr } from '../lib/tr'
import { Trans } from 'react-i18next'
// Upload a lab report; the server reads it into a preview (services/lab_report_reader.py)
// and NOTHING is saved until the person has looked at every row here and pressed Save.
// A misread digit on a health value changes what they are told, so the review is the
// point of the feature, not a formality.

const MAX_SIDE = 2400
const MAX_BYTES = 2.5 * 1024 * 1024

// Phone photos are routinely 4-8 MB, over the server's 5 MB cap. Downscale to a JPEG
// that still reads clearly; PDFs are sent as they are.
async function prepare(file) {
  if (!file.type.startsWith('image/') || (file.size <= MAX_BYTES && file.type !== 'image/heic')) return file
  const bitmap = await createImageBitmap(file).catch(() => null)
  if (!bitmap) return file
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg', 0.85))
  return blob ? new File([blob], 'report.jpg', { type: 'image/jpeg' }) : file
}

const today = () => new Date().toLocaleDateString('en-CA')

export default function LabReportUpload({ onDone }) {
  const qc = useQueryClient()
  const input = useRef(null)
  const [reading, setReading] = useState(false)
  const [preview, setPreview] = useState(null)
  const [rows, setRows] = useState([])
  const [date, setDate] = useState(today())
  const [error, setError] = useState('')

  async function pick(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setError('')
    setReading(true)
    try {
      const { data } = await labsAPI.read(await prepare(file))
      setPreview(data)
      setDate(data.report_date || today())
      setRows((data.results || []).map(r => ({
        ...r,
        include: r.value != null && !r.issue,
        input: r.value != null ? String(r.value) : '',
      })))
    } catch (err) {
      setError(err.response?.data?.detail?.toString?.() || 'We could not read that file. Try again, or add results by hand.')
    } finally {
      setReading(false)
    }
  }

  const save = useMutation({
    mutationFn: (payload) => labsAPI.bulk(payload),
    onSuccess: ({ data }) => {
      qc.invalidateQueries({ queryKey: ['labs'] })
      const urgent = (data.saved || []).filter(r => r.urgent)
      if (urgent.length) toast.warning((urgent.length === 1
        ? tr('ui.labReportUpload.urgentOne', '{{tests}}: contact a doctor today about this result.', { tests: urgent.map(r => r.label).join(', ') })
        : tr('ui.labReportUpload.urgentMany', '{{tests}}: contact a doctor today about these results.', { tests: urgent.map(r => r.label).join(', ') })), { duration: 10000 })
      else toast.success((data.saved.length === 1 ? tr('ui.labReportUpload.resultSavedOne', '1 result saved') : tr('ui.labReportUpload.resultSavedMany', '{{count}} results saved', { count: data.saved.length })))
      setPreview(null)
      onDone?.()
    },
    onError: (err) => setError(err.response?.data?.detail?.toString?.() || 'Could not save those results.'),
  })

  const chosen = rows.filter(r => r.include)
  function submit() {
    setError('')
    const results = []
    for (const r of chosen) {
      const v = parseFloat(r.input)
      if (Number.isNaN(v)) { setError(tr('ui.labReportUpload.enterANumberForOr', 'Enter a number for {{label}}, or untick it.', { label: r.label })); return }
      results.push({ test: r.test, value: v })
    }
    save.mutate({ taken_on: date, results, note: tr('ui.labReportUpload.fromAnUploadedReport', 'From an uploaded report') })
  }
  const update = (i, patch) => setRows(rs => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)))

  return (
    <div className="lab-upload">
      <input ref={input} type="file" hidden accept="application/pdf,image/jpeg,image/png,image/webp,image/heic" onChange={pick} />
      {!preview && (
        <>
          <button type="button" className="btn btn-secondary lab-add-btn" disabled={reading} onClick={() => input.current?.click()}>
            <FileUp size={15} /> {reading ? tr('ui.labReportUpload.readingYourReport', 'Reading your report…') : tr('ui.labReportUpload.uploadAReport', 'Upload a report')}
          </button>
          <p className="lab-unit-hint">
            {tr('ui.labReportUpload.aPdfOrAPhoto', 'A PDF or a photo. It is read by our AI provider to find the values and is not stored. You check every value before anything is saved.')}
          </p>
        </>
      )}
      {error && <p className="lab-error" role="alert">{error}</p>}

      {preview && (
        <div className="lab-review" aria-labelledby="lab-review-title">
          <h3 id="lab-review-title" className="lab-review-title">{tr('ui.labReportUpload.checkWhatWeRead', 'Check what we read')}</h3>
          {rows.length === 0 ? (
            <p className="lab-sub">{tr('ui.labReportUpload.weDidNotFindAny', 'We did not find any of the tests Ayura tracks on that report. You can add results by hand.')}</p>
          ) : (
            <>
              <p className="lab-sub">{tr('ui.labReportUpload.compareEachValueWithYour', 'Compare each value with your report. Untick anything that is wrong or not yours.')}</p>
              <div className="input-group lab-review-date">
                <label htmlFor="lab-review-date">{tr('ui.labReportUpload.dateOfTheTest', 'Date of the test')}</label>
                <input id="lab-review-date" type="date" max={today()} value={date} onChange={e => setDate(e.target.value)} />
              </div>
              <ul className="lab-review-list">
                {rows.map((r, i) => (
                  <li key={r.test} className={`lab-review-row${r.include ? '' : ' is-off'}`}>
                    <label className="lab-review-check">
                      <input type="checkbox" checked={r.include} onChange={e => update(i, { include: e.target.checked })}
                        aria-label={tr('ui.labReportUpload.save', 'Save {{label}}', { label: r.label })} />
                    </label>
                    <div className="lab-review-main">
                      <div className="lab-review-name">{r.label}</div>
                      <div className="lab-review-printed"><Trans i18nKey="ui.labReportUpload.onTheReport" defaults={"On the report: {{value}} {{value2}}"} values={{ value: r.printed || '—', value2: r.converted_from && r.value != null ? ` → ${r.value} ${r.unit}` : '' }} /></div>
                      {r.issue && <div className="lab-review-issue"><Info size={12} /> {r.issue}</div>}
                    </div>
                    <div className="lab-review-value">
                      <input type="number" step="any" inputMode="decimal" value={r.input}
                        aria-label={tr('ui.labReportUpload.valueIn', '{{label}} value in {{unit}}', { label: r.label, unit: r.unit })}
                        onChange={e => update(i, { input: e.target.value, include: true })} />
                      <span>{r.unit}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
          {preview.other_tests?.length > 0 && (
            <p className="lab-unit-hint"><Trans i18nKey="ui.labReportUpload.alsoOnTheReportNot" defaults={"Also on the report, not tracked by Ayura: {{value}} {{value2}}."} values={{ value: preview.other_tests.slice(0, 12).join(', '), value2: preview.other_tests.length > 12 ? ` and ${preview.other_tests.length - 12} more` : '' }} /></p>
          )}
          <div className="lab-review-actions">
            {rows.length > 0 && (
              <button type="button" className="btn btn-primary" disabled={!chosen.length || save.isPending} onClick={submit}>
                <Check size={15} /> {save.isPending ? tr('ui.labReportUpload.saving', 'Saving…') : (chosen.length === 1 ? tr('ui.labReportUpload.saveResultOne', 'Save 1 result') : tr('ui.labReportUpload.saveResultMany', 'Save {{count}} results', { count: chosen.length }))}
              </button>
            )}
            <button type="button" className="btn btn-secondary" onClick={() => { setPreview(null); setError('') }}>
              <X size={15} />{' '}{tr('ui.labReportUpload.discard', 'Discard')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
