// The panchakarma preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the panchakarma schema.
import { GOALS } from './options';

export default function PanchakarmaFields({ form, handleChange }) {
  return (
      <>
        <div className="pref-input-group">
          <label>Detox Goal</label>
          <select name="panchakarma_goal" value={form.panchakarma_goal || ''} onChange={handleChange} required>
            <option value="">Select goal...</option>
            {GOALS.panchakarma.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Available Days (3–21)</label>
            <input type="number" name="available_time_days" min={3} max={21} value={form.available_time_days || ''} onChange={handleChange} required />
          </div>
          <div className="pref-input-group">
            <label>Setting</label>
            <select name="setting" value={form.setting || ''} onChange={handleChange} required>
              <option value="home">Home Therapies (Shamana)</option>
              <option value="clinic">Clinical Reference Plan (Vaidya-Assisted)</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Prior PK Experience</label>
            <select name="detox_experience" value={form.detox_experience || ''} onChange={handleChange} required>
              <option value="none">First time</option>
              <option value="some">Done 1–2 courses</option>
              <option value="experienced">Experienced (3+ courses)</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Koshtha (Bowel Tendency)</label>
            <select name="koshtha" value={form.koshtha || ''} onChange={handleChange} required>
              <option value="">Select...</option>
              <option value="sama">Sama — Regular (once daily)</option>
              <option value="krura">Krura — Hard / infrequent (constipated)</option>
              <option value="mridu">Mridu — Loose / frequent</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Daily Self-Care Time</label>
            <select name="self_care_time_per_day" value={form.self_care_time_per_day || ''} onChange={handleChange} required>
              <option value="15 min">15 min</option>
              <option value="30 min">30 min</option>
              <option value="1 hour">1 hour</option>
              <option value="2+ hours">2+ hours</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Herb Access</label>
            <select name="access_to_ayurvedic_herbs" value={form.access_to_ayurvedic_herbs || ''} onChange={handleChange} required>
              <option value="willing_to_buy">Willing to Buy</option>
              <option value="yes">I have access</option>
              <option value="no">Kitchen spices only</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Diet Adherence</label>
            <select name="diet_adherence_ability" value={form.diet_adherence_ability || ''} onChange={handleChange} required>
              <option value="partial">Partial</option>
              <option value="strict">Strict (Kitchari Only)</option>
              <option value="lifestyle_only">Lifestyle Only</option>
            </select>
          </div>
        </div>
        {/* Also asked on the remedies form; the server unions the two, so either
            answer reaches both herb-doubling checks. It once sat only on the
            remedies form, whose schema did not declare it, and every answer was
            dropped on save. */}
        <div className="pref-input-group pref-full">
          <label>Ayurvedic Medicines You Take Now <span className="pref-hint">(optional, comma-separated)</span></label>
          <input
            type="text"
            name="current_ayurvedic_medicines"
            placeholder="e.g. Ashwagandha Churna, Brahmi Ghrita"
            value={form.current_ayurvedic_medicines || ''}
            onChange={handleChange}
          />
        </div>
      </>
  );
}
