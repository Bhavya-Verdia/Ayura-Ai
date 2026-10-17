// The diet preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the diet schema.
import { GOALS, DIETARY_TYPES } from './options';

export default function DietFields({ form, handleChange, handleToggle }) {
  return (
      <>
        <div className="pref-input-group">
          <label>Primary Goal</label>
          <select name="diet_goal" value={form.diet_goal || ''} onChange={handleChange} required>
            <option value="">Select your goal...</option>
            {GOALS.diet.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-input-group">
          <label>Dietary Type</label>
          <select name="dietary_type" value={form.dietary_type || ''} onChange={handleChange} required>
            <option value="">Select your diet...</option>
            {DIETARY_TYPES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
          <p className="pref-hint">
            Ayura&apos;s food library is a vegetarian Nighantu — every food in it is
            screened against your conditions by name. We would rather offer two
            diets we can screen than five we cannot.
          </p>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Intermittent Fasting</label>
            <select name="intermittent_fasting" value={form.intermittent_fasting || ''} onChange={handleChange} required>
              <option value="no">No Fasting</option>
              <option value="12:12">12:12 (Balanced)</option>
              <option value="14:10">14:10 (Moderate)</option>
              <option value="16:8">16:8 (Advanced)</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Daily Water Intake</label>
            <select name="water_intake" value={form.water_intake || ''} onChange={handleChange} required>
              <option value="< 1L">&lt; 1L</option>
              <option value="1-2L">1-2L</option>
              <option value="2-3L">2-3L</option>
              <option value="> 3L">&gt; 3L</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Gut Health</label>
            <select name="gut_health_issue" value={form.gut_health_issue || ''} onChange={handleChange} required>
              <option value="healthy">Healthy</option>
              <option value="acidity">Acidity / Heartburn</option>
              <option value="constipation">Constipation</option>
              <option value="bloating">Bloating</option>
              <option value="ibs">IBS</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Fasting Days (Optional)</label>
            <input type="text" name="fasting_days" placeholder="e.g. Monday, Ekadashi" value={form.fasting_days || ''} onChange={handleChange} />
          </div>
        </div>
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint">Food Allergies <span>(select all that apply)</span></label>
          <div className="pref-chip-row">
            {[
              { value: 'gluten', label: 'Gluten / Wheat' },
              { value: 'dairy', label: 'Dairy' },
              { value: 'nuts_tree', label: 'Tree Nuts' },
              { value: 'peanuts', label: 'Peanuts' },
              { value: 'soy', label: 'Soy' },
              { value: 'eggs', label: 'Eggs' },
              { value: 'shellfish', label: 'Shellfish' },
              { value: 'fish', label: 'Fish' },
              { value: 'sesame', label: 'Sesame / Til' },
              { value: 'mustard', label: 'Mustard / Rai' },
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                className={`pref-chip${(form.food_allergies || []).includes(opt.value) ? ' active' : ''}`}
                onClick={() => handleToggle('food_allergies', opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint">Food Intolerances <span>(select all that apply)</span></label>
          <div className="pref-chip-row">
            {[
              { value: 'lactose', label: 'Lactose' },
              { value: 'fructose', label: 'Fructose' },
              { value: 'gluten_sensitivity', label: 'Gluten Sensitivity' },
              { value: 'histamine', label: 'Histamine' },
              { value: 'fodmap', label: 'FODMAPs' },
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                className={`pref-chip${(form.food_intolerances || []).includes(opt.value) ? ' active' : ''}`}
                onClick={() => handleToggle('food_intolerances', opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        {/* What makes it a plan the person will actually eat. A dietitian asks all
            three before writing a meal; the form asked none of them. */}
        <div className="pref-row">
          <div className="pref-input-group">
            <label>Cuisine you grew up with</label>
            <select name="cuisine_preference" value={form.cuisine_preference || 'any'} onChange={handleChange}>
              <option value="any">Any Indian</option>
              <option value="north_indian">North Indian</option>
              <option value="south_indian">South Indian</option>
              <option value="east_indian">East Indian</option>
              <option value="west_indian">West Indian</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label>Foods you don&apos;t eat (Optional)</label>
            <input type="text" name="food_dislikes" placeholder="e.g. karela, baingan, mushroom"
              value={form.food_dislikes || ''} onChange={handleChange} />
          </div>
        </div>
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint">Food restrictions <span>(optional)</span></label>
          <div className="pref-chip-row">
            {[
              { value: 'jain', label: 'Jain (no root vegetables)' },
              { value: 'no_onion_garlic', label: 'No onion or garlic' },
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                className={`pref-chip${(form.dietary_restrictions || []).includes(opt.value) ? ' active' : ''}`}
                onClick={() => handleToggle('dietary_restrictions', opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </>
  );
}
