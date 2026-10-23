import { useState, useRef, useEffect, Suspense } from 'react'
import { toast } from 'sonner'
import { useAuth } from '../providers/AuthContext'
import { pushStatus, enablePush, disablePush } from '../lib/push'
import { privacyAPI, profileAPI, exportAPI } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { useTranslation, Trans } from 'react-i18next'
import { setLanguage, SUPPORTED_LANGUAGES } from '../i18n'
import { Helmet } from 'react-helmet-async'
import { m, AnimatePresence } from 'framer-motion'
import { useTheme } from '../providers/ThemeProvider'
import {
  Camera, Save, Brain, KeyRound, FileText, Table2,
  Package, LogOut, Trash2, MessageSquare,
} from 'lucide-react'
import React from 'react'
import './Settings.css'
import WhatsAppSettings from '../components/WhatsAppSettings'

import { tr } from '../lib/tr'
const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

const CONDITION_CATEGORIES = [
  {
    get label() { return tr('ui.settings.musculoskeletal', 'Musculoskeletal') },
    items: [
      { id: 'arthritis', get label() { return tr('ui.settings.arthritis', 'Arthritis') } },
      { id: 'osteoarthritis', get label() { return tr('ui.settings.osteoarthritis', 'Osteoarthritis') } },
      { id: 'rheumatoid_arthritis', get label() { return tr('ui.settings.rheumatoidArthritis', 'Rheumatoid Arthritis') } },
      { id: 'ankylosing_spondylitis', get label() { return tr('ui.settings.ankylosingSpondylitis', 'Ankylosing Spondylitis') } },
      { id: 'gout', get label() { return tr('ui.settings.gout', 'Gout') } },
      { id: 'fibromyalgia', get label() { return tr('ui.settings.fibromyalgia', 'Fibromyalgia') } },
      { id: 'osteoporosis', get label() { return tr('ui.settings.osteoporosis', 'Osteoporosis') } },
      { id: 'sciatica', get label() { return tr('ui.settings.sciatica', 'Sciatica') } },
      { id: 'cervical_spondylosis', get label() { return tr('ui.settings.cervicalSpondylosis', 'Cervical Spondylosis') } },
      { id: 'lumbar_spondylosis', get label() { return tr('ui.settings.lumbarSpondylosis', 'Lumbar Spondylosis') } },
    ],
  },
  {
    get label() { return tr('ui.settings.neurological', 'Neurological') },
    items: [
      { id: 'migraine', get label() { return tr('ui.settings.migraine', 'Migraine') } },
      { id: 'epilepsy', get label() { return tr('ui.settings.epilepsy', 'Epilepsy') } },
      { id: 'parkinson', get label() { return tr('ui.settings.parkinsonS', 'Parkinson\'s') } },
      { id: 'multiple_sclerosis', get label() { return tr('ui.settings.multipleSclerosis', 'Multiple Sclerosis') } },
      { id: 'tinnitus', get label() { return tr('ui.settings.tinnitus', 'Tinnitus') } },
      { id: 'vertigo', get label() { return tr('ui.settings.vertigo', 'Vertigo') } },
      { id: 'chronic_fatigue_syndrome', get label() { return tr('ui.settings.chronicFatigue', 'Chronic Fatigue') } },
      { id: 'peripheral_neuropathy', get label() { return tr('ui.settings.peripheralNeuropathy', 'Peripheral Neuropathy') } },
    ],
  },
  {
    get label() { return tr('ui.settings.mentalHealth', 'Mental Health') },
    items: [
      { id: 'anxiety', get label() { return tr('ui.settings.anxietyDisorder', 'Anxiety Disorder') } },
      { id: 'depression', get label() { return tr('ui.settings.depression', 'Depression') } },
      { id: 'bipolar', get label() { return tr('ui.settings.bipolarDisorder', 'Bipolar Disorder') } },
      { id: 'ocd', label: 'OCD' },
      { id: 'ptsd', label: 'PTSD' },
      { id: 'adhd', label: 'ADHD' },
      { id: 'insomnia', get label() { return tr('ui.settings.chronicInsomnia', 'Chronic Insomnia') } },
    ],
  },
  {
    get label() { return tr('ui.settings.cardiovascular', 'Cardiovascular') },
    items: [
      { id: 'hypertension', get label() { return tr('ui.settings.hypertension', 'Hypertension') } },
      { id: 'heart_disease', get label() { return tr('ui.settings.heartDisease', 'Heart Disease') } },
      { id: 'atrial_fibrillation', get label() { return tr('ui.settings.atrialFibrillation', 'Atrial Fibrillation') } },
      { id: 'anemia', get label() { return tr('ui.settings.anaemia', 'Anaemia') } },
      { id: 'varicose_veins', get label() { return tr('ui.settings.varicoseVeins', 'Varicose Veins') } },
      { id: 'low_blood_pressure', get label() { return tr('ui.settings.lowBloodPressure', 'Low Blood Pressure') } },
    ],
  },
  {
    get label() { return tr('ui.settings.respiratory', 'Respiratory') },
    items: [
      { id: 'asthma', get label() { return tr('ui.settings.asthma', 'Asthma') } },
      { id: 'copd', label: 'COPD' },
      { id: 'allergic_rhinitis', get label() { return tr('ui.settings.allergicRhinitis', 'Allergic Rhinitis') } },
      { id: 'sinusitis', get label() { return tr('ui.settings.chronicSinusitis', 'Chronic Sinusitis') } },
      { id: 'sleep_apnea', get label() { return tr('ui.settings.sleepApnea', 'Sleep Apnea') } },
      { id: 'chronic_bronchitis', get label() { return tr('ui.settings.chronicBronchitis', 'Chronic Bronchitis') } },
    ],
  },
  {
    get label() { return tr('ui.settings.digestive', 'Digestive') },
    items: [
      { id: 'acid_reflux', get label() { return tr('ui.settings.acidRefluxGerd', 'Acid Reflux / GERD') } },
      { id: 'ibs', label: 'IBS' },
      { id: 'ibd_crohns', get label() { return tr('ui.settings.crohnSDisease', 'Crohn\'s Disease') } },
      { id: 'ulcerative_colitis', get label() { return tr('ui.settings.ulcerativeColitis', 'Ulcerative Colitis') } },
      { id: 'fatty_liver', get label() { return tr('ui.settings.fattyLiver', 'Fatty Liver') } },
      { id: 'gallstones', get label() { return tr('ui.settings.gallstones', 'Gallstones') } },
      { id: 'constipation_chronic', get label() { return tr('ui.settings.chronicConstipation', 'Chronic Constipation') } },
      { id: 'celiac', get label() { return tr('ui.settings.celiacDisease', 'Celiac Disease') } },
      { id: 'hemorrhoids', get label() { return tr('ui.settings.haemorrhoids', 'Haemorrhoids') } },
    ],
  },
  {
    get label() { return tr('ui.settings.endocrineMetabolic', 'Endocrine & Metabolic') },
    items: [
      { id: 'diabetes_type2', get label() { return tr('ui.settings.type2Diabetes', 'Type 2 Diabetes') } },
      { id: 'diabetes_type1', get label() { return tr('ui.settings.type1Diabetes', 'Type 1 Diabetes') } },
      { id: 'hypothyroidism', get label() { return tr('ui.settings.hypothyroidism', 'Hypothyroidism') } },
      { id: 'hyperthyroidism', get label() { return tr('ui.settings.hyperthyroidism', 'Hyperthyroidism') } },
      { id: 'pcos', label: 'PCOS' },
      { id: 'high_cholesterol', get label() { return tr('ui.settings.highCholesterol', 'High Cholesterol') } },
      { id: 'obesity', get label() { return tr('ui.settings.obesityBmi30', 'Obesity (BMI > 30)') } },
      { id: 'metabolic_syndrome', get label() { return tr('ui.settings.metabolicSyndrome', 'Metabolic Syndrome') } },
      { id: 'hashimoto', get label() { return tr('ui.settings.hashimotoS', 'Hashimoto\'s') } },
    ],
  },
  {
    get label() { return tr('ui.settings.skin', 'Skin') },
    items: [
      { id: 'psoriasis', get label() { return tr('ui.settings.psoriasis', 'Psoriasis') } },
      { id: 'eczema', get label() { return tr('ui.settings.eczema', 'Eczema') } },
      { id: 'acne_severe', get label() { return tr('ui.settings.severeAcne', 'Severe Acne') } },
      { id: 'vitiligo', get label() { return tr('ui.settings.vitiligo', 'Vitiligo') } },
      { id: 'rosacea', get label() { return tr('ui.settings.rosacea', 'Rosacea') } },
      { id: 'urticaria', get label() { return tr('ui.settings.urticariaHives', 'Urticaria / Hives') } },
      { id: 'alopecia', get label() { return tr('ui.settings.alopecia', 'Alopecia') } },
    ],
  },
  {
    get label() { return tr('ui.settings.urologicalReproductive', 'Urological & Reproductive') },
    items: [
      { id: 'kidney_stones', get label() { return tr('ui.settings.kidneyStones', 'Kidney Stones') } },
      { id: 'recurrent_uti', get label() { return tr('ui.settings.recurrentUtis', 'Recurrent UTIs') } },
      { id: 'endometriosis', get label() { return tr('ui.settings.endometriosis', 'Endometriosis') } },
      { id: 'uterine_fibroids', get label() { return tr('ui.settings.uterineFibroids', 'Uterine Fibroids') } },
      { id: 'dysmenorrhea', get label() { return tr('ui.settings.painfulPeriods', 'Painful Periods') } },
      { id: 'menorrhagia', get label() { return tr('ui.settings.heavyPeriods', 'Heavy Periods') } },
    ],
  },
  {
    get label() { return tr('ui.settings.autoimmune', 'Autoimmune') },
    items: [
      { id: 'lupus', get label() { return tr('ui.settings.lupusSle', 'Lupus (SLE)') } },
      { id: 'scleroderma', get label() { return tr('ui.settings.scleroderma', 'Scleroderma') } },
      { id: 'rheumatoid_arthritis', get label() { return tr('ui.settings.rheumatoidArthritis', 'Rheumatoid Arthritis') } },
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
  const { theme, setThemeAnimated } = useTheme()
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
  // 'unsupported' | 'denied' | 'subscribed' | 'off' | 'unavailable' | 'busy'
  const [pushState, setPushState] = useState('off')
  useEffect(() => { pushStatus().then(setPushState).catch(() => {}) }, [])

  const togglePush = async () => {
    const prev = pushState
    setPushState('busy')
    try {
      if (prev === 'subscribed') {
        await disablePush()
        setPushState('off')
        toast.success(tr('ui.settings.pushNotificationsTurnedOffOn', 'Push notifications turned off on this device.'))
      } else {
        const result = await enablePush()
        setPushState(result === 'subscribed' ? 'subscribed' : result)
        if (result === 'subscribed') toast.success(tr('ui.settings.pushNotificationsEnabledRemindersNow', 'Push notifications enabled — reminders now reach this device.'))
        else if (result === 'denied') toast.error(tr('ui.settings.notificationsAreBlockedForThis', 'Notifications are blocked for this site in your browser settings.'))
        else if (result === 'unavailable') toast.error(tr('ui.settings.pushIsNotConfiguredOn', 'Push is not configured on the server yet.'))
      }
    } catch {
      setPushState(prev)
      toast.error(tr('ui.settings.couldNotUpdatePushNotifications', 'Could not update push notifications. Please try again.'))
    }
  }
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
      setNotice({ type: 'success', message: tr('ui.settings.profileUpdatedSuccessfully', 'Profile updated successfully!') })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to update profile.' })
    }
    setSaving(false)
  }

  async function changePassword(e) {
    e.preventDefault()
    if (passwords.new !== passwords.confirm) {
      setNotice({ type: 'error', message: tr('ui.settings.newPasswordsDoNotMatch', 'New passwords do not match.') })
      return
    }
    if (passwords.new.length < 8 || !/[A-Za-z]/.test(passwords.new) || !/\d/.test(passwords.new)) {
      setNotice({ type: 'error', message: tr('ui.settings.newPasswordMustBeAt', 'New password must be at least 8 characters and include a letter and a number.') })
      return
    }
    setSavingPw(true)
    setNotice({ type: '', message: '' })
    try {
      await profileAPI.changePassword(passwords.current, passwords.new)
      setPasswords({ current: '', new: '', confirm: '' })
      // The change signs out every other device, which they would otherwise
      // only find out about the next time they open the app there.
      setNotice({ type: 'success', message: tr('ui.settings.passwordChangedAnyOtherDevices', 'Password changed. Any other devices signed in to your account have been signed out.') })
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
      setNotice({ type: 'success', message: tr('ui.settings.avatarUploaded', 'Avatar uploaded!') })
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
      setNotice({ type: 'success', message: tr('ui.settings.accountDataExportStarted', 'Account data export started.') })
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
      setNotice({ type: 'success', message: tr('ui.settings.wellnessReportDownloaded', 'Wellness report downloaded.') })
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
      setNotice({ type: 'success', message: tr('ui.settings.progressCsvDownloaded', 'Progress CSV downloaded.') })
    } catch (err) {
      setNotice({ type: 'error', message: err.response?.data?.detail || 'Failed to export CSV.' })
    } finally {
      setExportingCsv(false)
    }
  }

  async function deleteAccount() {
    if (!window.confirm(tr('ui.settings.thisPermanentlyDeletesYourAyura', 'This permanently deletes your Ayura AI account and health data. Continue?'))) return
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
      <Helmet><title>{tr('ui.settings.settingsAyuraAi', 'Settings | Ayura AI')}</title></Helmet>
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
            <h1 className="settings-page-title">{tr('ui.settings.settings', 'Settings')}</h1>
            <p className="settings-page-sub">{tr('ui.settings.manageYourProfileHealthData', 'Manage your profile, health data, and account')}</p>
          </div>
          <m.button className="btn btn-secondary" onClick={() => navigate('/dashboard')} whileTap={{ scale: 0.97 }}>
            {tr('ui.settings.backToDashboard', '← Back to Dashboard')}
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
          <h2 className="settings-section-title">{tr('ui.settings.account', 'Account')}</h2>
          <div className="settings-account-row">
            <div className="settings-avatar-wrap">
              {avatarUrl ? (
                <img src={avatarUrl} alt={tr('ui.settings.avatar', 'Avatar')} className="settings-avatar-img" loading="lazy" decoding="async" />
              ) : (
                <div className="settings-avatar-placeholder">
                  {profile?.name ? profile.name.split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase() : '?'}
                </div>
              )}
              <label className="settings-avatar-btn" title={tr('ui.settings.uploadAvatar', 'Upload avatar')}>
                <Camera size={15} strokeWidth={2} />
                <input type="file" accept="image/*" onChange={handleAvatarUpload} hidden />
              </label>
              {uploadingAvatar && <div className="spinner" style={{ width: '16px', height: '16px', position: 'absolute', bottom: 0, right: 0 }} />}
            </div>
            <div>
              <div className="settings-account-name">{profile?.name}</div>
              <div className="settings-account-email">{profile?.email}</div>
              <div className="settings-account-meta"><Trans i18nKey="ui.settings.authDosha" defaults={"Auth: {{value}} · Dosha: {{value2}}"} values={{ value: profile?.auth_provider || 'local', value2: profile?.dominant_dosha || 'Not set' }} /></div>
            </div>
          </div>
        </m.div>

        {/* Theme Settings */}
        <m.div className="settings-card" variants={staggerItem}>
          <h2 className="settings-section-title">{tr('ui.settings.preferences', 'Preferences')}</h2>
          <div className="settings-pref-row">
            <div>
              <div className="settings-pref-label">{tr('ui.settings.appTheme', 'App Theme')}</div>
              <div className="settings-pref-help">{tr('ui.settings.chooseBetweenLightAndDark', 'Choose between light and dark mode')}</div>
              <div style={{ display: 'flex', gap: '16px', marginTop: '16px' }}>
                {/* Dark Theme Preview */}
                <button
                  type="button"
                  aria-pressed={theme === 'dark'}
                  className="settings-theme-preview" 
                  style={{ 
                    cursor: 'pointer',
                    borderColor: theme === 'dark' ? 'var(--ayura-teal)' : 'var(--border-light)',
                    boxShadow: theme === 'dark' ? '0 0 0 2px rgba(92,171,116,0.2)' : 'none',
                    background: '#0B1121' 
                  }}
                  onClick={(e) => setThemeAnimated('dark', e)}
                >
                  <div className="settings-theme-preview-bar" style={{ background: '#1E293B' }}>
                    <span style={{ background: '#334155' }} />
                    <span style={{ background: '#0F172A', flex: 2 }} />
                  </div>
                  <div className="settings-theme-preview-body">
                    <div className="settings-theme-preview-line" style={{ background: '#334155', width: '80%' }} />
                    <div className="settings-theme-preview-line" style={{ background: '#1E293B', width: '60%' }} />
                    <div className="settings-theme-preview-line" style={{ background: 'linear-gradient(135deg, #5cab74, #e6a23c)', width: '40%', marginTop: '8px' }} />
                  </div>
                  <div style={{ padding: '8px', textAlign: 'center', fontSize: '0.8rem', color: '#94A3B8', fontWeight: 600 }}>{tr('ui.settings.dark', 'Dark')}</div>
                </button>

                {/* Light Theme Preview */}
                <button
                  type="button"
                  aria-pressed={theme === 'light'}
                  className="settings-theme-preview" 
                  style={{ 
                    cursor: 'pointer',
                    borderColor: theme === 'light' ? 'var(--ayura-teal)' : 'var(--border-light)',
                    boxShadow: theme === 'light' ? '0 0 0 2px rgba(92,171,116,0.2)' : 'none',
                    background: '#F8FAFC' 
                  }}
                  onClick={(e) => setThemeAnimated('light', e)}
                >
                  <div className="settings-theme-preview-bar" style={{ background: '#E2E8F0' }}>
                    <span style={{ background: '#CBD5E1' }} />
                    <span style={{ background: '#F1F5F9', flex: 2 }} />
                  </div>
                  <div className="settings-theme-preview-body">
                    <div className="settings-theme-preview-line" style={{ background: '#CBD5E1', width: '80%' }} />
                    <div className="settings-theme-preview-line" style={{ background: '#E2E8F0', width: '60%' }} />
                    <div className="settings-theme-preview-line" style={{ background: 'linear-gradient(135deg, #5cab74, #e6a23c)', width: '40%', marginTop: '8px' }} />
                  </div>
                  <div style={{ padding: '8px', textAlign: 'center', fontSize: '0.8rem', color: '#475569', fontWeight: 600 }}>{tr('ui.settings.light', 'Light')}</div>
                </button>
              </div>
            </div>
          </div>

          <div className="settings-pref-row" style={{ marginTop: '16px' }}>
            <div>
              <div className="settings-pref-label" id="settings-language-label">{tr('ui.settings.language', 'Language')}</div>
              <div className="settings-pref-help">{tr('ui.settings.chooseYourPreferredLanguage', 'Choose your preferred language')}</div>
            </div>
            <select
              aria-labelledby="settings-language-label"
              value={i18n.language}
              onChange={(e) => setLanguage(e.target.value)}
              style={{ width: '150px' }}
            >
              {SUPPORTED_LANGUAGES.map(({ code, label }) => (
                <option key={code} value={code}>{label}</option>
              ))}
            </select>
          </div>

          {pushState !== 'unsupported' && (
            <div className="settings-pref-row" style={{ marginTop: '16px' }}>
              <div>
                <div className="settings-pref-label">{tr('ui.settings.pushNotifications', 'Push Notifications')}</div>
                <div className="settings-pref-help">
                  {pushState === 'subscribed'
                    ? tr('ui.settings.remindersReachThisDeviceEven', 'Reminders reach this device even when the app is closed')
                    : pushState === 'denied'
                      ? tr('ui.settings.blockedInYourBrowserAllow', 'Blocked in your browser — allow notifications for ayuraai.in to enable')
                      : tr('ui.settings.getRemindersOnThisDevice', 'Get reminders on this device even when the app is closed')}
                </div>
              </div>
              <button
                type="button"
                className={`btn btn-sm ${pushState === 'subscribed' ? 'btn-secondary' : 'btn-primary'}`}
                onClick={togglePush}
                disabled={pushState === 'busy' || pushState === 'denied'}
              >
                {pushState === 'busy' ? '…' : pushState === 'subscribed' ? tr('ui.settings.turnOff', 'Turn off') : tr('ui.settings.enable', 'Enable')}
              </button>
            </div>
          )}
        </m.div>

        {/* Profile form */}
        <m.form className="settings-card" onSubmit={saveProfile} variants={staggerItem}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <h2 className="settings-section-title" style={{ margin: 0 }}>{tr('ui.settings.healthProfile', 'Health Profile')}</h2>
            {autoSaveStatus === 'saving' && (
              <span className="settings-autosave saving">{tr('ui.settings.saving', 'Saving…')}</span>
            )}
            {autoSaveStatus === 'saved' && (
              <span className="settings-autosave saved">{tr('ui.settings.saved', '✓ Saved')}</span>
            )}
          </div>
          <div className="settings-grid">
            <div className="input-group">
              <label htmlFor="settings-age">{tr('ui.settings.age', 'Age')}</label>
              <input id="settings-age" type="number" name="age" value={form.age} onChange={handleChange} min={10} max={120} />
            </div>
            <div className="input-group">
              <label htmlFor="settings-height-cm">{tr('ui.settings.heightCm', 'Height (cm)')}</label>
              <input id="settings-height-cm" type="number" name="height_cm" value={form.height_cm} onChange={handleChange} step="0.1" />
            </div>
            <div className="input-group">
              <label htmlFor="settings-weight-kg">{tr('ui.settings.weightKg', 'Weight (kg)')}</label>
              <input id="settings-weight-kg" type="number" name="weight_kg" value={form.weight_kg} onChange={handleChange} step="0.1" />
            </div>
            <div className="input-group">
              <label htmlFor="settings-fitness-level">{tr('ui.settings.fitnessLevel', 'Fitness Level')}</label>
              <select id="settings-fitness-level" name="fitness_level" value={form.fitness_level} onChange={handleChange}>
                <option value="">{tr('ui.settings.select', 'Select')}</option>
                <option value="beginner">{tr('ui.settings.beginner', 'Beginner')}</option>
                <option value="intermediate">{tr('ui.settings.intermediate', 'Intermediate')}</option>
                <option value="advanced">{tr('ui.settings.advanced', 'Advanced')}</option>
              </select>
            </div>
            <div className="input-group">
              <label htmlFor="settings-activity-level">{tr('ui.settings.activityLevel', 'Activity Level')}</label>
              <select id="settings-activity-level" name="activity_level" value={form.activity_level} onChange={handleChange}>
                <option value="">{tr('ui.settings.select', 'Select')}</option>
                <option value="sedentary">{tr('ui.settings.sedentary', 'Sedentary')}</option>
                <option value="light">{tr('ui.settings.light', 'Light')}</option>
                <option value="moderate">{tr('ui.settings.moderate', 'Moderate')}</option>
                <option value="active">{tr('ui.settings.active', 'Active')}</option>
                <option value="very_active">{tr('ui.settings.veryActive', 'Very Active')}</option>
              </select>
            </div>
            <div className="input-group">
              <label htmlFor="settings-goal">{tr('ui.settings.goal', 'Goal')}</label>
              <select id="settings-goal" name="goal" value={form.goal} onChange={handleChange}>
                <option value="">{tr('ui.settings.select', 'Select')}</option>
                <option value="weight_loss">{tr('ui.settings.weightLoss', 'Weight Loss')}</option>
                <option value="muscle_gain">{tr('ui.settings.muscleGain', 'Muscle Gain')}</option>
                <option value="flexibility">{tr('ui.settings.flexibility', 'Flexibility')}</option>
                <option value="balance">{tr('ui.settings.balance', 'Balance')}</option>
                <option value="detox">{tr('ui.settings.detox', 'Detox')}</option>
                <option value="general_wellness">{tr('ui.settings.generalWellness', 'General Wellness')}</option>
              </select>
            </div>
          </div>

          <div style={{ marginTop: '16px' }}>
            <label htmlFor="settings-condition-search" style={{ display: 'block', marginBottom: '10px', fontWeight: 600, fontSize: '0.9rem' }}>{tr('ui.settings.medicalConditions', 'Medical Conditions')}</label>
            <input
              id="settings-condition-search"
              className="onb-condition-search"
              type="text"
              placeholder={tr('ui.settings.searchConditions', 'Search conditions…')}
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
                {tr('ui.settings.notListedAddHereComma', 'Not listed? Add here (comma-separated)')}
              </span>
              <input
                className="onb-condition-search"
                type="text"
                placeholder={tr('ui.settings.eGSarcoidosisHemophilia', 'e.g. sarcoidosis, hemophilia')}
                value={otherCondition}
                onChange={e => setOtherCondition(e.target.value)}
              />
            </div>
          </div>
          <div className="input-group">
            <label htmlFor="settings-satmya">{tr('ui.settings.howLongHaveYouFollowed', 'How long have you followed your current diet & lifestyle? (Satmya)')}</label>
            <select id="settings-satmya" name="satmya" value={form.satmya} onChange={handleChange}>
              <option value="">{tr('ui.settings.select2', 'Select…')}</option>
              <option value="less_than_1y">{tr('ui.settings.lessThan1Year', 'Less than 1 year')}</option>
              <option value="1_to_5y">{tr('ui.settings.n15Years', '1–5 years')}</option>
              <option value="over_5y">{tr('ui.settings.moreThan5Years', 'More than 5 years')}</option>
            </select>
          </div>

          <div className="input-group">
            <label htmlFor="settings-koshtha">{tr('ui.settings.bowelTendencyKoshthaUsedFor', 'Bowel Tendency (Koshtha) — used for Panchakarma personalisation')}</label>
            <select id="settings-koshtha" name="koshtha" value={form.koshtha} onChange={handleChange}>
              <option value="">{tr('ui.settings.select2', 'Select…')}</option>
              <option value="sama">{tr('ui.settings.samaRegularOnceDaily', 'Sama — Regular once daily')}</option>
              <option value="krura">{tr('ui.settings.kruraHardInfrequentTendsToward', 'Krura — Hard / infrequent (tends toward constipation)')}</option>
              <option value="mridu">{tr('ui.settings.mriduLooseFrequentTendsToward', 'Mridu — Loose / frequent (tends toward loose stools)')}</option>
            </select>
          </div>

          <div className="input-group">
            <label htmlFor="settings-current-symptoms">{tr('ui.settings.currentSymptomsCommaSeparated', 'Current Symptoms (comma-separated)')}</label>
            <input id="settings-current-symptoms" name="current_symptoms" value={form.current_symptoms} onChange={handleChange} placeholder={tr('ui.settings.eGFatigueBloatingInsomnia', 'e.g. fatigue, bloating, insomnia')} />
          </div>
          <div className="input-group">
            <label htmlFor="settings-current-medications">{tr('ui.settings.currentMedicationsCommaSeparated', 'Current Medications (comma-separated)')}</label>
            <input id="settings-current-medications" name="current_medications" value={form.current_medications} onChange={handleChange} placeholder={tr('ui.settings.eGMetforminAtenolol', 'e.g. metformin, atenolol')} />
          </div>

          <div className="settings-action-row">
            <m.button className="btn btn-primary" type="submit" disabled={saving} whileTap={{ scale: 0.97 }}>
              {saving ? tr('ui.settings.saving', 'Saving…') : <><Save size={16} strokeWidth={2} />{' '}{tr('ui.settings.saveProfile', 'Save Profile')}</>}
            </m.button>
            <m.button className="btn btn-secondary" type="button" onClick={() => navigate('/onboarding?retake=true')} whileTap={{ scale: 0.97 }}>
              <Brain size={16} strokeWidth={2} />{' '}{tr('ui.settings.retakeDoshaQuiz', 'Retake Dosha Quiz')}
            </m.button>
          </div>
        </m.form>

        {/* Password Change (local auth only) */}
        {isLocal && (
          <m.form className="settings-card" onSubmit={changePassword} variants={staggerItem}>
            <h2 className="settings-section-title">{tr('ui.settings.changePassword', 'Change Password')}</h2>
            <div className="settings-grid">
              <div className="input-group">
                <label htmlFor="settings-pw-current">{tr('ui.settings.currentPassword', 'Current Password')}</label>
                <input id="settings-pw-current" type="password" value={passwords.current} onChange={e => setPasswords(p => ({ ...p, current: e.target.value }))} required />
              </div>
              <div className="input-group">
                <label htmlFor="settings-pw-new">{tr('ui.settings.newPassword', 'New Password')}</label>
                <input id="settings-pw-new" type="password" value={passwords.new} onChange={e => setPasswords(p => ({ ...p, new: e.target.value }))} minLength={8} required />
              </div>
              <div className="input-group">
                <label htmlFor="settings-pw-confirm">{tr('ui.settings.confirmNewPassword', 'Confirm New Password')}</label>
                <input id="settings-pw-confirm" type="password" value={passwords.confirm} onChange={e => setPasswords(p => ({ ...p, confirm: e.target.value }))} required />
              </div>
            </div>
            <m.button className="btn btn-primary" type="submit" disabled={savingPw} style={{ marginTop: '16px' }} whileTap={{ scale: 0.97 }}>
              {savingPw ? tr('ui.settings.changing', 'Changing…') : <><KeyRound size={16} strokeWidth={2} />{' '}{tr('ui.settings.changePassword', 'Change Password')}</>}
            </m.button>
          </m.form>
        )}

        {/* WhatsApp — renders nothing until the server has it switched on */}
        <WhatsAppSettings variants={staggerItem} />

        {/* Export wellness data */}
        <m.div className="settings-card" variants={staggerItem}>
          <h2 className="settings-section-title">{tr('ui.settings.exportWellnessData', 'Export Wellness Data')}</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 20 }}>
            {tr('ui.settings.downloadAVaidyaHandoffPdf', 'Download a Vaidya-handoff PDF — your Prakriti & Vikriti assessment, Agni, Ama, Ojas, conditions, and plans in one summary to share with your Ayurvedic physician — or export your progress logs as a CSV spreadsheet.')}
          </p>
          <div className="settings-action-row">
            <m.button className="btn btn-primary" onClick={downloadPdf} disabled={exportingPdf} whileTap={{ scale: 0.97 }}>
              {exportingPdf ? tr('ui.settings.generating', 'Generating…') : <><FileText size={16} strokeWidth={2} />{' '}{tr('ui.settings.downloadVaidyaReportPdf', 'Download Vaidya Report (PDF)')}</>}
            </m.button>
            <m.button className="btn btn-secondary" onClick={downloadCsv} disabled={exportingCsv} whileTap={{ scale: 0.97 }}>
              {exportingCsv ? tr('ui.settings.exporting', 'Exporting…') : <><Table2 size={16} strokeWidth={2} />{' '}{tr('ui.settings.downloadProgressCsv', 'Download Progress CSV')}</>}
            </m.button>
          </div>
        </m.div>

        {/* Feedback — the permanent home for the widget. On phones this is the
            ONLY entry point: the floating FAB is hidden there because it sat over
            scrollable content and stole taps (see FeedbackWidget.css). */}
        <m.div className="settings-card" variants={staggerItem}>
          <h2 className="settings-section-title">{tr('ui.settings.helpUsImprove', 'Help us improve')}</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 20 }}>
            {tr('ui.settings.foundABugAMedical', 'Found a bug, a medical or content error, or something that could work better? Tell us — it goes straight to the team.')}
          </p>
          <div className="settings-action-row">
            <m.button
              className="btn btn-primary"
              onClick={() => window.dispatchEvent(new CustomEvent('ayura:open-feedback'))}
              whileTap={{ scale: 0.97 }}
            >
              <MessageSquare size={16} strokeWidth={2} />{' '}{tr('ui.settings.sendFeedback', 'Send Feedback')}
            </m.button>
          </div>
        </m.div>

        {/* Danger zone */}
        <m.div className="settings-card settings-danger" variants={staggerItem}>
          <h2 className="settings-section-title settings-danger-title">{tr('ui.settings.accountActions', 'Account Actions')}</h2>
          <div className="settings-action-row">
            <m.button className="btn btn-secondary" onClick={exportAccountData} whileTap={{ scale: 0.97 }}>
              <Package size={16} strokeWidth={2} />{' '}{tr('ui.settings.exportData', 'Export Data')}
            </m.button>
            <m.button className="btn btn-secondary" onClick={() => { logout(); navigate('/login') }} whileTap={{ scale: 0.97 }}>
              <LogOut size={16} strokeWidth={2} />{' '}{tr('ui.settings.logOut', 'Log Out')}
            </m.button>
            <m.button className="btn btn-secondary settings-btn-danger" onClick={deleteAccount} whileTap={{ scale: 0.97 }}>
              <Trash2 size={16} strokeWidth={2} />{' '}{tr('ui.settings.deleteAccount', 'Delete Account')}
            </m.button>
          </div>
        </m.div>
      </m.div>
    </div>
    </>
  )
}
