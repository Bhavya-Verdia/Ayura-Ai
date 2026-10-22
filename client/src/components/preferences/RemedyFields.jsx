import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'

// The remedies and medicines preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the remedies schema.

export default function RemedyFields({ form, handleChange, handleToggle }) {
  return (
      <>
        <p className="pref-notice">
          {tr('ui.remedyFields.recommendationsAreMatchedToYour', 'Recommendations are matched to your Vikriti (imbalance state), Agni, and conditions. Always consult a qualified Vaidya before starting Tier-2 formulations.')}
        </p>

        {/* ── Allopathic medications ── */}
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint"><Trans i18nKey="ui.remedyFields.currentAllopathicMedications0Select" defaults={"Current Allopathic Medications <0>(select all that apply — used for drug interaction safety)</0>"} components={[<span />]} /></label>
          <div className="pref-chip-row">
            {[
              { value: 'blood_thinners',      label: tr('ui.remedyFields.bloodThinnersAnticoagulants', 'Blood Thinners / Anticoagulants') },
              { value: 'diabetes_medication',  label: tr('ui.remedyFields.diabetesMedication', 'Diabetes Medication') },
              { value: 'thyroid_medication',   label: tr('ui.remedyFields.thyroidMedication', 'Thyroid Medication') },
              { value: 'antihypertensives',    label: tr('ui.remedyFields.bloodPressureMedication', 'Blood Pressure Medication') },
              { value: 'immunosuppressants',   label: tr('ui.remedyFields.immunosuppressantsSteroids', 'Immunosuppressants / Steroids') },
              { value: 'sedatives',            label: tr('ui.remedyFields.sedativesSleepMedication', 'Sedatives / Sleep Medication') },
              { value: 'antiepileptics',       label: tr('ui.remedyFields.antiEpileptics', 'Anti-Epileptics') },
              { value: 'antidepressants',      label: tr('ui.remedyFields.antidepressantsAntipsychotics', 'Antidepressants / Antipsychotics') },
              { value: 'cardiac_glycosides',   label: tr('ui.remedyFields.cardiacGlycosidesDigoxin', 'Cardiac Glycosides (Digoxin)') },
              { value: 'nsaids',               label: tr('ui.remedyFields.nsaidsPainRelievers', 'NSAIDs / Pain Relievers') },
              { value: 'hormone_therapy',      label: tr('ui.remedyFields.hormoneTherapyOcp', 'Hormone Therapy / OCP') },
              { value: 'antibiotics',          label: tr('ui.remedyFields.antibioticsCurrentCourse', 'Antibiotics (current course)') },
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
          <label htmlFor="pref-ama_self_assessment"><Trans i18nKey="ui.remedyFields.amaToxicLoadSelfAssessment" defaults={"Ama (Toxic Load) Self-Assessment <0>— Do you feel heavy, foggy, or notice a coated tongue in the morning?</0>"} components={[<span className="pref-hint-sub" />]} /></label>
          <select id="pref-ama_self_assessment" name="ama_self_assessment" value={form.ama_self_assessment || ''} onChange={handleChange}>
            <option value="">{tr('ui.remedyFields.letAiAssessFromProfile', 'Let AI assess from profile')}</option>
            <option value="high">{tr('ui.remedyFields.yesNoticeablyHeavyFoggyCoated', 'Yes, noticeably — heavy, foggy, coated tongue')}</option>
            <option value="moderate">{tr('ui.remedyFields.sometimesMildHeavinessOrSluggishness', 'Sometimes — mild heaviness or sluggishness')}</option>
            <option value="low">{tr('ui.remedyFields.noFeelLightAndClear', 'No — feel light and clear in the mornings')}</option>
          </select>
        </div>

        <div className="pref-row">
          {/* ── Ingredient access ── */}
          <div className="pref-input-group">
            <label htmlFor="pref-ingredient_access">{tr('ui.remedyFields.ingredientAccess', 'Ingredient Access')}</label>
            <select id="pref-ingredient_access" name="ingredient_access" value={form.ingredient_access || 'kitchen_only'} onChange={handleChange} required>
              <option value="kitchen_only">{tr('ui.remedyFields.kitchenSpicesOnlyTier1', 'Kitchen Spices Only (Tier 1)')}</option>
              <option value="can_buy_herbs">{tr('ui.remedyFields.canBuyHerbsFromAyurvedic', 'Can Buy Herbs from Ayurvedic Store')}</option>
              <option value="full_access">{tr('ui.remedyFields.fullAccessInclGugguluBhasma', 'Full Access incl. Guggulu & Bhasma (Tier 2)')}</option>
            </select>
          </div>
        </div>

        {/* Asked here and on the Panchakarma form; the server unions the two,
            so either answer reaches both herb-doubling checks. */}
        <div className="pref-input-group pref-full">
          <label htmlFor="pref-current_ayurvedic_medicines"><Trans i18nKey="ui.remedyFields.ayurvedicMedicinesYouTakeNow" defaults={"Ayurvedic Medicines You Take Now <0>(optional, comma-separated)</0>"} components={[<span className="pref-hint" />]} /></label>
          <input id="pref-current_ayurvedic_medicines"
            type="text"
            name="current_ayurvedic_medicines"
            placeholder={tr('ui.remedyFields.eGAshwagandhaChurnaTriphala', 'e.g. Ashwagandha Churna, Triphala')}
            value={form.current_ayurvedic_medicines || ''}
            onChange={handleChange}
          />
        </div>

        <div className="pref-row">
          {/* ── Previous medicines ── */}
          <div className="pref-input-group">
            <label htmlFor="pref-previous_ayurvedic_medicines"><Trans i18nKey="ui.remedyFields.previouslyTriedAyurvedicMedicines0" defaults={"Previously Tried Ayurvedic Medicines <0>(optional, comma-separated)</0>"} components={[<span className="pref-hint" />]} /></label>
            <input id="pref-previous_ayurvedic_medicines"
              type="text"
              name="previous_ayurvedic_medicines"
              placeholder={tr('ui.remedyFields.eGAshwagandhaTriphalaChyawanprash', 'e.g. Ashwagandha, Triphala, Chyawanprash')}
              value={form.previous_ayurvedic_medicines || ''}
              onChange={handleChange}
            />
          </div>
        </div>
      </>
  );
}
