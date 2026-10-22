// The gym preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the gym schema.
import { GOALS, EQUIPMENT, KNOWN_LIFTS } from './options';

import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'
export default function GymFields({ form, setForm, handleChange, renderInjuryChips }) {
  return (
      <>
        <div className="pref-input-group">
          <label htmlFor="pref-gym_goal">{tr('ui.gymFields.primaryGoal', 'Primary Goal')}</label>
          <select id="pref-gym_goal" name="gym_goal" value={form.gym_goal || ''} onChange={handleChange} required>
            <option value="">{tr('ui.gymFields.selectYourGoal', 'Select your goal...')}</option>
            {GOALS.gym.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-workout_days_per_week">{tr('ui.gymFields.daysPerWeek27', 'Days per Week (2-7)')}</label>
            <input id="pref-workout_days_per_week" type="number" name="workout_days_per_week" min={2} max={7} value={form.workout_days_per_week || ''} onChange={handleChange} required />
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-workout_duration_minutes">{tr('ui.gymFields.sessionDurationMins', 'Session Duration (mins)')}</label>
            <input id="pref-workout_duration_minutes" type="number" name="workout_duration_minutes" min={20} max={90} value={form.workout_duration_minutes || ''} onChange={handleChange} required />
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-training_style">{tr('ui.gymFields.trainingStyle', 'Training Style')}</label>
            <select id="pref-training_style" name="training_style" value={form.training_style ?? ''} onChange={handleChange}>
              <option value="">{tr('ui.gymFields.balancedFollowMyGoal', 'Balanced — follow my goal')}</option>
              <option value="strength">{tr('ui.gymFields.strength', 'Strength')}</option>
              <option value="hypertrophy">{tr('ui.gymFields.hypertrophyMuscleSize', 'Hypertrophy (Muscle Size)')}</option>
              <option value="endurance">{tr('ui.gymFields.endurance', 'Endurance')}</option>
              <option value="circuit">{tr('ui.gymFields.circuitTraining', 'Circuit Training')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-cardio_preference">{tr('ui.gymFields.cardio', 'Cardio')}</label>
            <select id="pref-cardio_preference" name="cardio_preference" value={form.cardio_preference || 'none'} onChange={handleChange} required>
              <option value="none">{tr('ui.gymFields.none', 'None')}</option>
              <option value="light">{tr('ui.gymFields.light', 'Light')}</option>
              <option value="moderate">{tr('ui.gymFields.moderate', 'Moderate')}</option>
              <option value="heavy">{tr('ui.gymFields.heavy', 'Heavy')}</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-target_muscle_focus">{tr('ui.gymFields.muscleFocus', 'Muscle Focus')}</label>
            <select id="pref-target_muscle_focus" name="target_muscle_focus" value={form.target_muscle_focus || 'full_body'} onChange={handleChange} required>
              <option value="full_body">{tr('ui.gymFields.fullBody', 'Full Body')}</option>
              <option value="upper">{tr('ui.gymFields.upperBody', 'Upper Body')}</option>
              <option value="lower">{tr('ui.gymFields.lowerBody', 'Lower Body')}</option>
              <option value="core">{tr('ui.gymFields.core', 'Core')}</option>
              <option value="back">{tr('ui.gymFields.back', 'Back')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-strength_level">{tr('ui.gymFields.liftingStrengthLevel', 'Lifting Strength Level')}</label>
            <select id="pref-strength_level" name="strength_level" value={form.strength_level || 'beginner'} onChange={handleChange}>
              <option value="untrained">{tr('ui.gymFields.untrainedNeverLiftedWeights', 'Untrained — never lifted weights')}</option>
              <option value="beginner">{tr('ui.gymFields.beginnerUnder1YearLifting', 'Beginner — under 1 year lifting')}</option>
              <option value="intermediate">{tr('ui.gymFields.intermediate13YearsConsistent', 'Intermediate — 1–3 years, consistent')}</option>
              <option value="advanced">{tr('ui.gymFields.advanced3YearsNearMax', 'Advanced — 3+ years, near max lifts')}</option>
            </select>
          </div>
        </div>
        <div className="pref-input-group">
          <label>{tr('ui.gymFields.equipmentYouCanTrainWith', 'Equipment you can train with')}</label>
          <div className="pref-chip-row">
            {EQUIPMENT.map(eq => {
              const chosen = (form.available_equipment || []).includes(eq.value)
              return (
                <button
                  key={eq.value}
                  type="button"
                  aria-pressed={chosen}
                  className={`pref-chip${chosen ? ' active' : ''}`}
                  onClick={() => setForm(p => {
                    const current = p.available_equipment || []
                    return {
                      ...p,
                      available_equipment: chosen
                        ? current.filter(v => v !== eq.value)
                        : [...current, eq.value],
                    }
                  })}
                >
                  {eq.label}
                </button>
              )
            })}
          </div>
          <p className="pref-hint">
            {tr('ui.gymFields.bodyweightMovementsAreAlwaysIncluded', 'Bodyweight movements are always included. Tick nothing and the plan is built from them alone.')}
          </p>
        </div>
        <div className="pref-input-group">
          <label htmlFor="pref-injury_detail"><Trans i18nKey="ui.gymFields.injuriesOrJointProblems0" defaults={"Injuries or joint problems <0>optional</0>"} components={[<span className="pref-hint-sub" />]} /></label>
          {renderInjuryChips()}
          <input id="pref-injury_detail"
            type="text"
            name="injury_detail"
            maxLength={300}
            placeholder={tr('ui.gymFields.anythingElseEGOld', 'Anything else? e.g. old ACL tear, tennis elbow')}
            value={form.injury_detail || ''}
            onChange={handleChange}
          />
          <p className="pref-hint">
            {tr('ui.gymFields.exercisesThatLoadAnInjured', 'Exercises that load an injured area are left out. If we cannot match what you type, the plan says so rather than guessing. Your yoga plan reads these too.')}
          </p>
        </div>
        <details className="pref-input-group pref-known-lifts" open={!!form.known_lifts && Object.keys(form.known_lifts).length > 0}>
          <summary><Trans i18nKey="ui.gymFields.knowYourWorkingWeights0" defaults={"Know your working weights? <0>optional — makes every load fit you</0>"} components={[<span className="pref-hint-sub" />]} /></summary>
          <p className="pref-hint">
            {tr('ui.gymFields.aWeightYouCanLift', 'A weight you can lift for that many reps with good form. Leave any you do not know blank. For dumbbells, enter the weight of one dumbbell.')}
          </p>
          {KNOWN_LIFTS.map(lift => {
            const v = (form.known_lifts || {})[lift.value] || {}
            const set = (field, value) => setForm(p => ({
              ...p,
              known_lifts: {
                ...(p.known_lifts || {}),
                [lift.value]: { ...((p.known_lifts || {})[lift.value] || {}), [field]: value },
              },
            }))
            return (
              <div key={lift.value} className="pref-known-row">
                <span className="pref-known-label">{lift.label}</span>
                <input type="number" inputMode="decimal" min="1" max="400" step="0.5"
                  aria-label={`${lift.label} kg`} placeholder="kg"
                  value={v.kg ?? ''} onChange={e => set('kg', e.target.value)} />
                <span className="pref-known-x" aria-hidden="true">×</span>
                <input type="number" inputMode="numeric" min="1" max="20" step="1"
                  aria-label={`${lift.label} reps`} placeholder="reps"
                  value={v.reps ?? ''} onChange={e => set('reps', e.target.value)} />
              </div>
            )
          })}
        </details>
        {/* `exercise_preferences` has been in the schema since the beginning and
            had nowhere to be typed. A term matches on name, movement pattern,
            lift class or equipment, so "deadlift" takes out the hinge family and
            "barbell" takes out an implement — loose on purpose, because someone
            typing a dislike is describing a category, not picking rows. */}
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-dislikes"><Trans i18nKey="ui.gymFields.movementsToAvoid0Optional" defaults={"Movements to avoid <0>optional</0>"} components={[<span className="pref-hint-sub" />]} /></label>
            <input id="pref-dislikes"
              type="text"
              name="dislikes"
              placeholder={tr('ui.gymFields.burpeesDeadliftJumpRope', 'burpees, deadlift, jump rope')}
              value={form.dislikes || ''}
              onChange={handleChange}
            />
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-likes"><Trans i18nKey="ui.gymFields.movementsYouEnjoy0Optional" defaults={"Movements you enjoy <0>optional</0>"} components={[<span className="pref-hint-sub" />]} /></label>
            <input id="pref-likes"
              type="text"
              name="likes"
              placeholder={tr('ui.gymFields.pullUpsKettlebellRowing', 'pull-ups, kettlebell, rowing')}
              value={form.likes || ''}
              onChange={handleChange}
            />
          </div>
        </div>
        <p className="pref-hint">
          {tr('ui.gymFields.commaSeparatedADislikeIs', 'Comma separated. A dislike is a preference, not a restriction — if leaving something out would leave a muscle group with too little to train it, the plan keeps a few and tells you which.')}
        </p>
      </>
  );
}
