// The gym preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the gym schema.
import { GOALS, EQUIPMENT, KNOWN_LIFTS } from './options';

export default function GymFields({ form, setForm, handleChange, renderInjuryChips }) {
  return (
      <>
        <div className="pref-input-group">
          <label>Primary Goal</label>
          <select name="gym_goal" value={form.gym_goal || ''} onChange={handleChange} required>
            <option value="">Select your goal...</option>
            {GOALS.gym.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Days per Week (2-7)</label>
            <input type="number" name="workout_days_per_week" min={2} max={7} value={form.workout_days_per_week || ''} onChange={handleChange} required />
          </div>
          <div className="pref-input-group">
            <label>Session Duration (mins)</label>
            <input type="number" name="workout_duration_minutes" min={20} max={90} value={form.workout_duration_minutes || ''} onChange={handleChange} required />
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Training Style</label>
            <select name="training_style" value={form.training_style ?? ''} onChange={handleChange}>
              <option value="">Balanced — follow my goal</option>
              <option value="strength">Strength</option>
              <option value="hypertrophy">Hypertrophy (Muscle Size)</option>
              <option value="endurance">Endurance</option>
              <option value="circuit">Circuit Training</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Cardio</label>
            <select name="cardio_preference" value={form.cardio_preference || ''} onChange={handleChange} required>
              <option value="none">None</option>
              <option value="light">Light</option>
              <option value="moderate">Moderate</option>
              <option value="heavy">Heavy</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Muscle Focus</label>
            <select name="target_muscle_focus" value={form.target_muscle_focus || ''} onChange={handleChange} required>
              <option value="full_body">Full Body</option>
              <option value="upper">Upper Body</option>
              <option value="lower">Lower Body</option>
              <option value="core">Core</option>
              <option value="back">Back</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Lifting Strength Level</label>
            <select name="strength_level" value={form.strength_level || 'beginner'} onChange={handleChange}>
              <option value="untrained">Untrained — never lifted weights</option>
              <option value="beginner">Beginner — under 1 year lifting</option>
              <option value="intermediate">Intermediate — 1–3 years, consistent</option>
              <option value="advanced">Advanced — 3+ years, near max lifts</option>
            </select>
          </div>
        </div>
        <div className="pref-input-group">
          <label>Equipment you can train with</label>
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
            Bodyweight movements are always included. Tick nothing and the plan is
            built from them alone.
          </p>
        </div>
        <div className="pref-input-group">
          <label>Injuries or joint problems <span className="pref-hint-sub">optional</span></label>
          {renderInjuryChips()}
          <input
            type="text"
            name="injury_detail"
            maxLength={300}
            placeholder="Anything else? e.g. old ACL tear, tennis elbow"
            value={form.injury_detail || ''}
            onChange={handleChange}
          />
          <p className="pref-hint">
            Exercises that load an injured area are left out. If we cannot match
            what you type, the plan says so rather than guessing. Your yoga plan
            reads these too.
          </p>
        </div>
        <details className="pref-input-group pref-known-lifts" open={!!form.known_lifts && Object.keys(form.known_lifts).length > 0}>
          <summary>
            Know your working weights? <span className="pref-hint-sub">optional — makes every load fit you</span>
          </summary>
          <p className="pref-hint">
            A weight you can lift for that many reps with good form. Leave any you
            do not know blank. For dumbbells, enter the weight of one dumbbell.
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
            <label>Movements to avoid <span className="pref-hint-sub">optional</span></label>
            <input
              type="text"
              name="dislikes"
              placeholder="burpees, deadlift, jump rope"
              value={form.dislikes || ''}
              onChange={handleChange}
            />
          </div>
          <div className="pref-input-group">
            <label>Movements you enjoy <span className="pref-hint-sub">optional</span></label>
            <input
              type="text"
              name="likes"
              placeholder="pull-ups, kettlebell, rowing"
              value={form.likes || ''}
              onChange={handleChange}
            />
          </div>
        </div>
        <p className="pref-hint">
          Comma separated. A dislike is a preference, not a restriction — if leaving
          something out would leave a muscle group with too little to train it, the
          plan keeps a few and tells you which.
        </p>
      </>
  );
}
