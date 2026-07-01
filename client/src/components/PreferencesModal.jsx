import React, { useState, useEffect } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { preferencesAPI } from '../api/client';
import './PreferencesModal.css';

const GOALS = {
  gym: [
    { value: 'fat_loss', label: 'Fat Loss' },
    { value: 'muscle_gain', label: 'Muscle Gain' },
    { value: 'endurance', label: 'Endurance' },
    { value: 'strength', label: 'Strength' },
    { value: 'general_fitness', label: 'General Fitness' }
  ],
  yoga: [
    { value: 'flexibility', label: 'Flexibility' },
    { value: 'stress_relief', label: 'Stress Relief' },
    { value: 'strength', label: 'Strength' },
    { value: 'balance', label: 'Balance' },
    { value: 'healing', label: 'Healing' },
    { value: 'spiritual', label: 'Spiritual' }
  ],
  diet: [
    { value: 'weight_loss', label: 'Weight Loss' },
    { value: 'muscle_support', label: 'Muscle Support' },
    { value: 'gut_health', label: 'Gut Health' },
    { value: 'energy', label: 'Energy' },
    { value: 'detox', label: 'Detox' },
    { value: 'general_wellness', label: 'General Wellness' }
  ],
  routine: [
    { value: 'weight_loss', label: 'Weight Loss' },
    { value: 'muscle_support', label: 'Muscle Support' },
    { value: 'gut_health', label: 'Gut Health' },
    { value: 'energy', label: 'Energy' },
    { value: 'detox', label: 'Detox' },
    { value: 'general_wellness', label: 'General Wellness' }
  ],
  panchakarma: [
    { value: 'detox', label: 'Detox' },
    { value: 'rejuvenation', label: 'Rejuvenation' },
    { value: 'stress_relief', label: 'Stress Relief' },
    { value: 'seasonal_cleanse', label: 'Seasonal Cleanse' },
    { value: 'specific_condition', label: 'Specific Condition' }
  ]
};

const DIETARY_TYPES = [
  { value: 'vegetarian', label: 'Vegetarian' },
  { value: 'vegan', label: 'Vegan' },
  { value: 'eggetarian', label: 'Eggetarian' },
  { value: 'non_vegetarian', label: 'Non-Vegetarian' },
  { value: 'pescatarian', label: 'Pescatarian' }
];

