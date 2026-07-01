import { useState, useRef, Suspense } from 'react'
import { useAuth } from '../providers/AuthContext'
import { privacyAPI, profileAPI, exportAPI } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Helmet } from 'react-helmet-async'
import { m, AnimatePresence } from 'framer-motion'
import { useTheme } from '../providers/ThemeProvider'
import {
  Camera, Save, Brain, KeyRound, FileText, Table2,
  Package, LogOut, Trash2,
} from 'lucide-react'
import React from 'react'
import './Settings.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

const CONDITION_CATEGORIES = [
  {
    label: 'Musculoskeletal',
    items: [
      { id: 'arthritis', label: 'Arthritis' },
      { id: 'osteoarthritis', label: 'Osteoarthritis' },
      { id: 'rheumatoid_arthritis', label: 'Rheumatoid Arthritis' },
      { id: 'ankylosing_spondylitis', label: 'Ankylosing Spondylitis' },
      { id: 'gout', label: 'Gout' },
      { id: 'fibromyalgia', label: 'Fibromyalgia' },
      { id: 'osteoporosis', label: 'Osteoporosis' },
      { id: 'sciatica', label: 'Sciatica' },
      { id: 'cervical_spondylosis', label: 'Cervical Spondylosis' },
      { id: 'lumbar_spondylosis', label: 'Lumbar Spondylosis' },
    ],
  },
  {
    label: 'Neurological',
    items: [
      { id: 'migraine', label: 'Migraine' },
      { id: 'epilepsy', label: 'Epilepsy' },
      { id: 'parkinson', label: "Parkinson's" },
      { id: 'multiple_sclerosis', label: 'Multiple Sclerosis' },
      { id: 'tinnitus', label: 'Tinnitus' },
      { id: 'vertigo', label: 'Vertigo' },
      { id: 'chronic_fatigue_syndrome', label: 'Chronic Fatigue' },
      { id: 'peripheral_neuropathy', label: 'Peripheral Neuropathy' },
    ],
  },
  {
    label: 'Mental Health',
    items: [
      { id: 'anxiety', label: 'Anxiety Disorder' },
      { id: 'depression', label: 'Depression' },
      { id: 'bipolar', label: 'Bipolar Disorder' },
      { id: 'ocd', label: 'OCD' },
      { id: 'ptsd', label: 'PTSD' },
      { id: 'adhd', label: 'ADHD' },
      { id: 'insomnia', label: 'Chronic Insomnia' },
    ],
  },
  {
    label: 'Cardiovascular',
    items: [
      { id: 'hypertension', label: 'Hypertension' },
      { id: 'heart_disease', label: 'Heart Disease' },
      { id: 'atrial_fibrillation', label: 'Atrial Fibrillation' },
      { id: 'anemia', label: 'Anaemia' },
      { id: 'varicose_veins', label: 'Varicose Veins' },
      { id: 'low_blood_pressure', label: 'Low Blood Pressure' },
    ],
  },
  {
    label: 'Respiratory',
    items: [
      { id: 'asthma', label: 'Asthma' },
      { id: 'copd', label: 'COPD' },
      { id: 'allergic_rhinitis', label: 'Allergic Rhinitis' },
      { id: 'sinusitis', label: 'Chronic Sinusitis' },
      { id: 'sleep_apnea', label: 'Sleep Apnea' },
      { id: 'chronic_bronchitis', label: 'Chronic Bronchitis' },
    ],
  },
  {
    label: 'Digestive',
    items: [
      { id: 'acid_reflux', label: 'Acid Reflux / GERD' },
      { id: 'ibs', label: 'IBS' },
      { id: 'ibd_crohns', label: "Crohn's Disease" },
      { id: 'ulcerative_colitis', label: 'Ulcerative Colitis' },
      { id: 'fatty_liver', label: 'Fatty Liver' },
      { id: 'gallstones', label: 'Gallstones' },
      { id: 'constipation_chronic', label: 'Chronic Constipation' },
      { id: 'celiac', label: 'Celiac Disease' },
      { id: 'hemorrhoids', label: 'Haemorrhoids' },
    ],
  },
  {
    label: 'Endocrine & Metabolic',
    items: [
      { id: 'diabetes_type2', label: 'Type 2 Diabetes' },
      { id: 'diabetes_type1', label: 'Type 1 Diabetes' },
      { id: 'hypothyroidism', label: 'Hypothyroidism' },
      { id: 'hyperthyroidism', label: 'Hyperthyroidism' },
      { id: 'pcos', label: 'PCOS' },
      { id: 'high_cholesterol', label: 'High Cholesterol' },
      { id: 'obesity', label: 'Obesity (BMI > 30)' },
      { id: 'metabolic_syndrome', label: 'Metabolic Syndrome' },
      { id: 'hashimoto', label: "Hashimoto's" },
    ],
  },
  {
    label: 'Skin',
    items: [
      { id: 'psoriasis', label: 'Psoriasis' },
      { id: 'eczema', label: 'Eczema' },
      { id: 'acne_severe', label: 'Severe Acne' },
      { id: 'vitiligo', label: 'Vitiligo' },
      { id: 'rosacea', label: 'Rosacea' },
      { id: 'urticaria', label: 'Urticaria / Hives' },
      { id: 'alopecia', label: 'Alopecia' },
    ],
  },
  {
    label: 'Urological & Reproductive',
    items: [
      { id: 'kidney_stones', label: 'Kidney Stones' },
      { id: 'recurrent_uti', label: 'Recurrent UTIs' },
      { id: 'endometriosis', label: 'Endometriosis' },
      { id: 'uterine_fibroids', label: 'Uterine Fibroids' },
      { id: 'dysmenorrhea', label: 'Painful Periods' },
      { id: 'menorrhagia', label: 'Heavy Periods' },
    ],
  },
  {
    label: 'Autoimmune',
    items: [
      { id: 'lupus', label: 'Lupus (SLE)' },
      { id: 'scleroderma', label: 'Scleroderma' },
      { id: 'rheumatoid_arthritis', label: 'Rheumatoid Arthritis' },
    ],
  },
]

