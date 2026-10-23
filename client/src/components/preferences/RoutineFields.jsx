import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'

// The routine preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the routine schema.

export default function RoutineFields({ form, setForm, handleChange }) {
  return (
      <>
        <p className="pref-notice">
          {tr('ui.routineFields.yourDailyRoutineIsPersonalised', 'Your daily routine is personalised from your Dosha, season, conditions, and the preferences below. Gym and Yoga integration pulls your existing plan schedules automatically.')}
        </p>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-wake_preference">{tr('ui.routineFields.wakePreference', 'Wake Preference')}</label>
            <select id="pref-wake_preference" name="wake_preference" value={form.wake_preference || 'natural'} onChange={handleChange} required>
              <option value="early">{tr('ui.routineFields.early430530', 'Early — 4:30–5:30 AM')}</option>
              <option value="natural">{tr('ui.routineFields.naturalTheHourYourDosha', 'Natural — the hour your Dosha and season suggest')}</option>
              <option value="late">{tr('ui.routineFields.late630730', 'Late — 6:30–7:30 AM')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-occupation_type">{tr('ui.routineFields.occupationType', 'Occupation Type')}</label>
            <select id="pref-occupation_type" name="occupation_type" value={form.occupation_type || 'moderately_active'} onChange={handleChange} required>
              <option value="sedentary">{tr('ui.routineFields.sedentaryMostlyDeskDriving', 'Sedentary — mostly desk / driving')}</option>
              <option value="moderately_active">{tr('ui.routineFields.moderatelyActiveMixed', 'Moderately Active — mixed')}</option>
              <option value="very_active">{tr('ui.routineFields.veryActiveLabourAthlete', 'Very Active — labour / athlete')}</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-agni_type_self_report"><Trans i18nKey="ui.routineFields.agniDigestiveFireType0" defaults={"Agni (Digestive Fire) Type <0>— how would you describe your digestion?</0>"} components={[<span className="pref-hint-sub" />]} /></label>
            <select id="pref-agni_type_self_report" name="agni_type_self_report" value={form.agni_type_self_report || 'assessed'} onChange={handleChange} required>
              <option value="assessed">{tr('ui.routineFields.useMyAssessment', 'Use my assessment')}</option>
              <option value="sama">{tr('ui.routineFields.samaBalancedRegularDigestion', 'Sama — Balanced, regular digestion')}</option>
              <option value="manda">{tr('ui.routineFields.mandaSlowHeavyBloatedAfter', 'Manda — Slow, heavy, bloated after meals')}</option>
              <option value="tikshna">{tr('ui.routineFields.tikshnaSharpHungryQuicklyAcidity', 'Tikshna — Sharp, hungry quickly, acidity')}</option>
              <option value="vishama">{tr('ui.routineFields.vishamaIrregularSomeDaysStrong', 'Vishama — Irregular, some days strong, some weak')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-intermittent_fasting">{tr('ui.routineFields.intermittentFastingWindow', 'Intermittent Fasting Window')}</label>
            <select id="pref-intermittent_fasting" name="intermittent_fasting" value={form.intermittent_fasting || 'no'} onChange={handleChange}>
              <option value="no">{tr('ui.routineFields.noFasting', 'No Fasting')}</option>
              <option value="12:12">{tr('ui.routineFields.n1212Balanced', '12:12 — Balanced')}</option>
              <option value="14:10">{tr('ui.routineFields.n1410Moderate', '14:10 — Moderate')}</option>
              <option value="16:8">{tr('ui.routineFields.n168Advanced', '16:8 — Advanced')}</option>
            </select>
          </div>
        </div>
        <div className="pref-input-group pref-full">
          <label htmlFor="pref-fasting_days"><Trans i18nKey="ui.routineFields.fastingDays0OptionalComma" defaults={"Fasting Days <0>(optional, comma-separated)</0>"} components={[<span className="pref-hint" />]} /></label>
          <input id="pref-fasting_days"
            type="text"
            name="fasting_days"
            placeholder={tr('ui.routineFields.eGMondayEkadashi', 'e.g. Monday, Ekadashi')}
            value={form.fasting_days || ''}
            onChange={handleChange}
          />
        </div>
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint"><Trans i18nKey="ui.routineFields.yourGymAndYogaPlans" defaults={"Your gym and yoga plans <0>(their sessions are placed in your day — tap one to leave it out)</0>"} components={[<span />]} /></label>
          <div className="pref-chip-row">
            <button
              type="button"
              className={`pref-chip${!form.exclude_gym_plan ? ' active' : ''}`}
              aria-pressed={!form.exclude_gym_plan}
              onClick={() => setForm(p => ({ ...p, exclude_gym_plan: !p.exclude_gym_plan }))}
            >
              {tr('ui.routineFields.includeGymPlan', 'Include Gym Plan')}
            </button>
            <button
              type="button"
              className={`pref-chip${!form.exclude_yoga_plan ? ' active' : ''}`}
              aria-pressed={!form.exclude_yoga_plan}
              onClick={() => setForm(p => ({ ...p, exclude_yoga_plan: !p.exclude_yoga_plan }))}
            >
              {tr('ui.routineFields.includeYogaPlan', 'Include Yoga Plan')}
            </button>
          </div>
        </div>
        {!form.exclude_gym_plan && (
          <div className="pref-input-group">
            <label htmlFor="pref-gym_time_of_day">{tr('ui.routineFields.gymTime', 'Gym Time')}</label>
            <select id="pref-gym_time_of_day" name="gym_time_of_day" value={form.gym_time_of_day || 'morning'} onChange={handleChange}>
              <option value="morning">{tr('ui.routineFields.morning', 'Morning')}</option>
              <option value="evening">{tr('ui.routineFields.eveningBeforeDinner', 'Evening (before dinner)')}</option>
            </select>
            <p className="pref-hint">{tr('ui.routineFields.yogaGoesAtTheTime', 'Yoga goes at the time you chose on the yoga form.')}</p>
          </div>
        )}
      </>
  );
}
