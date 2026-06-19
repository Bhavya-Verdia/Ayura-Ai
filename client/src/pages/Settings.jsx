import { useState, useRef, Suspense } from 'react'
import { useAuth } from '../providers/AuthContext'
import { privacyAPI, profileAPI } from '../api/client'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Helmet } from 'react-helmet-async'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from '../providers/ThemeProvider'
import React from 'react'
import './Settings.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

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

  const [form, setForm] = useState({
    age: profile?.age || '',
    height_cm: profile?.height_cm || '',
    weight_kg: profile?.weight_kg || '',
    fitness_level: profile?.fitness_level || '',
    activity_level: profile?.activity_level || '',
    goal: profile?.goal || '',
    medical_history: (profile?.medical_history || []).join(', '),
    current_symptoms: (profile?.current_symptoms || []).join(', '),
    current_medications: (profile?.current_medications || []).join(', '),
  })

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
        medical_history:    formData.medical_history    ? formData.medical_history.split(',').map(s => s.trim()).filter(Boolean)    : undefined,
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
        medical_history: form.medical_history ? form.medical_history.split(',').map(s => s.trim()).filter(Boolean) : undefined,
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

      <motion.div
        className="settings-container"
        variants={staggerContainer}
        initial="initial"
        animate="animate"
      >
        <motion.div variants={staggerItem} className="settings-header">
          <div>
            <h1 className="settings-page-title">Settings</h1>
            <p className="settings-page-sub">Manage your profile, health data, and account</p>
          </div>
          <motion.button className="btn btn-secondary" onClick={() => navigate('/dashboard')} whileTap={{ scale: 0.97 }}>
            ← Back to Dashboard
          </motion.button>
        </motion.div>

        <AnimatePresence>
          {notice.message && (
            <motion.div
              className={`settings-notice ${notice.type}`}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {notice.message}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Account Info */}
        <motion.div className="settings-card" variants={staggerItem}>
          <h2 className="settings-section-title">Account</h2>
          <div className="settings-account-row">
            <div className="settings-avatar-wrap">
              {avatarUrl ? (
                <img src={avatarUrl} alt="Avatar" className="settings-avatar-img" />
              ) : (
                <div className="settings-avatar-placeholder">
                  {profile?.name?.charAt(0)?.toUpperCase() || '?'}
                </div>
              )}
              <label className="settings-avatar-btn" title="Upload avatar">
                📷
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
        </motion.div>

        {/* Theme Settings */}
        <motion.div className="settings-card" variants={staggerItem}>
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
        </motion.div>

        {/* Profile form */}
        <motion.form className="settings-card" onSubmit={saveProfile} variants={staggerItem}>
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

          <div className="input-group" style={{ marginTop: '16px' }}>
            <label>Medical History (comma-separated)</label>
            <input name="medical_history" value={form.medical_history} onChange={handleChange} placeholder="e.g. diabetes, hypertension" />
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
            <motion.button className="btn btn-primary" type="submit" disabled={saving} whileTap={{ scale: 0.97 }}>
              {saving ? 'Saving...' : '💾 Save Profile'}
            </motion.button>
            <motion.button className="btn btn-secondary" type="button" onClick={() => navigate('/onboarding?retake=true')} whileTap={{ scale: 0.97 }}>
              🧬 Retake Dosha Quiz
            </motion.button>
          </div>
        </motion.form>

        {/* Password Change (local auth only) */}
        {isLocal && (
          <motion.form className="settings-card" onSubmit={changePassword} variants={staggerItem}>
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
            <motion.button className="btn btn-primary" type="submit" disabled={savingPw} style={{ marginTop: '16px' }} whileTap={{ scale: 0.97 }}>
              {savingPw ? 'Changing...' : '🔒 Change Password'}
            </motion.button>
          </motion.form>
        )}

        {/* Danger zone */}
        <motion.div className="settings-card settings-danger" variants={staggerItem}>
          <h2 className="settings-section-title settings-danger-title">Account Actions</h2>
          <div className="settings-action-row">
            <motion.button className="btn btn-secondary" onClick={exportAccountData} whileTap={{ scale: 0.97 }}>
              📦 Export Data
            </motion.button>
            <motion.button className="btn btn-secondary" onClick={() => { logout(); navigate('/login') }} whileTap={{ scale: 0.97 }}>
              🚪 Log Out
            </motion.button>
            <motion.button className="btn btn-secondary settings-btn-danger" onClick={deleteAccount} whileTap={{ scale: 0.97 }}>
              🗑️ Delete Account
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </div>
    </>
  )
}
