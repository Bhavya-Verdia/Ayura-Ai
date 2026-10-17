import { useState, useRef } from 'react'
import { CircleCheck } from 'lucide-react'
import { profileAPI } from '../../api/client'

export default function TongueUploader({ onResult }) {
  const [state, setState] = useState('idle') // idle | selected | uploading | done | error
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [errMsg, setErrMsg] = useState('')
  const inputRef = useRef(null)

  function handleFile(f) {
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setState('selected')
    setErrMsg('')
  }

  async function upload() {
    if (!file) return
    setState('uploading')
    try {
      const res = await profileAPI.tongueAssessment(file)
      onResult(res.data)
      setState('done')
    } catch (e) {
      setErrMsg(e.response?.data?.detail || 'Upload failed. Please try again.')
      setState('error')
    }
  }

  if (state === 'done') {
    return (
      <div className="da-tongue-done">
        <span style={{display:'inline-flex',verticalAlign:'-2px'}}><CircleCheck size={14} strokeWidth={2} /></span> Tongue analysis applied to your Vikriti scores.
      </div>
    )
  }

  return (
    <div className="da-tongue-uploader">
      <span className="da-tongue-label">Optional: Tongue Analysis (Jihva Pareeksha)</span>
      <span className="da-tongue-hint">Upload a clear photo of your tongue in natural light — GPT-4o will read Ayurvedic signals.</span>
      {preview && (
        <div className="da-tongue-preview-wrap">
          <img src={preview} alt="Tongue preview" className="da-tongue-preview" />
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {state === 'idle' && (
        <button type="button" className="btn btn-secondary" onClick={() => inputRef.current?.click()}>
          Choose Photo
        </button>
      )}
      {state === 'selected' && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" className="btn btn-primary" onClick={upload}>
            Analyse Tongue
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => inputRef.current?.click()}>
            Change
          </button>
        </div>
      )}
      {state === 'uploading' && <span className="da-tongue-hint">Analysing…</span>}
      {state === 'error' && (
        <>
          <span style={{ color: 'var(--color-error, #f87171)', fontSize: '0.85rem' }}>{errMsg}</span>
          <button type="button" className="btn btn-secondary" onClick={() => setState('selected')}>Retry</button>
        </>
      )}
    </div>
  )
}
