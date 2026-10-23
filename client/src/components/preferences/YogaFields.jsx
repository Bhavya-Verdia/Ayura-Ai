// The yoga preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the yoga schema.
import { GOALS, YOGA_SESSION_MINUTES, YOGA_PRANAYAMA_MINUTES, YOGA_SUGGESTED_MINUTES } from './options';

import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'
export default function YogaFields({ form, handleChange, renderInjuryChips }) {
  return (
      <>
        <div className="pref-input-group">
          <label htmlFor="pref-yoga_goal">{tr('ui.yogaFields.primaryFocus', 'Primary Focus')}</label>
          <select id="pref-yoga_goal" name="yoga_goal" value={form.yoga_goal || ''} onChange={handleChange} required>
            <option value="">{tr('ui.yogaFields.selectYourFocus', 'Select your focus...')}</option>
            {GOALS.yoga.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-yoga_experience">{tr('ui.yogaFields.experienceLevel', 'Experience Level')}</label>
            <select id="pref-yoga_experience" name="yoga_experience" value={form.yoga_experience || 'beginner'} onChange={handleChange} required>
              <option value="none">{tr('ui.yogaFields.noneNeverPracticed', 'None — never practiced')}</option>
              <option value="beginner">{tr('ui.yogaFields.beginnerUnder1Year', 'Beginner — under 1 year')}</option>
              <option value="intermediate">{tr('ui.yogaFields.intermediate13Years', 'Intermediate — 1–3 years')}</option>
              <option value="advanced">{tr('ui.yogaFields.advanced3Years', 'Advanced — 3+ years')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-flexibility_level">{tr('ui.yogaFields.currentFlexibility', 'Current Flexibility')}</label>
            <select id="pref-flexibility_level" name="flexibility_level" value={form.flexibility_level || 'moderate'} onChange={handleChange} required>
              <option value="low">{tr('ui.yogaFields.lowLimitedRange', 'Low — limited range')}</option>
              <option value="moderate">{tr('ui.yogaFields.moderateAverageFlexibility', 'Moderate — average flexibility')}</option>
              <option value="high">{tr('ui.yogaFields.highVeryFlexible', 'High — very flexible')}</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-yoga_style_preference">{tr('ui.yogaFields.yogaStyle', 'Yoga Style')}</label>
            <select id="pref-yoga_style_preference" name="yoga_style_preference" value={form.yoga_style_preference || 'hatha'} onChange={handleChange} required>
              <option value="hatha">{tr('ui.yogaFields.hathaSlowFoundational', 'Hatha — slow, foundational')}</option>
              <option value="vinyasa">{tr('ui.yogaFields.vinyasaFlowingDynamic', 'Vinyasa — flowing, dynamic')}</option>
              <option value="restorative">{tr('ui.yogaFields.restorativePassiveHealing', 'Restorative — passive, healing')}</option>
              <option value="yin">{tr('ui.yogaFields.yinLongHoldsDeepTissue', 'Yin — long holds, deep tissue')}</option>
              <option value="power">{tr('ui.yogaFields.powerStrengthFocused', 'Power — strength-focused')}</option>
              <option value="ashtanga">{tr('ui.yogaFields.ashtangaStructuredSeries', 'Ashtanga — structured series')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-time_available_minutes"><Trans i18nKey="ui.yogaFields.sessionDuration0TheSame" defaults={"Session Duration <0>— the same every day; the plan varies the effort, not the time</0>"} components={[<span className="pref-hint-sub" />]} /></label>
            <select id="pref-time_available_minutes" name="time_available_minutes" value={form.time_available_minutes || YOGA_SUGGESTED_MINUTES[form.yoga_experience || 'beginner'] || 30} onChange={handleChange} required>
              {YOGA_SESSION_MINUTES.map(m => (
                <option key={m} value={m}><Trans i18nKey="ui.yogaFields.minIncludesMinPranayama" defaults={"{{m}} min — includes {{value}} min pranayama"} values={{ m, value: YOGA_PRANAYAMA_MINUTES[form.yoga_experience || 'beginner'] }} /></option>
              ))}
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-time_of_day_preference">{tr('ui.yogaFields.timeOfDay', 'Time of Day')}</label>
            <select id="pref-time_of_day_preference" name="time_of_day_preference" value={form.time_of_day_preference || 'morning'} onChange={handleChange} required>
              <option value="morning">{tr('ui.yogaFields.morning', 'Morning')}</option>
              <option value="evening">{tr('ui.yogaFields.evening', 'Evening')}</option>
              <option value="both">{tr('ui.yogaFields.both', 'Both')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-pranayama_interest">{tr('ui.yogaFields.includePranayama', 'Include Pranayama?')}</label>
            <select id="pref-pranayama_interest" name="pranayama_interest" value={form.pranayama_interest || 'yes'} onChange={handleChange} required>
              <option value="yes">{tr('ui.yogaFields.yes', 'Yes')}</option>
              <option value="no">{tr('ui.yogaFields.no', 'No')}</option>
              <option value="already_practice">{tr('ui.yogaFields.alreadyPractice', 'Already Practice')}</option>
            </select>
          </div>
        </div>
        <div className="pref-input-group">
          <label htmlFor="pref-indoor_outdoor">{tr('ui.yogaFields.location', 'Location')}</label>
          <select id="pref-indoor_outdoor" name="indoor_outdoor" value={form.indoor_outdoor || 'indoor'} onChange={handleChange} required>
            <option value="indoor">{tr('ui.yogaFields.indoor', 'Indoor')}</option>
            <option value="outdoor">{tr('ui.yogaFields.outdoor', 'Outdoor')}</option>
            <option value="both">{tr('ui.yogaFields.both', 'Both')}</option>
          </select>
        </div>
        <div className="pref-input-group">
          <label htmlFor="pref-physical_limitations_detail"><Trans i18nKey="ui.yogaFields.injuriesOrPhysicalLimitations0" defaults={"Injuries or physical limitations <0>optional</0>"} components={[<span className="pref-hint-sub" />]} /></label>
          {renderInjuryChips()}
          <input id="pref-physical_limitations_detail" type="text" name="physical_limitations_detail" maxLength={300}
            placeholder={tr('ui.yogaFields.anythingElseEGCan', 'Anything else? e.g. can\'t kneel')}
            value={form.physical_limitations_detail || ''} onChange={handleChange} />
          <p className="pref-hint">
            {tr('ui.yogaFields.posesThatLoadAnInjured', 'Poses that load an injured area are left out, and anything we cannot match is named in the plan. Your gym plan reads these too.')}
          </p>
        </div>
      </>
  );
}
