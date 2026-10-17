import { useState } from 'react'
import { toast } from 'sonner'
import { Download, Printer } from 'lucide-react'
import { exportAPI } from '../api/client'

// The Daily Routine as a printable PDF (server/services/routine_pdf.py): the week, one
// day per page, or just today's page. Print opens the PDF so the browser's own print
// dialog prints the sheet as designed, not the screen.
async function blobError(err, fallback) {
  try {
    const t = await err?.response?.data?.text?.()
    return JSON.parse(t).detail || fallback
  } catch {
    return fallback
  }
}

export default function RoutinePdfButtons() {
  const [busy, setBusy] = useState(null)

  async function fetchPdf(day) {
    const { data } = await exportAPI.routinePdf(day)
    return URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
  }

  async function download(day) {
    setBusy(day)
    try {
      const url = await fetchPdf(day)
      const a = document.createElement('a')
      a.href = url
      a.download = day === 'today' ? 'ayura-daily-routine-today.pdf' : 'ayura-daily-routine-week.pdf'
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (err) {
      toast.error(await blobError(err, 'Could not make the PDF. Try again.'))
    } finally {
      setBusy(null)
    }
  }

  async function print() {
    // Opened before the request, inside the click, or a popup blocker stops it.
    const win = window.open('', '_blank')
    setBusy('print')
    try {
      const url = await fetchPdf('today')
      if (win) win.location.href = url
      else window.location.href = url
    } catch (err) {
      win?.close()
      toast.error(await blobError(err, 'Could not make the PDF. Try again.'))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="din-pdf-bar" role="group" aria-label="Download or print your routine">
      <button type="button" className="btn btn-secondary btn-sm" disabled={!!busy} onClick={() => download('all')}>
        <Download size={14} /> {busy === 'all' ? 'Preparing…' : 'Week as PDF'}
      </button>
      <button type="button" className="btn btn-secondary btn-sm" disabled={!!busy} onClick={() => download('today')}>
        <Download size={14} /> {busy === 'today' ? 'Preparing…' : "Today's page"}
      </button>
      <button type="button" className="btn btn-secondary btn-sm" disabled={!!busy} onClick={print}>
        <Printer size={14} /> {busy === 'print' ? 'Preparing…' : 'Print today'}
      </button>
    </div>
  )
}
