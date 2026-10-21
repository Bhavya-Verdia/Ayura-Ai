// The remedies and medicines preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the remedies schema.

export default function RemedyFields({ form, handleChange, handleToggle }) {
  return (
      <>
        <p className="pref-notice">
          Recommendations are matched to your Vikriti (imbalance state), Agni, and conditions.
          Always consult a qualified Vaidya before starting Tier-2 formulations.
        </p>

        {/* ── Allopathic medications ── */}
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint">
            Current Allopathic Medications <span>(select all that apply — used for drug interaction safety)</span>
          </label>
          <div className="pref-chip-row">
            {[
              { value: 'blood_thinners',      label: 'Blood Thinners / Anticoagulants' },
              { value: 'diabetes_medication',  label: 'Diabetes Medication' },
              { value: 'thyroid_medication',   label: 'Thyroid Medication' },
              { value: 'antihypertensives',    label: 'Blood Pressure Medication' },
              { value: 'immunosuppressants',   label: 'Immunosuppressants / Steroids' },
              { value: 'sedatives',            label: 'Sedatives / Sleep Medication' },
              { value: 'antiepileptics',       label: 'Anti-Epileptics' },
              { value: 'antidepressants',      label: 'Antidepressants / Antipsychotics' },
              { value: 'cardiac_glycosides',   label: 'Cardiac Glycosides (Digoxin)' },
              { value: 'nsaids',               label: 'NSAIDs / Pain Relievers' },
              { value: 'hormone_therapy',      label: 'Hormone Therapy / OCP' },
              { value: 'antibiotics',          label: 'Antibiotics (current course)' },
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                className={`pref-chip${(form.current_allopathic_medications || []).includes(opt.value) ? ' active' : ''}`}
                onClick={() => handleToggle('current_allopathic_medications', opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Ama self-assessment ── */}
        <div className="pref-input-group">
          <label>
            Ama (Toxic Load) Self-Assessment
            <span className="pref-hint-sub"> — Do you feel heavy, foggy, or notice a coated tongue in the morning?</span>
          </label>
          <select name="ama_self_assessment" value={form.ama_self_assessment || ''} onChange={handleChange}>
            <option value="">Let AI assess from profile</option>
            <option value="high">Yes, noticeably — heavy, foggy, coated tongue</option>
            <option value="moderate">Sometimes — mild heaviness or sluggishness</option>
            <option value="low">No — feel light and clear in the mornings</option>
          </select>
        </div>

        <div className="pref-row">
          {/* ── Ingredient access ── */}
          <div className="pref-input-group">
            <label>Ingredient Access</label>
            <select name="ingredient_access" value={form.ingredient_access || ''} onChange={handleChange} required>
              <option value="kitchen_only">Kitchen Spices Only (Tier 1)</option>
              <option value="can_buy_herbs">Can Buy Herbs from Ayurvedic Store</option>
              <option value="full_access">Full Access incl. Guggulu & Bhasma (Tier 2)</option>
            </select>
          </div>
        </div>

        {/* Asked here and on the Panchakarma form; the server unions the two,
            so either answer reaches both herb-doubling checks. */}
        <div className="pref-input-group pref-full">
          <label>Ayurvedic Medicines You Take Now <span className="pref-hint">(optional, comma-separated)</span></label>
          <input
            type="text"
            name="current_ayurvedic_medicines"
            placeholder="e.g. Ashwagandha Churna, Triphala"
            value={form.current_ayurvedic_medicines || ''}
            onChange={handleChange}
          />
        </div>

        <div className="pref-row">
          {/* ── Previous medicines ── */}
          <div className="pref-input-group">
            <label>Previously Tried Ayurvedic Medicines <span className="pref-hint">(optional, comma-separated)</span></label>
            <input
              type="text"
              name="previous_ayurvedic_medicines"
              placeholder="e.g. Ashwagandha, Triphala, Chyawanprash"
              value={form.previous_ayurvedic_medicines || ''}
              onChange={handleChange}
            />
          </div>
        </div>
      </>
  );
}
