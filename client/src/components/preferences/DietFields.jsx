// The diet preferences form. PreferencesModal owns the state and the
// save; `server/tests/test_preferences_form_fields.py` reads this file to hold
// every field it collects to the diet schema.
import { GOALS, DIETARY_TYPES } from './options';

import { tr } from '../../lib/tr'
import { Trans } from 'react-i18next'
export default function DietFields({ form, handleChange, handleToggle }) {
  return (
      <>
        <div className="pref-input-group">
          <label htmlFor="pref-diet_goal">{tr('ui.dietFields.primaryGoal', 'Primary Goal')}</label>
          <select id="pref-diet_goal" name="diet_goal" value={form.diet_goal || ''} onChange={handleChange} required>
            <option value="">{tr('ui.dietFields.selectYourGoal', 'Select your goal...')}</option>
            {GOALS.diet.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>
        <div className="pref-input-group">
          <label htmlFor="pref-dietary_type">{tr('ui.dietFields.dietaryType', 'Dietary Type')}</label>
          <select id="pref-dietary_type" name="dietary_type" value={form.dietary_type || ''} onChange={handleChange} required>
            <option value="">{tr('ui.dietFields.selectYourDiet', 'Select your diet...')}</option>
            {DIETARY_TYPES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
          <p className="pref-hint">
            {tr('ui.dietFields.ayuraSFoodLibraryIs', 'Ayura\'s food library is a vegetarian Nighantu — every food in it is screened against your conditions by name. We would rather offer two diets we can screen than five we cannot.')}
          </p>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-intermittent_fasting">{tr('ui.dietFields.intermittentFasting', 'Intermittent Fasting')}</label>
            <select id="pref-intermittent_fasting" name="intermittent_fasting" value={form.intermittent_fasting || 'no'} onChange={handleChange} required>
              <option value="no">{tr('ui.dietFields.noFasting', 'No Fasting')}</option>
              <option value="12:12">{tr('ui.dietFields.n1212Balanced', '12:12 (Balanced)')}</option>
              <option value="14:10">{tr('ui.dietFields.n1410Moderate', '14:10 (Moderate)')}</option>
              <option value="16:8">{tr('ui.dietFields.n168Advanced', '16:8 (Advanced)')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-water_intake">{tr('ui.dietFields.dailyWaterIntake', 'Daily Water Intake')}</label>
            <select id="pref-water_intake" name="water_intake" value={form.water_intake || '1-2L'} onChange={handleChange} required>
              <option value="< 1L">&lt; 1L</option>
              <option value="1-2L">1-2L</option>
              <option value="2-3L">2-3L</option>
              <option value="> 3L">&gt; 3L</option>
            </select>
          </div>
        </div>
        <div className="pref-row">
          <div className="pref-input-group">
            <label htmlFor="pref-gut_health_issue">{tr('ui.dietFields.gutHealth', 'Gut Health')}</label>
            <select id="pref-gut_health_issue" name="gut_health_issue" value={form.gut_health_issue || 'healthy'} onChange={handleChange} required>
              <option value="healthy">{tr('ui.dietFields.healthy', 'Healthy')}</option>
              <option value="acidity">{tr('ui.dietFields.acidityHeartburn', 'Acidity / Heartburn')}</option>
              <option value="constipation">{tr('ui.dietFields.constipation', 'Constipation')}</option>
              <option value="bloating">{tr('ui.dietFields.bloating', 'Bloating')}</option>
              <option value="ibs">IBS</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-fasting_days">{tr('ui.dietFields.fastingDaysOptional', 'Fasting Days (Optional)')}</label>
            <input id="pref-fasting_days" type="text" name="fasting_days" placeholder={tr('ui.dietFields.eGMondayEkadashi', 'e.g. Monday, Ekadashi')} value={form.fasting_days || ''} onChange={handleChange} />
          </div>
        </div>
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint"><Trans i18nKey="ui.dietFields.foodAllergies0SelectAll" defaults={"Food Allergies <0>(select all that apply)</0>"} components={[<span />]} /></label>
          <div className="pref-chip-row">
            {[
              { value: 'gluten', label: tr('ui.dietFields.glutenWheat', 'Gluten / Wheat') },
              { value: 'dairy', label: tr('ui.dietFields.dairy', 'Dairy') },
              { value: 'nuts_tree', label: tr('ui.dietFields.treeNuts', 'Tree Nuts') },
              { value: 'peanuts', label: tr('ui.dietFields.peanuts', 'Peanuts') },
              { value: 'soy', label: tr('ui.dietFields.soy', 'Soy') },
              { value: 'eggs', label: tr('ui.dietFields.eggs', 'Eggs') },
              { value: 'shellfish', label: tr('ui.dietFields.shellfish', 'Shellfish') },
              { value: 'fish', label: tr('ui.dietFields.fish', 'Fish') },
              { value: 'sesame', label: tr('ui.dietFields.sesameTil', 'Sesame / Til') },
              { value: 'mustard', label: tr('ui.dietFields.mustardRai', 'Mustard / Rai') },
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
          <label className="pref-label-hint"><Trans i18nKey="ui.dietFields.foodIntolerances0SelectAll" defaults={"Food Intolerances <0>(select all that apply)</0>"} components={[<span />]} /></label>
          <div className="pref-chip-row">
            {[
              { value: 'lactose', label: tr('ui.dietFields.lactose', 'Lactose') },
              { value: 'fructose', label: tr('ui.dietFields.fructose', 'Fructose') },
              { value: 'gluten_sensitivity', label: tr('ui.dietFields.glutenSensitivity', 'Gluten Sensitivity') },
              { value: 'histamine', label: tr('ui.dietFields.histamine', 'Histamine') },
              { value: 'fodmap', label: tr('ui.dietFields.fodmaps', 'FODMAPs') },
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
            <label htmlFor="pref-cuisine_preference">{tr('ui.dietFields.cuisineYouGrewUpWith', 'Cuisine you grew up with')}</label>
            <select id="pref-cuisine_preference" name="cuisine_preference" value={form.cuisine_preference || 'any'} onChange={handleChange}>
              <option value="any">{tr('ui.dietFields.anyIndian', 'Any Indian')}</option>
              <option value="north_indian">{tr('ui.dietFields.northIndian', 'North Indian')}</option>
              <option value="south_indian">{tr('ui.dietFields.southIndian', 'South Indian')}</option>
              <option value="east_indian">{tr('ui.dietFields.eastIndian', 'East Indian')}</option>
              <option value="west_indian">{tr('ui.dietFields.westIndian', 'West Indian')}</option>
            </select>
          </div>
          <div className="pref-input-group">
            <label htmlFor="pref-food_dislikes">{tr('ui.dietFields.foodsYouDonTEat', 'Foods you don\'t eat (Optional)')}</label>
            <input id="pref-food_dislikes" type="text" name="food_dislikes" placeholder={tr('ui.dietFields.eGKarelaBainganMushroom', 'e.g. karela, baingan, mushroom')}
              value={form.food_dislikes || ''} onChange={handleChange} />
          </div>
        </div>
        <div className="pref-input-group pref-full">
          <label className="pref-label-hint"><Trans i18nKey="ui.dietFields.foodRestrictions0Optional0" defaults={"Food restrictions <0>(optional)</0>"} components={[<span />]} /></label>
          <div className="pref-chip-row">
            {[
              { value: 'jain', label: tr('ui.dietFields.jainNoRootVegetables', 'Jain (no root vegetables)') },
              { value: 'no_onion_garlic', label: tr('ui.dietFields.noOnionOrGarlic', 'No onion or garlic') },
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
