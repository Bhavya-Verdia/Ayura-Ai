// The routine preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the routine schema.

export default function RoutineFields({ form, setForm, handleChange }) {
  return (
      <>
        <p className="pref-notice">
          Your daily routine is personalised from your Dosha, season, conditions, and the preferences below. Gym and Yoga integration pulls your existing plan schedules automatically.
        </p>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Wake Preference</label>
            <select name="wake_preference" value={form.wake_preference || 'natural'} onChange={handleChange} required>
              <option value="early">Early — 4:30–5:30 AM</option>
              <option value="natural">Natural — the hour your Dosha and season suggest</option>
              <option value="late">Late — 6:30–7:30 AM</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Occupation Type</label>
            <select name="occupation_type" value={form.occupation_type || 'moderately_active'} onChange={handleChange} required>
              <option value="sedentary">Sedentary — mostly desk / driving</option>
              <option value="moderately_active">Moderately Active — mixed</option>
              <option value="very_active">Very Active — labour / athlete</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>
              Agni (Digestive Fire) Type
              <span className="pref-hint-sub"> — how would you describe your digestion?</span>
            </label>
            <select name="agni_type_self_report" value={form.agni_type_self_report || 'assessed'} onChange={handleChange} required>
              <option value="assessed">Use my assessment</option>
              <option value="sama">Sama — Balanced, regular digestion</option>
              <option value="manda">Manda — Slow, heavy, bloated after meals</option>
              <option value="tikshna">Tikshna — Sharp, hungry quickly, acidity</option>
              <option value="vishama">Vishama — Irregular, some days strong, some weak</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Intermittent Fasting Window</label>
            <select name="intermittent_fasting" value={form.intermittent_fasting || 'no'} onChange={handleChange}>
              <option value="no">No Fasting</option>
              <option value="12:12">12:12 — Balanced</option>
              <option value="14:10">14:10 — Moderate</option>
              <option value="16:8">16:8 — Advanced</option>
            </select>
          </div>
        </div>
        <div className="pref-input-group pref-full">
          <label>Fasting Days <span className="pref-hint">(optional, comma-separated)</span></label>
          <input
            type="text"
            name="fasting_days"
            placeholder="e.g. Monday, Ekadashi"
            value={form.fasting_days || ''}
            onChange={handleChange}
          />
        </div>
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint">Your gym and yoga plans <span>(their sessions are placed in your day — tap one to leave it out)</span></label>
          <div className="pref-chip-row">
            <button
              type="button"
              className={`pref-chip${!form.exclude_gym_plan ? ' active' : ''}`}
              aria-pressed={!form.exclude_gym_plan}
              onClick={() => setForm(p => ({ ...p, exclude_gym_plan: !p.exclude_gym_plan }))}
            >
              Include Gym Plan
            </button>
            <button
              type="button"
              className={`pref-chip${!form.exclude_yoga_plan ? ' active' : ''}`}
              aria-pressed={!form.exclude_yoga_plan}
              onClick={() => setForm(p => ({ ...p, exclude_yoga_plan: !p.exclude_yoga_plan }))}
            >
              Include Yoga Plan
            </button>
          </div>
        </div>
        {!form.exclude_gym_plan && (
          <div className="pref-input-group">
            <label>Gym Time</label>
            <select name="gym_time_of_day" value={form.gym_time_of_day || 'morning'} onChange={handleChange}>
              <option value="morning">Morning</option>
              <option value="evening">Evening (before dinner)</option>
            </select>
            <p className="pref-hint">Yoga goes at the time you chose on the yoga form.</p>
          </div>
        )}
      </>
  );
}
