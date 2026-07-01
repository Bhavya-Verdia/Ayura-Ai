import React, { useState, useEffect, useCallback, useRef } from 'react'
import { m, AnimatePresence } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { remindersAPI } from '../api/client'
import {
  Pill, Flower2, Brain, Salad, ClipboardCheck, AlarmClock,
  Bell, Pencil, X, Plus, Clock, TriangleAlert,
} from 'lucide-react'
import './Reminders.css'

// ── Constants ────────────────────────────────────────────────
const TYPE_OPTIONS = [
  { value: 'medication',  label: 'Medication',  Icon: Pill },
  { value: 'yoga',        label: 'Yoga',         Icon: Flower2 },
  { value: 'meditation',  label: 'Meditation',   Icon: Brain },
  { value: 'diet',        label: 'Diet',         Icon: Salad },
  { value: 'checkin',     label: 'Check-In',     Icon: ClipboardCheck },
  { value: 'custom',      label: 'Custom',       Icon: AlarmClock },
]
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const DAY_VALUES = [1, 2, 3, 4, 5, 6, 0] // ISO weekday, Sun=0

function getTypeInfo(type) {
  return TYPE_OPTIONS.find(t => t.value === type) || TYPE_OPTIONS[TYPE_OPTIONS.length - 1]
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const [h, m] = timeStr.split(':')
  const hNum = parseInt(h, 10)
  const ampm = hNum >= 12 ? 'PM' : 'AM'
  const h12  = hNum % 12 || 12
  return `${h12}:${m} ${ampm}`
}

// ── Empty form state ─────────────────────────────────────────
const EMPTY_FORM = {
  title: '',
  type: 'medication',
  time: '08:00',
  days_of_week: [1, 2, 3, 4, 5],
  description: '',
}

// ── Frontend ⇄ API shape adapters ────────────────────────────
// The API speaks {id, reminder_type, days:[names], timezone}; the UI uses
// {_id, type, days_of_week:[ISO nums]}. Reminders fire in the user's timezone,
// so we send the browser's IANA zone with every create/edit.
const DAY_NUM_TO_NAME = { 0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday', 4: 'thursday', 5: 'friday', 6: 'saturday' }
const DAY_NAME_TO_NUM = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 }
const BROWSER_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

function fromApiShape(r) {
  return {
    _id: r.id ?? r._id,
    title: r.title ?? '',
    time: r.time ?? '08:00',
    type: r.reminder_type ?? 'custom',
    days_of_week: (r.days ?? []).map(d => DAY_NAME_TO_NUM[String(d).toLowerCase()]).filter(n => n !== undefined),
    description: r.description ?? '',
    is_active: r.is_active ?? true,
    timezone: r.timezone ?? BROWSER_TZ,
  }
}

function toApiShape(form) {
  return {
    title: form.title,
    time: form.time,
    reminder_type: form.type,
    days: (form.days_of_week ?? []).map(n => DAY_NUM_TO_NAME[n]).filter(Boolean),
    description: form.description ?? '',
    timezone: BROWSER_TZ,
  }
}