const staggerContainer = {
  animate: { transition: { staggerChildren: 0.06 } },
}

const staggerItem = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
}

export default function Settings() {
  const { profile, updateProfile, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()
  const { i18n } = useTranslation()

  const [selectedConditions, setSelectedConditions] = useState(
    (profile?.medical_history || []).filter(id =>
      CONDITION_CATEGORIES.some(cat => cat.items.some(item => item.id === id))
    )
  )
  const [conditionSearch, setConditionSearch] = useState('')
  const [otherCondition, setOtherCondition] = useState(
    (profile?.medical_history || [])
      .filter(id => !CONDITION_CATEGORIES.some(cat => cat.items.some(item => item.id === id)))
      .join(', ')
  )

  const [form, setForm] = useState({
    age: profile?.age || '',
    height_cm: profile?.height_cm || '',
    weight_kg: profile?.weight_kg || '',
    fitness_level: profile?.fitness_level || '',
    activity_level: profile?.activity_level || '',
    goal: profile?.goal || '',
    satmya: profile?.satmya || '',
    koshtha: profile?.koshtha || '',
    current_symptoms: (profile?.current_symptoms || []).join(', '),
    current_medications: (profile?.current_medications || []).join(', '),
  })

  function toggleCondition(id) {
    setSelectedConditions(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    )
  }

  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' })
  const [saving, setSaving] = useState(false)
  const [savingPw, setSavingPw] = useState(false)
  const [notice, setNotice] = useState({ type: '', message: '' })
  const [autoSaveStatus, setAutoSaveStatus] = useState('')
  const autoSaveTimer = useRef(null)
  const [avatarPreview, setAvatarPreview] = useState(null)
  const [uploadingAvatar, setUploadingAvatar] = useState(false)

  const isLocal = profile?.auth_provider === 'local'

  function handleChange(e) {
    const updated = { ...form, [e.target.name]: e.target.value }
    setForm(updated)
    // Debounced auto-save
    setAutoSaveStatus('saving')
    clearTimeout(autoSaveTimer.current)
    autoSaveTimer.current = setTimeout(() => autoSave(updated), 1400)
  }

  async function autoSave(formData) {
    try {
      const updates = {
        age:                formData.age         ? Number(formData.age)         : undefined,
        height_cm:          formData.height_cm   ? Number(formData.height_cm)   : undefined,
        weight_kg:          formData.weight_kg   ? Number(formData.weight_kg)   : undefined,
        fitness_level:      formData.fitness_level   || undefined,
        activity_level:     formData.activity_level  || undefined,
        goal:               formData.goal             || undefined,
        satmya:             formData.satmya           || undefined,
        koshtha:            formData.koshtha          || undefined,
        medical_history: [
          ...selectedConditions,
          ...otherCondition.split(',').map(s => s.trim().toLowerCase().replace(/\s+/g, '_')).filter(Boolean),
        ].filter(Boolean) || undefined,
        current_symptoms:   formData.current_symptoms   ? formData.current_symptoms.split(',').map(s => s.trim()).filter(Boolean)   : undefined,
        current_medications:formData.current_medications? formData.current_medications.split(',').map(s => s.trim()).filter(Boolean): undefined,
      }
      Object.keys(updates).forEach(k => updates[k] === undefined && delete updates[k])
      await updateProfile(updates)
      setAutoSaveStatus('saved')
      setTimeout(() => setAutoSaveStatus(''), 2200)
    } catch {
      setAutoSaveStatus('')
    }
  }

  async function saveProfile(e) {
    e.preventDefault()
    setSaving(true)
    setNotice({ type: '', message: '' })
    try {
      const updates = {
        age: form.age ? Number(form.age) : undefined,
        height_cm: form.height_cm ? Number(form.height_cm) : undefined,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : undefined,
        fitness_level: form.fitness_level || undefined,
        activity_level: form.activity_level || undefined,
        goal: form.goal || undefined,
        satmya: form.satmya || undefined,
        koshtha: form.koshtha || undefined,
        medical_history: [
          ...selectedConditions,
          ...otherCondition.split(',').map(s => s.trim().toLowerCase().replace(/\s+/g, '_')).filter(Boolean),
        ].filter(Boolean) || undefined,
        current_symptoms: form.current_symptoms ? form.current_symptoms.split(',').map(s => s.trim()).filter(Boolean) : undefined,
        current_medications: form.current_medications ? form.current_medications.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      }
      // Remove undefined keys
      Object.keys(updates).forEach(k => updates[k] === undefined && delete updates[k])
      await updateProfile(updates)
      setNotice({ type: 'success', message: 'Profile updated successfully!' })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to update profile.' })
    }
    setSaving(false)
  }

  async function changePassword(e) {
    e.preventDefault()
    if (passwords.new !== passwords.confirm) {
      setNotice({ type: 'error', message: 'New passwords do not match.' })
      return
    }
    if (passwords.new.length < 8 || !/[A-Za-z]/.test(passwords.new) || !/\d/.test(passwords.new)) {
      setNotice({ type: 'error', message: 'New password must be at least 8 characters and include a letter and a number.' })
      return
    }
    setSavingPw(true)
    setNotice({ type: '', message: '' })
    try {
      await profileAPI.changePassword(passwords.current, passwords.new)
      setPasswords({ current: '', new: '', confirm: '' })
      setNotice({ type: 'success', message: 'Password changed successfully!' })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to change password.' })
    }
    setSavingPw(false)
  }

  async function handleAvatarUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setAvatarPreview(URL.createObjectURL(file))
    setUploadingAvatar(true)
    try {
      await profileAPI.uploadAvatar(file)
      setNotice({ type: 'success', message: 'Avatar uploaded!' })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to upload avatar.' })
      setAvatarPreview(null)
    }
    setUploadingAvatar(false)
  }

  async function exportAccountData() {
    setNotice({ type: '', message: '' })
    try {
      const { data } = await privacyAPI.exportData()
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a')
      link.href = url
      link.download = 'ayura-account-data.json'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setNotice({ type: 'success', message: 'Account data export started.' })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to export account data.' })
    }
  }

  const [exportingPdf, setExportingPdf] = useState(false)
  const [exportingCsv, setExportingCsv] = useState(false)

  async function downloadPdf() {
    setExportingPdf(true)
    try {
      const { data } = await exportAPI.pdf()
      const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.download = 'ayura-wellness-report.pdf'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setNotice({ type: 'success', message: 'Wellness report downloaded.' })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to export PDF. Generate a plan first.' })
    } finally {
      setExportingPdf(false)
    }
  }

  async function downloadCsv() {
    setExportingCsv(true)
    try {
      const { data } = await exportAPI.csv()
      const url = URL.createObjectURL(new Blob([data], { type: 'text/csv' }))
      const link = document.createElement('a')
      link.href = url
      link.download = 'ayura-progress.csv'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setNotice({ type: 'success', message: 'Progress CSV downloaded.' })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to export CSV.' })
    } finally {
      setExportingCsv(false)
    }
  }

  async function deleteAccount() {
    if (!window.confirm('This permanently deletes your Ayura AI account and health data. Continue?')) return
    try {
      await privacyAPI.deleteAccount()
      await logout()
      navigate('/')
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to delete account.' })
    }
  }

  const avatarUrl = avatarPreview || (profile?.avatar_url ? profile.avatar_url : null)

  return (
    <>
      <Helmet><title>Settings | Ayura AI</title></Helmet>
    <div className="settings-root">
      <Suspense fallback={null}>
        <LazyParticleField count={200} spread={25} style={{ opacity: 0.4 }} />
      </Suspense>

      <div className="settings-bg-orb settings-bg-orb-a" />
      <div className="settings-bg-orb settings-bg-orb-b" />

      <m.div
        className="settings-container"
        variants={staggerContainer}
        initial="initial"
        animate="animate"
      >
        <m.div variants={staggerItem} className="settings-header">
          <div>
            <h1 className="settings-page-title">Settings</h1>
            <p className="settings-page-sub">Manage your profile, health data, and account</p>
          </div>
          <m.button className="btn btn-secondary" onClick={() => navigate('/dashboard')} whileTap={{ scale: 0.97 }}>
            ← Back to Dashboard
          </m.button>
        </m.div>

        <AnimatePresence>
          {notice.message && (
            <m.div
              className={`settings-notice ${notice.type}`}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {notice.message}
            </m.div>
          )}
        </AnimatePresence>

        {/* Account Info */}
        <m.div className="settings-card" variants={staggerItem}>
          <h2 className="settings-section-title">Account</h2>
          <div className="settings-account-row">
            <div className="settings-avatar-wrap">
              {avatarUrl ? (
                <img src={avatarUrl} alt="Avatar" className="settings-avatar-img" loading="lazy" decoding="async" />
              ) : (
                <div className="settings-avatar-placeholder">
                  {profile?.name?.charAt(0)?.toUpperCase() || '?'}
                </div>
              )}
              <label className="settings-avatar-btn" title="Upload avatar">
                <Camera size={15} strokeWidth={2} />
                <input type="file" accept="image/*" onChange={handleAvatarUpload} hidden />
              </label>
              {uploadingAvatar && <div className="spinner" style={{ width: '16px', height: '16px', position: 'absolute', bottom: 0, right: 0 }} />}
            </div>
            <div>
              <div className="settings-account-name">{profile?.name}</div>
              <div className="settings-account-email">{profile?.email}</div>
              <div className="settings-account-meta">
                Auth: {profile?.auth_provider || 'local'} · Dosha: {profile?.dominant_dosha || 'Not set'}
              </div>
            </div>
          </div>
        </m.div>

        {/* Theme Settings */}
        <m.div className="settings-card" variants={staggerItem}>
          <h2 className="settings-section-title">Preferences</h2>
          <div className="settings-pref-row">
            <div>
              <div className="settings-pref-label">App Theme</div>
              <div className="settings-pref-help">Choose between light and dark mode</div>
              <div style={{ display: 'flex', gap: '16px', marginTop: '16px' }}>
                {/* Dark Theme Preview */}
                <div 
                  className="settings-theme-preview" 
                  style={{ 
                    cursor: 'pointer',
                    borderColor: theme === 'dark' ? 'var(--ayura-teal)' : 'var(--border-light)',
                    boxShadow: theme === 'dark' ? '0 0 0 2px rgba(45,212,191,0.2)' : 'none',
                    background: '#0B1121' 
                  }}
                  onClick={() => setTheme('dark')}
                >
                  <div className="settings-theme-preview-bar" style={{ background: '#1E293B' }}>
                    <span style={{ background: '#334155' }} />
                    <span style={{ background: '#0F172A', flex: 2 }} />
                  </div>
                  <div className="settings-theme-preview-body">
                    <div className="settings-theme-preview-line" style={{ background: '#334155', width: '80%' }} />
                    <div className="settings-theme-preview-line" style={{ background: '#1E293B', width: '60%' }} />
                    <div className="settings-theme-preview-line" style={{ background: 'linear-gradient(135deg, #2DD4BF, #818CF8)', width: '40%', marginTop: '8px' }} />
                  </div>
                  <div style={{ padding: '8px', textAlign: 'center', fontSize: '0.8rem', color: '#94A3B8', fontWeight: 600 }}>Dark</div>
                </div>

                {/* Light Theme Preview */}
                <div 
                  className="settings-theme-preview" 
                  style={{ 
                    cursor: 'pointer',
                    borderColor: theme === 'light' ? 'var(--ayura-teal)' : 'var(--border-light)',
                    boxShadow: theme === 'light' ? '0 0 0 2px rgba(45,212,191,0.2)' : 'none',
                    background: '#F8FAFC' 
                  }}
                  onClick={() => setTheme('light')}
                >
                  <div className="settings-theme-preview-bar" style={{ background: '#E2E8F0' }}>
                    <span style={{ background: '#CBD5E1' }} />
                    <span style={{ background: '#F1F5F9', flex: 2 }} />
                  </div>
                  <div className="settings-theme-preview-body">
                    <div className="settings-theme-preview-line" style={{ background: '#CBD5E1', width: '80%' }} />
                    <div className="settings-theme-preview-line" style={{ background: '#E2E8F0', width: '60%' }} />
                    <div className="settings-theme-preview-line" style={{ background: 'linear-gradient(135deg, #2DD4BF, #818CF8)', width: '40%', marginTop: '8px' }} />
                  </div>
                  <div style={{ padding: '8px', textAlign: 'center', fontSize: '0.8rem', color: '#475569', fontWeight: 600 }}>Light</div>
                </div>
              </div>
            </div>
          </div>

          <div className="settings-pref-row" style={{ marginTop: '16px' }}>
            <div>
              <div className="settings-pref-label">Language</div>
              <div className="settings-pref-help">Choose your preferred language</div>
            </div>
            <select
              value={i18n.language}
              onChange={(e) => {
                i18n.changeLanguage(e.target.value);
                localStorage.setItem('ayura_lang', e.target.value);
              }}
              style={{ width: '120px' }}
            >
              <option value="en">English</option>
              <option value="hi">हिंदी (Hindi)</option>
            </select>
          </div>
        </m.div>

        {/* Profile form */}
        <m.form className="settings-card" onSubmit={saveProfile} variants={staggerItem}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <h2 className="settings-section-title" style={{ margin: 0 }}>Health Profile</h2>
            {autoSaveStatus === 'saving' && (
              <span className="settings-autosave saving">Saving…</span>
            )}
            {autoSaveStatus === 'saved' && (
              <span className="settings-autosave saved">✓ Saved</span>
            )}
          </div>
          <div className="settings-grid">
            <div className="input-group">
              <label>Age</label>
              <input type="number" name="age" value={form.age} onChange={handleChange} min={10} max={120} />
            </div>
            <div className="input-group">
              <label>Height (cm)</label>
              <input type="number" name="height_cm" value={form.height_cm} onChange={handleChange} step="0.1" />
            </div>
            <div className="input-group">
              <label>Weight (kg)</label>
              <input type="number" name="weight_kg" value={form.weight_kg} onChange={handleChange} step="0.1" />
            </div>
            <div className="input-group">
              <label>Fitness Level</label>
              <select name="fitness_level" value={form.fitness_level} onChange={handleChange}>
                <option value="">Select</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
            <div className="input-group">
              <label>Activity Level</label>
              <select name="activity_level" value={form.activity_level} onChange={handleChange}>
                <option value="">Select</option>
                <option value="sedentary">Sedentary</option>
                <option value="light">Light</option>
                <option value="moderate">Moderate</option>
                <option value="active">Active</option>
                <option value="very_active">Very Active</option>
              </select>
            </div>
            <div className="input-group">
              <label>Goal</label>
              <select name="goal" value={form.goal} onChange={handleChange}>
                <option value="">Select</option>
                <option value="weight_loss">Weight Loss</option>
                <option value="muscle_gain">Muscle Gain</option>
                <option value="flexibility">Flexibility</option>
                <option value="balance">Balance</option>
                <option value="detox">Detox</option>
                <option value="general_wellness">General Wellness</option>
              </select>
            </div>
          </div>

          <div style={{ marginTop: '16px' }}>
            <label style={{ display: 'block', marginBottom: '10px', fontWeight: 600, fontSize: '0.9rem' }}>Medical Conditions</label>
            <input
              className="onb-condition-search"
              type="text"
              placeholder="Search conditions…"
              value={conditionSearch}
              onChange={e => setConditionSearch(e.target.value)}
            />
            {CONDITION_CATEGORIES.map(cat => {
              const q = conditionSearch.trim().toLowerCase()
              const visible = q
                ? cat.items.filter(({ label }) => label.toLowerCase().includes(q))
                : cat.items
              if (visible.length === 0) return null
              return (
                <div key={cat.label} className="onb-condition-category">
                  <span className="onb-condition-cat-label">{cat.label}</span>
                  <div className="onb-chip-wrap">
                    {visible.map(({ id, label }) => (
                      <button
                        key={id} type="button"
                        onClick={() => toggleCondition(id)}
                        className={`onb-chip ${selectedConditions.includes(id) ? 'selected' : ''}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
            <div className="onb-other-condition">
              <span className="onb-condition-cat-label" style={{ display: 'block', marginTop: 10 }}>
                Not listed? Add here (comma-separated)
              </span>
              <input
                className="onb-condition-search"
                type="text"
                placeholder="e.g. sarcoidosis, hemophilia"
                value={otherCondition}
                onChange={e => setOtherCondition(e.target.value)}
              />
            </div>
          </div>
          <div className="input-group">
            <label>How long have you followed your current diet &amp; lifestyle? (Satmya)</label>
            <select name="satmya" value={form.satmya} onChange={handleChange}>
              <option value="">Select…</option>
              <option value="less_than_1y">Less than 1 year</option>
              <option value="1_to_5y">1–5 years</option>
              <option value="over_5y">More than 5 years</option>
            </select>
          </div>

          <div className="input-group">
            <label>Bowel Tendency (Koshtha) — used for Panchakarma personalisation</label>
            <select name="koshtha" value={form.koshtha} onChange={handleChange}>
              <option value="">Select…</option>
              <option value="sama">Sama — Regular once daily</option>
              <option value="krura">Krura — Hard / infrequent (tends toward constipation)</option>
              <option value="mridu">Mridu — Loose / frequent (tends toward loose stools)</option>
            </select>
          </div>

          <div className="input-group">
            <label>Current Symptoms (comma-separated)</label>
            <input name="current_symptoms" value={form.current_symptoms} onChange={handleChange} placeholder="e.g. fatigue, bloating, insomnia" />
          </div>
          <div className="input-group">
            <label>Current Medications (comma-separated)</label>
            <input name="current_medications" value={form.current_medications} onChange={handleChange} placeholder="e.g. metformin, atenolol" />
          </div>

          <div className="settings-action-row">
            <m.button className="btn btn-primary" type="submit" disabled={saving} whileTap={{ scale: 0.97 }}>
              {saving ? 'Saving…' : <><Save size={16} strokeWidth={2} /> Save Profile</>}
            </m.button>
            <m.button className="btn btn-secondary" type="button" onClick={() => navigate('/onboarding?retake=true')} whileTap={{ scale: 0.97 }}>
              <Brain size={16} strokeWidth={2} /> Retake Dosha Quiz
            </m.button>
          </div>
        </m.form>

        {/* Password Change (local auth only) */}
        {isLocal && (
          <m.form className="settings-card" onSubmit={changePassword} variants={staggerItem}>
            <h2 className="settings-section-title">Change Password</h2>
            <div className="settings-grid">
              <div className="input-group">
                <label>Current Password</label>
                <input type="password" value={passwords.current} onChange={e => setPasswords(p => ({ ...p, current: e.target.value }))} required />
              </div>
              <div className="input-group">
                <label>New Password</label>
                <input type="password" value={passwords.new} onChange={e => setPasswords(p => ({ ...p, new: e.target.value }))} minLength={8} required />
              </div>
              <div className="input-group">
                <label>Confirm New Password</label>
                <input type="password" value={passwords.confirm} onChange={e => setPasswords(p => ({ ...p, confirm: e.target.value }))} required />
              </div>
            </div>
            <m.button className="btn btn-primary" type="submit" disabled={savingPw} style={{ marginTop: '16px' }} whileTap={{ scale: 0.97 }}>
              {savingPw ? 'Changing…' : <><KeyRound size={16} strokeWidth={2} /> Change Password</>}
            </m.button>
          </m.form>
        )}

        {/* Export wellness data */}
        <m.div className="settings-card" variants={staggerItem}>
          <h2 className="settings-section-title">Export Wellness Data</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 20 }}>
            Download a Vaidya-handoff PDF — your Prakriti &amp; Vikriti assessment, Agni, Ama, Ojas, conditions, and plans in one summary to share with your Ayurvedic physician — or export your progress logs as a CSV spreadsheet.
          </p>
          <div className="settings-action-row">
            <m.button className="btn btn-primary" onClick={downloadPdf} disabled={exportingPdf} whileTap={{ scale: 0.97 }}>
              {exportingPdf ? 'Generating…' : <><FileText size={16} strokeWidth={2} /> Download Vaidya Report (PDF)</>}
            </m.button>
            <m.button className="btn btn-secondary" onClick={downloadCsv} disabled={exportingCsv} whileTap={{ scale: 0.97 }}>
              {exportingCsv ? 'Exporting…' : <><Table2 size={16} strokeWidth={2} /> Download Progress CSV</>}
            </m.button>
          </div>
        </m.div>

        {/* Danger zone */}
        <m.div className="settings-card settings-danger" variants={staggerItem}>
          <h2 className="settings-section-title settings-danger-title">Account Actions</h2>
          <div className="settings-action-row">
            <m.button className="btn btn-secondary" onClick={exportAccountData} whileTap={{ scale: 0.97 }}>
              <Package size={16} strokeWidth={2} /> Export Data
            </m.button>
            <m.button className="btn btn-secondary" onClick={() => { logout(); navigate('/login') }} whileTap={{ scale: 0.97 }}>
              <LogOut size={16} strokeWidth={2} /> Log Out
            </m.button>
            <m.button className="btn btn-secondary settings-btn-danger" onClick={deleteAccount} whileTap={{ scale: 0.97 }}>
              <Trash2 size={16} strokeWidth={2} /> Delete Account
            </m.button>
          </div>
        </m.div>
      </m.div>
    </div>
    </>
  )
}
