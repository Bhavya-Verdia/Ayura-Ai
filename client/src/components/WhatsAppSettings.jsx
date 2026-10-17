import { useEffect, useState } from 'react'
import { m } from 'framer-motion'
import { toast } from 'sonner'
import { MessageCircle } from 'lucide-react'
import { whatsappAPI } from '../api/client'

// Settings › WhatsApp. Hidden entirely while the server has WhatsApp switched off, so
// nobody is offered a channel that cannot deliver. A number is used only after the
// code sent to it is entered (routes/whatsapp.py).
const detail = (e, fallback) => e?.response?.data?.detail?.toString?.() || fallback

export default function WhatsAppSettings({ variants }) {
  const [st, setSt] = useState(null)
  const [phone, setPhone] = useState('')
  const [consent, setConsent] = useState(false)
  const [code, setCode] = useState('')
  const [sentTo, setSentTo] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { whatsappAPI.status().then(r => setSt(r.data)).catch(() => {}) }, [])
  if (!st?.available) return null

  const run = async (fn, ok) => {
    setBusy(true)
    try { await fn(); if (ok) toast.success(ok) } catch (e) { toast.error(detail(e, 'Something went wrong.')) }
    finally { setBusy(false) }
  }
  const sendCode = () => run(async () => {
    const r = await whatsappAPI.start({ phone, consent })
    setSentTo(r.data.phone)
  })
  const verify = () => run(async () => {
    const r = await whatsappAPI.verify(code)
    setSt(r.data); setSentTo(null); setCode('')
  }, 'WhatsApp connected')
  const save = (patch) => run(async () => setSt((await whatsappAPI.settings(patch)).data))
  const stop = () => run(async () => { setSt((await whatsappAPI.stop()).data); setPhone(''); setConsent(false) },
    'WhatsApp messages stopped')

  return (
    <m.div className="settings-card" variants={variants}>
      <h2 className="settings-section-title"><MessageCircle size={18} style={{ verticalAlign: '-3px', marginRight: 8 }} />WhatsApp</h2>

      {!st.verified && !sentTo && (
        <>
          <p className="settings-pref-help" style={{ marginBottom: 16 }}>
            Get your reminders, and if you like a short morning message with today's meals, on WhatsApp.
          </p>
          <div className="input-group">
            <label htmlFor="wa-phone">WhatsApp number</label>
            <input id="wa-phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="98765 43210"
              value={phone} onChange={e => setPhone(e.target.value)} />
          </div>
          <label className="settings-wa-consent" style={{ display: 'flex', gap: 10, alignItems: 'flex-start', margin: '12px 0 16px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
            <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
            <span>I agree to receive messages from Ayura AI on WhatsApp at this number. I can stop them here at any time.</span>
          </label>
          <button type="button" className="btn btn-primary" disabled={busy || !phone || !consent} onClick={sendCode}>
            {busy ? 'Sending…' : 'Send code on WhatsApp'}
          </button>
        </>
      )}

      {!st.verified && sentTo && (
        <>
          <p className="settings-pref-help" style={{ marginBottom: 16 }}>We sent a 6-digit code to {sentTo} on WhatsApp.</p>
          <div className="input-group">
            <label htmlFor="wa-code">Code</label>
            <input id="wa-code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="\d{6}"
              value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} />
          </div>
          <div className="settings-action-row" style={{ marginTop: 12 }}>
            <button type="button" className="btn btn-primary" disabled={busy || code.length !== 6} onClick={verify}>
              {busy ? 'Checking…' : 'Verify'}
            </button>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => { setSentTo(null); setCode('') }}>
              Change number
            </button>
          </div>
        </>
      )}

      {st.verified && (
        <>
          <p className="settings-pref-help" style={{ marginBottom: 16 }}>Connected to {st.phone}.</p>
          <div className="settings-pref-row">
            <div>
              <div className="settings-pref-label">Reminders</div>
              <div className="settings-pref-help">The reminders you set, on WhatsApp as well</div>
            </div>
            <button type="button" className={`btn btn-sm ${st.reminders ? 'btn-secondary' : 'btn-primary'}`} style={{ whiteSpace: 'nowrap' }}
              aria-pressed={st.reminders} disabled={busy} onClick={() => save({ reminders: !st.reminders })}>
              {st.reminders ? 'Turn off' : 'Turn on'}
            </button>
          </div>
          <div className="settings-pref-row">
            <div>
              <div className="settings-pref-label">Morning message</div>
              <div className="settings-pref-help">Today's meals and your streak, once a day</div>
              {st.daily && (
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 8, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  at
                  <input type="time" value={st.daily_time} disabled={busy}
                    onChange={e => e.target.value && save({ daily_time: e.target.value })} />
                </label>
              )}
            </div>
            <button type="button" className={`btn btn-sm ${st.daily ? 'btn-secondary' : 'btn-primary'}`} style={{ whiteSpace: 'nowrap' }}
              aria-pressed={st.daily} disabled={busy} onClick={() => save({ daily: !st.daily })}>
              {st.daily ? 'Turn off' : 'Turn on'}
            </button>
          </div>
          <button type="button" className="btn btn-secondary" style={{ marginTop: 16 }} disabled={busy} onClick={stop}>
            Stop WhatsApp messages
          </button>
        </>
      )}
    </m.div>
  )
}
