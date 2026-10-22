// The panchakarma preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the panchakarma schema.
import { GOALS } from './options';

import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'
export default function PanchakarmaFields({ form, handleChange }) {
  return (
      <>
        <div className="pref-input-group">
          <label htmlFor="pref-panchakarma_goal">{tr('ui.panchakarmaFields.detoxGoal', 'Detox Goal')}</label>
          <select id="pref-panchakarma_goal" name="panchakarma_goal" value={form.panchakarma_goal || ''} onChange={handleChange} required>
            <option value="">{tr('ui.panchakarmaFields.selectGoal', 'Select goal...')}</option>
            {GOALS.panchakarma.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-available_time_days">{tr('ui.panchakarmaFields.availableDays321', 'Available Days (3–21)')}</label>
            <input id="pref-available_time_days" type="number" name="available_time_days" min={3} max={21} value={form.available_time_days || ''} onChange={handleChange} required />
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-setting">{tr('ui.panchakarmaFields.setting', 'Setting')}</label>
            <select id="pref-setting" name="setting" value={form.setting || 'home'} onChange={handleChange} required>
              <option value="home">{tr('ui.panchakarmaFields.homeTherapiesShamana', 'Home Therapies (Shamana)')}</option>
              <option value="clinic">{tr('ui.panchakarmaFields.clinicalReferencePlanVaidyaAssisted', 'Clinical Reference Plan (Vaidya-Assisted)')}</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-detox_experience">{tr('ui.panchakarmaFields.priorPkExperience', 'Prior PK Experience')}</label>
            <select id="pref-detox_experience" name="detox_experience" value={form.detox_experience || 'none'} onChange={handleChange} required>
              <option value="none">{tr('ui.panchakarmaFields.firstTime', 'First time')}</option>
              <option value="some">{tr('ui.panchakarmaFields.done12Courses', 'Done 1–2 courses')}</option>
              <option value="experienced">{tr('ui.panchakarmaFields.experienced3Courses', 'Experienced (3+ courses)')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-koshtha">{tr('ui.panchakarmaFields.koshthaBowelTendency', 'Koshtha (Bowel Tendency)')}</label>
            <select id="pref-koshtha" name="koshtha" value={form.koshtha || ''} onChange={handleChange} required>
              <option value="">{tr('ui.panchakarmaFields.select', 'Select...')}</option>
              <option value="sama">{tr('ui.panchakarmaFields.samaRegularOnceDaily', 'Sama — Regular (once daily)')}</option>
              <option value="krura">{tr('ui.panchakarmaFields.kruraHardInfrequentConstipated', 'Krura — Hard / infrequent (constipated)')}</option>
              <option value="mridu">{tr('ui.panchakarmaFields.mriduLooseFrequent', 'Mridu — Loose / frequent')}</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-self_care_time_per_day">{tr('ui.panchakarmaFields.dailySelfCareTime', 'Daily Self-Care Time')}</label>
            <select id="pref-self_care_time_per_day" name="self_care_time_per_day" value={form.self_care_time_per_day || '30 min'} onChange={handleChange} required>
              <option value="15 min">{tr('ui.panchakarmaFields.n15Min', '15 min')}</option>
              <option value="30 min">{tr('ui.panchakarmaFields.n30Min', '30 min')}</option>
              <option value="1 hour">{tr('ui.panchakarmaFields.n1Hour', '1 hour')}</option>
              <option value="2+ hours">{tr('ui.panchakarmaFields.n2Hours', '2+ hours')}</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-access_to_ayurvedic_herbs">{tr('ui.panchakarmaFields.herbAccess', 'Herb Access')}</label>
            <select id="pref-access_to_ayurvedic_herbs" name="access_to_ayurvedic_herbs" value={form.access_to_ayurvedic_herbs || 'willing_to_buy'} onChange={handleChange} required>
              <option value="willing_to_buy">{tr('ui.panchakarmaFields.willingToBuy', 'Willing to Buy')}</option>
              <option value="yes">{tr('ui.panchakarmaFields.iHaveAccess', 'I have access')}</option>
              <option value="no">{tr('ui.panchakarmaFields.kitchenSpicesOnly', 'Kitchen spices only')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-diet_adherence_ability">{tr('ui.panchakarmaFields.dietAdherence', 'Diet Adherence')}</label>
            <select id="pref-diet_adherence_ability" name="diet_adherence_ability" value={form.diet_adherence_ability || 'partial'} onChange={handleChange} required>
              <option value="partial">{tr('ui.panchakarmaFields.partial', 'Partial')}</option>
              <option value="strict">{tr('ui.panchakarmaFields.strictKitchariOnly', 'Strict (Kitchari Only)')}</option>
              <option value="lifestyle_only">{tr('ui.panchakarmaFields.lifestyleOnly', 'Lifestyle Only')}</option>
            </select>
          </div>
        </div>
        {/* Also asked on the remedies form; the server unions the two, so either
            answer reaches both herb-doubling checks. It once sat only on the
            remedies form, whose schema did not declare it, and every answer was
            dropped on save. */}
        <div className="pref-input-group pref-full">
          <label htmlFor="pref-current_ayurvedic_medicines"><Trans i18nKey="ui.panchakarmaFields.ayurvedicMedicinesYouTakeNow" defaults={"Ayurvedic Medicines You Take Now <0>(optional, comma-separated)</0>"} components={[<span className="pref-hint" />]} /></label>
          <input id="pref-current_ayurvedic_medicines"
            type="text"
            name="current_ayurvedic_medicines"
            placeholder={tr('ui.panchakarmaFields.eGAshwagandhaChurnaBrahmi', 'e.g. Ashwagandha Churna, Brahmi Ghrita')}
            value={form.current_ayurvedic_medicines || ''}
            onChange={handleChange}
          />
        </div>
      </>
  );
}