export default function PreferencesModal({ isOpen, onClose, typeId, onSubmitSuccess }) {
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(false);

  // Initialize defaults when modal opens
  useEffect(() => {
    if (isOpen && typeId) {
      setForm({});
    }
  }, [isOpen, typeId]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleToggle = (field, value) => {
    setForm(prev => {
      const current = Array.isArray(prev[field]) ? prev[field] : [];
      const next = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value];
      return { ...prev, [field]: next };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    // Transform arrays for specific fields if necessary
    const payload = { ...form };
    
    // Feature specific defaults / cleanup
    if (typeId === 'gym') {
      payload.gym_goal = payload.gym_goal || 'general_fitness';
      payload.workout_days_per_week = parseInt(payload.workout_days_per_week || 4, 10);
      payload.workout_duration_minutes = parseInt(payload.workout_duration_minutes || 45, 10);
      payload.available_equipment = ['bodyweight']; // hardcode for now
      payload.training_style = payload.training_style || 'hypertrophy';
      payload.cardio_preference = payload.cardio_preference || 'moderate';
      payload.target_muscle_focus = payload.target_muscle_focus || 'full_body';
    } else if (typeId === 'yoga') {
      payload.yoga_goal = payload.yoga_goal || 'flexibility';
      payload.yoga_experience = payload.yoga_experience || 'beginner';
      payload.flexibility_level = payload.flexibility_level || 'moderate';
      payload.time_available_minutes = parseInt(payload.time_available_minutes || 30, 10);
      payload.time_of_day_preference = payload.time_of_day_preference || 'morning';
      payload.yoga_style_preference = [payload.yoga_style_preference || 'hatha'];
      payload.pranayama_interest = payload.pranayama_interest || 'yes';
      payload.meditation_interest = payload.meditation_interest || 'yes';
      payload.indoor_outdoor = payload.indoor_outdoor || 'indoor';
    } else if (typeId === 'diet') {
      payload.diet_goal = payload.diet_goal || 'general_wellness';
      payload.dietary_type = payload.dietary_type || 'vegetarian';
      payload.intermittent_fasting = payload.intermittent_fasting || 'no';
      payload.water_intake = payload.water_intake || '1-2L';
      payload.gut_health_issue = payload.gut_health_issue || 'healthy';
      payload.food_allergies = Array.isArray(form.food_allergies) ? form.food_allergies : [];
      payload.food_intolerances = Array.isArray(form.food_intolerances) ? form.food_intolerances : [];
      payload.fasting_days = payload.fasting_days
        ? payload.fasting_days.split(',').map(s => s.trim()).filter(Boolean)
        : [];
    } else if (typeId === 'routine') {
      payload.wake_preference = payload.wake_preference || 'natural';
      payload.occupation_type = payload.occupation_type || 'moderately_active';
      payload.agni_type_self_report = payload.agni_type_self_report || 'sama';
      payload.intermittent_fasting = payload.intermittent_fasting || 'no';
      payload.fasting_days = payload.fasting_days
        ? payload.fasting_days.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      payload.integrate_gym_plan = !!form.integrate_gym_plan;
      payload.integrate_yoga_plan = !!form.integrate_yoga_plan;
    } else if (typeId === 'panchakarma') {
      payload.panchakarma_goal = payload.panchakarma_goal || 'detox';
      payload.detox_experience = payload.detox_experience || 'none';
      payload.available_time_days = parseInt(payload.available_time_days || 7, 10);
      payload.setting = payload.setting || 'home';
      payload.self_care_time_per_day = payload.self_care_time_per_day || '30 min';
      payload.access_to_ayurvedic_herbs = payload.access_to_ayurvedic_herbs || 'willing_to_buy';
      payload.diet_adherence_ability = payload.diet_adherence_ability || 'partial';
    } else if (typeId === 'remedies' || typeId === 'medicines') {
      payload.previous_ayurvedic_medicines = payload.previous_ayurvedic_medicines 
        ? payload.previous_ayurvedic_medicines.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      payload.ingredient_access = payload.ingredient_access || 'kitchen_only';
    }

    try {
      await preferencesAPI.saveFeature(typeId, payload);
      toast.success('Preferences saved successfully!');
      onSubmitSuccess(); // Trigger plan generation
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save preferences.');
    } finally {
      setLoading(false);
    }
  };

  const renderFormFields = () => {
    switch (typeId) {
      case 'gym':
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
                <select name="training_style" value={form.training_style || ''} onChange={handleChange} required>
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
          </>
        );
      case 'yoga':
        return (
          <>
            <div className="pref-input-group">
              <label>Primary Focus</label>
              <select name="yoga_goal" value={form.yoga_goal || ''} onChange={handleChange} required>
                <option value="">Select your focus...</option>
                {GOALS.yoga.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>
            <div className="pref-row">
              <div className="pref-input-group">
                <label>Experience Level</label>
                <select name="yoga_experience" value={form.yoga_experience || ''} onChange={handleChange} required>
                  <option value="none">None — never practiced</option>
                  <option value="beginner">Beginner — under 1 year</option>
                  <option value="intermediate">Intermediate — 1–3 years</option>
                  <option value="advanced">Advanced — 3+ years</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Current Flexibility</label>
                <select name="flexibility_level" value={form.flexibility_level || ''} onChange={handleChange} required>
                  <option value="low">Low — limited range</option>
                  <option value="moderate">Moderate — average flexibility</option>
                  <option value="high">High — very flexible</option>
                </select>
              </div>
            </div>
            <div className="pref-row">
              <div className="pref-input-group">
                <label>Yoga Style</label>
                <select name="yoga_style_preference" value={form.yoga_style_preference || ''} onChange={handleChange} required>
                  <option value="hatha">Hatha — slow, foundational</option>
                  <option value="vinyasa">Vinyasa — flowing, dynamic</option>
                  <option value="restorative">Restorative — passive, healing</option>
                  <option value="yin">Yin — long holds, deep tissue</option>
                  <option value="power">Power — strength-focused</option>
                  <option value="ashtanga">Ashtanga — structured series</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Session Duration (mins)</label>
                <input type="number" name="time_available_minutes" min={15} max={90} value={form.time_available_minutes || ''} onChange={handleChange} required placeholder="e.g. 30" />
              </div>
            </div>
            <div className="pref-row">
              <div className="pref-input-group">
                <label>Time of Day</label>
                <select name="time_of_day_preference" value={form.time_of_day_preference || ''} onChange={handleChange} required>
                  <option value="morning">Morning</option>
                  <option value="evening">Evening</option>
                  <option value="both">Both</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Include Pranayama?</label>
                <select name="pranayama_interest" value={form.pranayama_interest || ''} onChange={handleChange} required>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="already_practice">Already Practice</option>
                </select>
              </div>
            </div>
            <div className="pref-row">
              <div className="pref-input-group">
                <label>Location</label>
                <select name="indoor_outdoor" value={form.indoor_outdoor || ''} onChange={handleChange} required>
                  <option value="indoor">Indoor</option>
                  <option value="outdoor">Outdoor</option>
                  <option value="both">Both</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Physical Limitations</label>
                <input type="text" name="physical_limitations_detail" placeholder="e.g. bad knees" value={form.physical_limitations_detail || ''} onChange={handleChange} />
              </div>
            </div>
          </>
        );
      case 'routine':
        return (
          <>
            <p className="pref-notice">
              Your daily routine is personalised from your Dosha, season, conditions, and the preferences below. Gym and Yoga integration pulls your existing plan schedules automatically.
            </p>
            <div className="pref-row">
              <div className="pref-input-group">
                <label>Wake Preference</label>
                <select name="wake_preference" value={form.wake_preference || 'natural'} onChange={handleChange} required>
                  <option value="early">Early — 4:30–5:30 AM</option>
                  <option value="natural">Natural — 5:30–6:30 AM</option>
                  <option value="late">Late — 6:30–7:30 AM</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Occupation Type</label>
                <select name="occupation_type" value={form.occupation_type || 'moderately_active'} onChange={handleChange} required>
                  <option value="sedentary">Sedentary — mostly desk / driving</option>
                  <option value="moderately_active">Moderately Active — mixed</option>
                  <option value="very_active">Very Active — labour / athlete</option>
                </select>
              </div>
            </div>
            <div className="pref-row">
              <div className="pref-input-group">
                <label>
                  Agni (Digestive Fire) Type
                  <span className="pref-hint-sub"> — how would you describe your digestion?</span>
                </label>
                <select name="agni_type_self_report" value={form.agni_type_self_report || 'sama'} onChange={handleChange} required>
                  <option value="sama">Sama — Balanced, regular digestion</option>
                  <option value="manda">Manda — Slow, heavy, bloated after meals</option>
                  <option value="tikshna">Tikshna — Sharp, hungry quickly, acidity</option>
                  <option value="vishama">Vishama — Irregular, some days strong, some weak</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Intermittent Fasting Window</label>
                <select name="intermittent_fasting" value={form.intermittent_fasting || 'no'} onChange={handleChange}>
                  <option value="no">No Fasting</option>
                  <option value="12:12">12:12 — Balanced</option>
                  <option value="14:10">14:10 — Moderate</option>
                  <option value="16:8">16:8 — Advanced</option>
                </select>
              </div>
            </div>
            <div className="pref-input-group pref-full">
              <label>Fasting Days <span className="pref-hint">(optional, comma-separated)</span></label>
              <input
                type="text"
                name="fasting_days"
                placeholder="e.g. Monday, Ekadashi"
                value={form.fasting_days || ''}
                onChange={handleChange}
              />
            </div>
            <div className="pref-input-group pref-full">
              <label className="pref-label-hint">Plan Integration <span>(select to annotate your routine with existing plans)</span></label>
              <div className="pref-chip-row">
                <button
                  type="button"
                  className={`pref-chip${form.integrate_gym_plan ? ' active' : ''}`}
                  onClick={() => setForm(p => ({ ...p, integrate_gym_plan: !p.integrate_gym_plan }))}
                >
                  Integrate Gym Plan
                </button>
                <button
                  type="button"
                  className={`pref-chip${form.integrate_yoga_plan ? ' active' : ''}`}
                  onClick={() => setForm(p => ({ ...p, integrate_yoga_plan: !p.integrate_yoga_plan }))}
                >
                  Integrate Yoga Plan
                </button>
              </div>
            </div>
          </>
        );
      case 'diet':
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
          </>
        );
      case 'panchakarma':
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
                <label>Available Days (3–30)</label>
                <input type="number" name="available_time_days" min={3} max={30} value={form.available_time_days || ''} onChange={handleChange} required />
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
          </>
        );
      case 'remedies':
      case 'medicines':
        return (
          <>
            <p className="pref-notice">
              Recommendations are clinically targeted to your Vikriti (imbalance state), Agni, and conditions.
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
      default:
        return null;
    }
  };

  return (
    <AnimatePresence>
      <div className="pref-modal-overlay">
        <m.div 
          className="pref-modal-content"
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.3 }}
        >
          <div className="pref-modal-header">
            <h2 className="pref-modal-title">Configure {typeId.charAt(0).toUpperCase() + typeId.slice(1)} Preferences</h2>
            <button className="pref-modal-close" onClick={onClose}>×</button>
          </div>
          
          <p className="pref-modal-subtitle">
            To generate a highly personalized plan, we need a few specific details about your goals and constraints.
          </p>

          <form className="pref-modal-form" onSubmit={handleSubmit}>
            {renderFormFields()}
            
            <div className="pref-modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Saving...' : 'Save & Generate ✦'}
              </button>
            </div>
          </form>
        </m.div>
      </div>
    </AnimatePresence>
  );
}