// ── DayChips ─────────────────────────────────────────────────
function DayChips({ selected, onChange, compact = false }) {
  const toggleDay = (val) => {
    if (selected.includes(val)) {
      onChange(selected.filter(d => d !== val))
    } else {
      onChange([...selected, val].sort((a, b) => a - b))
    }
  }
  return (
    <div className={`rem-day-chips${compact ? ' rem-day-chips--compact' : ''}`}>
      {DAY_LABELS.map((label, i) => {
        const val = DAY_VALUES[i]
        const active = selected.includes(val)
        return (
          <button
            key={label}
            type="button"
            className={`rem-day-chip${active ? ' rem-day-chip--active' : ''}`}
            onClick={() => toggleDay(val)}
            aria-pressed={active}
            aria-label={label}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}

// ── Toggle Switch ────────────────────────────────────────────
function ToggleSwitch({ checked, onChange, label }) {
  return (
    <label className="rem-toggle" aria-label={label}>
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
      />
      <span className="rem-toggle-slider" />
    </label>
  )
}

// ── Reminder Form ─────────────────────────────────────────────
function ReminderForm({ initial = EMPTY_FORM, onSave, onCancel, saving }) {
  const [form, setForm] = useState({ ...initial })
  const titleRef = useRef(null)

  useEffect(() => {
    titleRef.current?.focus()
  }, [])

  const set = (key, val) => setForm(prev => ({ ...prev, [key]: val }))

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.title.trim()) return
    onSave(form)
  }

  return (
    <m.form
      className="rem-form"
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="rem-form-grid">
        {/* Title */}
        <div className="input-group rem-form-full">
          <label htmlFor="rem-title">Title *</label>
          <input
            id="rem-title"
            ref={titleRef}
            type="text"
            value={form.title}
            onChange={e => set('title', e.target.value)}
            placeholder="e.g. Morning Ashwagandha"
            required
            maxLength={80}
          />
        </div>

        {/* Type */}
        <div className="input-group">
          <label htmlFor="rem-type">Type</label>
          <select
            id="rem-type"
            value={form.type}
            onChange={e => set('type', e.target.value)}
          >
            {TYPE_OPTIONS.map(t => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {/* Time */}
        <div className="input-group">
          <label htmlFor="rem-time">Time</label>
          <input
            id="rem-time"
            type="time"
            value={form.time}
            onChange={e => set('time', e.target.value)}
          />
        </div>

        {/* Days */}
        <div className="input-group rem-form-full">
          <label>Days of Week</label>
          <DayChips
            selected={form.days_of_week}
            onChange={val => set('days_of_week', val)}
          />
        </div>

        {/* Description */}
        <div className="input-group rem-form-full">
          <label htmlFor="rem-desc">Description (optional)</label>
          <textarea
            id="rem-desc"
            value={form.description}
            onChange={e => set('description', e.target.value)}
            placeholder="Add notes or dosage details…"
            rows={3}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="rem-form-actions">
        <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <m.button
          type="submit"
          className="btn btn-primary btn-sm"
          disabled={saving || !form.title.trim()}
          whileTap={{ scale: 0.96 }}
        >
          {saving ? (
            <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Saving…</>
          ) : (
            initial === EMPTY_FORM ? '+ Add Reminder' : '✓ Save Changes'
          )}
        </m.button>
      </div>
    </m.form>
  )
}

// ── Delete Confirmation ───────────────────────────────────────
function DeleteConfirm({ onConfirm, onCancel }) {
  return (
    <m.div
      className="rem-delete-confirm"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      <span>Delete this reminder?</span>
      <div className="rem-delete-actions">
        <button className="btn btn-secondary btn-sm" onClick={onCancel}>No</button>
        <button className="btn btn-sm rem-btn-danger" onClick={onConfirm}>Yes, delete</button>
      </div>
    </m.div>
  )
}

// ── Reminder Card ─────────────────────────────────────────────
function ReminderCard({ reminder, onToggle, onDelete, onEdit, index }) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [editing, setEditing]             = useState(false)
  const [saving, setSaving]               = useState(false)

  const typeInfo = getTypeInfo(reminder.type)

  const handleToggle = async () => {
    await onToggle(reminder._id, !reminder.is_active)
  }

  const handleEdit = async (formData) => {
    setSaving(true)
    await onEdit(reminder._id, formData)
    setSaving(false)
    setEditing(false)
  }

  return (
    <m.div
      layout
      className={`rem-card${reminder.is_active ? '' : ' rem-card--inactive'}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -30, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Main row */}
      <div className="rem-card-main">
        {/* Icon */}
        <div className="rem-card-icon-wrap">
          <span className="rem-card-icon" aria-label={typeInfo.label}>
            <typeInfo.Icon size={18} strokeWidth={2} />
          </span>
        </div>

        {/* Info */}
        <div className="rem-card-info">
          <div className="rem-card-top">
            <span className="rem-card-title">{reminder.title}</span>
            <span className="rem-card-time"><Clock size={13} strokeWidth={2} /> {formatTime(reminder.time)}</span>
          </div>
          {reminder.description && (
            <p className="rem-card-desc">{reminder.description}</p>
          )}
          <DayChips
            selected={reminder.days_of_week ?? []}
            onChange={() => {}}
            compact
          />
        </div>

        {/* Controls */}
        <div className="rem-card-controls">
          <ToggleSwitch
            checked={reminder.is_active}
            onChange={handleToggle}
            label={`Toggle ${reminder.title}`}
          />
          <button
            className="rem-icon-btn rem-icon-btn--edit"
            onClick={() => { setEditing(e => !e); setConfirmDelete(false) }}
            title="Edit"
            aria-label="Edit reminder"
          >
            <Pencil size={14} strokeWidth={2} />
          </button>
          <button
            className="rem-icon-btn rem-icon-btn--delete"
            onClick={() => { setConfirmDelete(c => !c); setEditing(false) }}
            title="Delete"
            aria-label="Delete reminder"
          >
            <X size={15} strokeWidth={2} />
          </button>
        </div>
      </div>

      {/* Inline edit form */}
      <AnimatePresence>
        {editing && (
          <ReminderForm
            initial={{ ...reminder }}
            onSave={handleEdit}
            onCancel={() => setEditing(false)}
            saving={saving}
          />
        )}
      </AnimatePresence>

      {/* Delete confirm */}
      <AnimatePresence>
        {confirmDelete && (
          <DeleteConfirm
            onConfirm={() => { setConfirmDelete(false); onDelete(reminder._id) }}
            onCancel={() => setConfirmDelete(false)}
          />
        )}
      </AnimatePresence>
    </m.div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────
function ReminderSkeleton() {
  return (
    <div className="rem-skeleton-wrap">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="rem-skeleton-item">
          <div className="rem-skeleton-icon skeleton" />
          <div className="rem-skeleton-body">
            <div className="rem-skeleton-title skeleton" />
            <div className="rem-skeleton-days skeleton" />
          </div>
          <div className="rem-skeleton-toggle skeleton" />
        </div>
      ))}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────
export default function Reminders() {
  const [reminders, setReminders] = useState([])
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]   = useState(false)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState(null)
  const [success, setSuccess]     = useState(null)

  const showSuccess = (msg) => {
    setSuccess(msg)
    setTimeout(() => setSuccess(null), 3000)
  }

  const fetchReminders = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await remindersAPI.list()
      const data = Array.isArray(res.data) ? res.data : (res.data?.reminders ?? [])
      setReminders(data.map(fromApiShape))
    } catch (err) {
      console.error('Failed to load reminders:', err)
      setError('Could not load reminders. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchReminders() }, [fetchReminders])

  const handleCreate = async (formData) => {
    setSaving(true)
    setError(null)
    try {
      const res = await remindersAPI.create(toApiShape(formData))
      setReminders(prev => [fromApiShape(res.data), ...prev])
      setShowForm(false)
      showSuccess('Reminder created!')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create reminder.')
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (id, is_active) => {
    // Optimistic
    setReminders(prev => prev.map(r => r._id === id ? { ...r, is_active } : r))
    try {
      await remindersAPI.update(id, { is_active })
    } catch {
      setReminders(prev => prev.map(r => r._id === id ? { ...r, is_active: !is_active } : r))
    }
  }

  const handleEdit = async (id, formData) => {
    setError(null)
    try {
      const res = await remindersAPI.update(id, toApiShape(formData))
      setReminders(prev => prev.map(r => r._id === id ? fromApiShape(res.data) : r))
      showSuccess('Reminder updated!')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update reminder.')
      throw err
    }
  }

  const handleDelete = async (id) => {
    setReminders(prev => prev.filter(r => r._id !== id))
    try {
      await remindersAPI.remove(id)
      showSuccess('Reminder deleted.')
    } catch {
      fetchReminders()
    }
  }

  const activeCount   = reminders.filter(r => r.is_active).length
  const inactiveCount = reminders.length - activeCount

  return (
    <>
      <Helmet>
        <title>Reminders — Ayura AI</title>
        <meta name="description" content="Manage your Ayura AI wellness reminders for medications, yoga, meditation, and more." />
      </Helmet>

      <div className="rem-root">
        <div className="rem-orb rem-orb-a" aria-hidden="true" />
        <div className="rem-orb rem-orb-b" aria-hidden="true" />

        <div className="rem-container">
          {/* Header */}
          <m.div
            className="rem-header"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="rem-header-left">
              <h1 className="rem-page-title gradient-text">Reminders</h1>
              <p className="rem-page-sub">
                {reminders.length === 0
                  ? 'No reminders yet — add your first one'
                  : `${activeCount} active · ${inactiveCount} paused`}
              </p>
            </div>
            <m.button
              className="btn btn-primary rem-add-btn"
              onClick={() => setShowForm(f => !f)}
              whileTap={{ scale: 0.96 }}
              aria-expanded={showForm}
            >
              <span className="rem-add-icon">{showForm ? <X size={16} strokeWidth={2.2} /> : <Plus size={16} strokeWidth={2.2} />}</span>
              {showForm ? 'Cancel' : 'New Reminder'}
            </m.button>
          </m.div>

          {/* Toasts */}
          <AnimatePresence>
            {error && (
              <m.div
                className="rem-toast rem-toast--error"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><TriangleAlert size={15} strokeWidth={2} /> {error}</span>
                <button onClick={() => setError(null)} className="rem-toast-close" aria-label="Dismiss"><X size={14} strokeWidth={2} /></button>
              </m.div>
            )}
            {success && (
              <m.div
                className="rem-toast rem-toast--success"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                {success}
              </m.div>
            )}
          </AnimatePresence>

          {/* Add form slide-in */}
          <AnimatePresence>
            {showForm && (
              <m.div
                className="rem-form-panel"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className="rem-form-panel-inner">
                  <h2 className="rem-form-title">New Reminder</h2>
                  <ReminderForm
                    initial={EMPTY_FORM}
                    onSave={handleCreate}
                    onCancel={() => setShowForm(false)}
                    saving={saving}
                  />
                </div>
              </m.div>
            )}
          </AnimatePresence>

          {/* Type legend */}
          <m.div
            className="rem-legend"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.15 }}
          >
            {TYPE_OPTIONS.map(t => (
              <span key={t.value} className="rem-legend-item">
                <span className="rem-legend-icon"><t.Icon size={14} strokeWidth={2} /></span>
                <span>{t.label}</span>
              </span>
            ))}
          </m.div>

          {/* List */}
          {loading ? (
            <ReminderSkeleton />
          ) : reminders.length === 0 ? (
            <m.div
              className="rem-empty"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="rem-empty-icon"><Bell size={28} strokeWidth={1.8} /></div>
              <h2 className="rem-empty-title">No reminders yet</h2>
              <p className="rem-empty-sub">Create your first reminder to stay on track with your wellness routine.</p>
              <button
                className="btn btn-primary"
                onClick={() => setShowForm(true)}
              >
                + Add Reminder
              </button>
            </m.div>
          ) : (
            <div className="rem-list">
              <AnimatePresence mode="popLayout">
                {reminders.map((reminder, i) => (
                  <ReminderCard
                    key={reminder._id}
                    reminder={reminder}
                    onToggle={handleToggle}
                    onDelete={handleDelete}
                    onEdit={handleEdit}
                    index={i}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
