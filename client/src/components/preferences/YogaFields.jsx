// The yoga preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the yoga schema.
import { GOALS, YOGA_SESSION_MINUTES, YOGA_PRANAYAMA_MINUTES, YOGA_SUGGESTED_MINUTES } from './options';

export default function YogaFields({ form, handleChange, renderInjuryChips }) {
  return (
      <>
        <div className="pref-input-group">
          <label htmlFor="pref-yoga_goal">Primary Focus</label>
          <select id="pref-yoga_goal" name="yoga_goal" value={form.yoga_goal || ''} onChange={handleChange} required>
            <option value="">Select your focus...</option>
            {GOALS.yoga.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-yoga_experience">Experience Level</label>
            <select id="pref-yoga_experience" name="yoga_experience" value={form.yoga_experience || 'beginner'} onChange={handleChange} required>
              <option value="none">None — never practiced</option>
              <option value="beginner">Beginner — under 1 year</option>
              <option value="intermediate">Intermediate — 1–3 years</option>
              <option value="advanced">Advanced — 3+ years</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-flexibility_level">Current Flexibility</label>
            <select id="pref-flexibility_level" name="flexibility_level" value={form.flexibility_level || 'moderate'} onChange={handleChange} required>
              <option value="low">Low — limited range</option>
              <option value="moderate">Moderate — average flexibility</option>
              <option value="high">High — very flexible</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-yoga_style_preference">Yoga Style</label>
            <select id="pref-yoga_style_preference" name="yoga_style_preference" value={form.yoga_style_preference || 'hatha'} onChange={handleChange} required>
              <option value="hatha">Hatha — slow, foundational</option>
              <option value="vinyasa">Vinyasa — flowing, dynamic</option>
              <option value="restorative">Restorative — passive, healing</option>
              <option value="yin">Yin — long holds, deep tissue</option>
              <option value="power">Power — strength-focused</option>
              <option value="ashtanga">Ashtanga — structured series</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-time_available_minutes">
              Session Duration
              {/* The same length every day of the week — the plan varies the
                  effort, not the slot, so this is the commitment being made. */}
              <span className="pref-hint-sub"> — the same every day; the plan varies the effort, not the time</span>
            </label>
            <select id="pref-time_available_minutes" name="time_available_minutes" value={form.time_available_minutes || YOGA_SUGGESTED_MINUTES[form.yoga_experience || 'beginner'] || 30} onChange={handleChange} required>
              {YOGA_SESSION_MINUTES.map(m => (
                <option key={m} value={m}>
                  {m} min — includes {YOGA_PRANAYAMA_MINUTES[form.yoga_experience || 'beginner']} min pranayama
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-time_of_day_preference">Time of Day</label>
            <select id="pref-time_of_day_preference" name="time_of_day_preference" value={form.time_of_day_preference || 'morning'} onChange={handleChange} required>
              <option value="morning">Morning</option>
              <option value="evening">Evening</option>
              <option value="both">Both</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-pranayama_interest">Include Pranayama?</label>
            <select id="pref-pranayama_interest" name="pranayama_interest" value={form.pranayama_interest || 'yes'} onChange={handleChange} required>
              <option value="yes">Yes</option>
              <option value="no">No</option>
              <option value="already_practice">Already Practice</option>
            </select>
          </div>
        </div>
        <div className="pref-input-group">
          <label htmlFor="pref-indoor_outdoor">Location</label>
          <select id="pref-indoor_outdoor" name="indoor_outdoor" value={form.indoor_outdoor || 'indoor'} onChange={handleChange} required>
            <option value="indoor">Indoor</option>
            <option value="outdoor">Outdoor</option>
            <option value="both">Both</option>
          </select>
        </div>
        <div className="pref-input-group">
          <label htmlFor="pref-physical_limitations_detail">Injuries or physical limitations <span className="pref-hint-sub">optional</span></label>
          {renderInjuryChips()}
          <input id="pref-physical_limitations_detail" type="text" name="physical_limitations_detail" maxLength={300}
            placeholder="Anything else? e.g. can't kneel"
            value={form.physical_limitations_detail || ''} onChange={handleChange} />
          <p className="pref-hint">
            Poses that load an injured area are left out, and anything we cannot
            match is named in the plan. Your gym plan reads these too.
          </p>
        </div>
      </>
  );
}
