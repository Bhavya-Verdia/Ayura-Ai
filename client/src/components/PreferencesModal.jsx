import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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
      payload.yoga_style_preference = ['hatha'];
      payload.pranayama_interest = payload.pranayama_interest || 'yes';
      payload.meditation_interest = payload.meditation_interest || 'yes';
      payload.indoor_outdoor = payload.indoor_outdoor || 'indoor';
    } else if (typeId === 'diet' || typeId === 'routine') {
      payload.diet_goal = payload.diet_goal || 'general_wellness';
      payload.dietary_type = payload.dietary_type || 'vegetarian';
      payload.intermittent_fasting = payload.intermittent_fasting || 'no';
      payload.water_intake = payload.water_intake || '1-2L';
      payload.gut_health_issue = payload.gut_health_issue || 'healthy';
      payload.food_allergies = [];
      payload.food_intolerances = [];
      payload.fasting_days = payload.fasting_days 
        ? payload.fasting_days.split(',').map(s => s.trim()).filter(Boolean)
        : [];
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
                  <option value="none">None</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Time of Day</label>
                <select name="time_of_day_preference" value={form.time_of_day_preference || ''} onChange={handleChange} required>
                  <option value="morning">Morning</option>
                  <option value="evening">Evening</option>
                  <option value="both">Both</option>
                </select>
              </div>
            </div>
            <div className="pref-row">
              <div className="pref-input-group">
                <label>Include Pranayama?</label>
                <select name="pranayama_interest" value={form.pranayama_interest || ''} onChange={handleChange} required>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="already_practice">Already Practice</option>
                </select>
              </div>
              <div className="pref-input-group">
                <label>Guided Meditation?</label>
                <select name="meditation_interest" value={form.meditation_interest || ''} onChange={handleChange} required>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
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
      case 'diet':
      case 'routine':
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
              Recommendations are highly targeted to your Dosha and specific imbalances. 
              Always consult a practitioner before starting potent formulations.
            </p>
            <div className="pref-input-group">
              <label>Previous Ayurvedic Medicines Tried (optional, comma-separated)</label>
              <input 
                type="text" 
                name="previous_ayurvedic_medicines" 
                placeholder="e.g. Ashwagandha, Triphala" 
                value={form.previous_ayurvedic_medicines || ''} 
                onChange={handleChange} 
              />
            </div>
            <div className="pref-input-group">
              <label>Ingredient Access</label>
              <select name="ingredient_access" value={form.ingredient_access || ''} onChange={handleChange} required>
                <option value="kitchen_only">Kitchen Spices Only</option>
                <option value="can_buy_herbs">Can Buy Common Herbs</option>
                <option value="full_access">Full Access</option>
              </select>
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
        <motion.div 
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
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
