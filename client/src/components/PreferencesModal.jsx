import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../providers/AuthContext';
import { m, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { preferencesAPI } from '../api/client';
import './PreferencesModal.css';
import { INJURIES, GYM_SUGGESTED_STYLE, YOGA_SUGGESTED_MINUTES, savedToForm } from './preferences/options';
import GymFields from './preferences/GymFields';
import YogaFields from './preferences/YogaFields';
import RoutineFields from './preferences/RoutineFields';
import DietFields from './preferences/DietFields';
import PanchakarmaFields from './preferences/PanchakarmaFields';
import RemedyFields from './preferences/RemedyFields';

export default function PreferencesModal({ isOpen, onClose, typeId, onSubmitSuccess }) {
  // `profile`, not `user`: `user` is a trimmed identity mapping with no
  // allergies on it, so seeding from it showed nothing for every patient.
  const { profile } = useAuth();
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(false);
  // Whether the practitioner has set the session length themselves. Once they
  // have, changing experience level must not move it back — a suggestion that
  // silently overwrites a deliberate choice is worse than no suggestion.
  const [durationTouched, setDurationTouched] = useState(false);
  // Same contract for the gym set scheme: choosing a goal suggests the style that
  // usually goes with it, and stops doing so the moment the practitioner picks
  // one for themselves.
  const [styleTouched, setStyleTouched] = useState(false);

  // Initialize defaults when modal opens
  useEffect(() => {
    if (isOpen && typeId) {
      // Seed the diet form's allergy chips from what onboarding already recorded, so
      // the person is not asked a second time for the one answer where forgetting to
      // repeat it is dangerous. The server unions the two lists regardless — this is
      // so the form shows what is actually being enforced, rather than empty chips
      // beside a plan that is withholding peanuts.
      const seeded = typeId === 'diet' && Array.isArray(profile?.allergies)
        ? { food_allergies: [...profile.allergies] }
        : {};
      setForm(seeded);
      setDurationTouched(false);
      setStyleTouched(false);
      // Every form opened blank, so saving one again to change a single answer
      // wiped the rest — the gym's injuries and working weights, the diet's
      // fasting days, the medicines already being taken. Each now starts from
      // what is saved, in the form's own shape; anything typed before the saved
      // answers arrive still wins.
      let live = true;
      preferencesAPI.getFeature(typeId)
        .then(({ data }) => {
          if (!live) return;
          if (!data?.is_set) {
            // Injuries are one list across the gym and yoga forms. A form opened
            // for the first time starts from it, or saving would clear the other's.
            const shared = data?.preferences?.injuries;
            if (Array.isArray(shared) && shared.length && (typeId === 'gym' || typeId === 'yoga')) {
              setForm(prev => ({ injuries: shared, ...prev }));
            }
            return;
          }
          const saved = savedToForm(typeId, data.preferences || {});
          setForm(prev => {
            // Keep only what the person changed; the seeded allergy chips are not
            // an answer, they are merged with the saved list below.
            const typed = Object.fromEntries(
              Object.entries(prev).filter(([k, v]) => seeded[k] !== v));
            const merged = { ...saved, ...typed };
            if (typeId === 'diet' && !('food_allergies' in typed)) {
              merged.food_allergies = [...new Set([
                ...(saved.food_allergies || []), ...(seeded.food_allergies || [])])];
            }
            return merged;
          });
          if (saved.workout_duration_minutes || saved.time_available_minutes) setDurationTouched(true);
          if (saved.training_style) setStyleTouched(true);
        })
        .catch(() => {});
      return () => { live = false; };
    }
  }, [isOpen, typeId, profile]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'time_available_minutes') setDurationTouched(true);
    if (name === 'training_style') setStyleTouched(true);
    setForm(prev => {
      const next = { ...prev, [name]: value };
      if (name === 'yoga_experience' && !durationTouched) {
        next.time_available_minutes = String(YOGA_SUGGESTED_MINUTES[value] ?? 30);
      }
      if (name === 'gym_goal' && !styleTouched) {
        next.training_style = GYM_SUGGESTED_STYLE[value] ?? '';
      }
      return next;
    });
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
      // Bodyweight is always available and is never a choice — the engine adds it
      // regardless, and a plan has to be buildable for someone who ticks nothing.
      payload.available_equipment = ['bodyweight', ...(form.available_equipment || [])];
      const splitTerms = (text) => String(text || '')
        .split(',').map(t => t.trim()).filter(Boolean);
      payload.exercise_preferences = {
        likes: splitTerms(form.likes),
        dislikes: splitTerms(form.dislikes),
      };
      delete payload.likes;
      delete payload.dislikes;
      // Empty means "follow the goal"; the engine derives the scheme. It used to
      // be forced to 'hypertrophy' for everyone, which nothing read — and which
      // would now quietly rewrite a fat-loss block into a hypertrophy one.
      payload.training_style = payload.training_style || null;
      payload.cardio_preference = payload.cardio_preference || 'moderate';
      payload.target_muscle_focus = payload.target_muscle_focus || 'full_body';
      payload.injuries = Array.isArray(form.injuries) ? form.injuries : [];
      payload.injury_detail = (form.injury_detail || '').trim() || null;
      // Only complete rows are sent; a half-filled one would be rejected.
      const known = {};
      Object.entries(form.known_lifts || {}).forEach(([lift, v]) => {
        const kg = parseFloat(v?.kg), reps = parseInt(v?.reps, 10);
        if (kg > 0 && reps > 0) known[lift] = { kg, reps };
      });
      payload.known_lifts = Object.keys(known).length ? known : null;
    } else if (typeId === 'yoga') {
      payload.yoga_goal = payload.yoga_goal || 'flexibility';
      payload.yoga_experience = payload.yoga_experience || 'beginner';
      payload.flexibility_level = payload.flexibility_level || 'moderate';
      // Fall back to the tier for the level they chose, not a flat 30. The
      // picker fills itself in as soon as an experience level is selected, so
      // this only runs for a payload that never went through the form.
      payload.time_available_minutes = parseInt(
        payload.time_available_minutes
          || YOGA_SUGGESTED_MINUTES[payload.yoga_experience]
          || 30,
        10);
      payload.time_of_day_preference = payload.time_of_day_preference || 'morning';
      payload.yoga_style_preference = [payload.yoga_style_preference || 'hatha'];
      payload.pranayama_interest = payload.pranayama_interest || 'yes';
      payload.meditation_interest = payload.meditation_interest || 'yes';
      payload.indoor_outdoor = payload.indoor_outdoor || 'indoor';
      payload.injuries = Array.isArray(form.injuries) ? form.injuries : [];
      payload.physical_limitations_detail = (form.physical_limitations_detail || '').trim() || null;
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
      payload.food_dislikes = typeof form.food_dislikes === 'string'
        ? form.food_dislikes.split(',').map(s => s.trim()).filter(Boolean)
        : (Array.isArray(form.food_dislikes) ? form.food_dislikes : []);
      payload.cuisine_preference = payload.cuisine_preference || 'any';
      payload.dietary_restrictions = Array.isArray(form.dietary_restrictions) ? form.dietary_restrictions : [];
    } else if (typeId === 'routine') {
      payload.wake_preference = payload.wake_preference || 'natural';
      payload.occupation_type = payload.occupation_type || 'moderately_active';
      payload.agni_type_self_report = payload.agni_type_self_report || 'assessed';
      payload.intermittent_fasting = payload.intermittent_fasting || 'no';
      payload.fasting_days = payload.fasting_days
        ? payload.fasting_days.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      payload.exclude_gym_plan = !!form.exclude_gym_plan;
      payload.exclude_yoga_plan = !!form.exclude_yoga_plan;
      payload.gym_time_of_day = payload.gym_time_of_day || 'morning';
      delete payload.integrate_gym_plan;
      delete payload.integrate_yoga_plan;
    } else if (typeId === 'panchakarma') {
      payload.panchakarma_goal = payload.panchakarma_goal || 'detox';
      payload.detox_experience = payload.detox_experience || 'none';
      payload.available_time_days = parseInt(payload.available_time_days || 7, 10);
      payload.setting = payload.setting || 'home';
      payload.self_care_time_per_day = payload.self_care_time_per_day || '30 min';
      payload.access_to_ayurvedic_herbs = payload.access_to_ayurvedic_herbs || 'willing_to_buy';
      payload.diet_adherence_ability = payload.diet_adherence_ability || 'partial';
      payload.current_ayurvedic_medicines = payload.current_ayurvedic_medicines
        ? payload.current_ayurvedic_medicines.split(',').map(s => s.trim()).filter(Boolean)
        : [];
    } else if (typeId === 'remedies' || typeId === 'medicines') {
      payload.current_ayurvedic_medicines = payload.current_ayurvedic_medicines
        ? payload.current_ayurvedic_medicines.split(',').map(s => s.trim()).filter(Boolean)
        : [];
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

  const renderInjuryChips = () => (
    <div className="pref-chip-row">
      {INJURIES.map(inj => {
        const chosen = (form.injuries || []).includes(inj.value)
        return (
          <button
            key={inj.value}
            type="button"
            aria-pressed={chosen}
            className={`pref-chip${chosen ? ' active' : ''}`}
            onClick={() => handleToggle('injuries', inj.value)}
          >
            {inj.label}
          </button>
        )
      })}
    </div>
  );

  const fieldProps = {
    form, setForm, handleChange, handleToggle, renderInjuryChips,
    durationTouched, setDurationTouched, styleTouched, setStyleTouched, profile,
  };

  const renderFormFields = () => {
    switch (typeId) {
      case 'gym':
        return <GymFields {...fieldProps} />;
      case 'yoga':
        return <YogaFields {...fieldProps} />;
      case 'routine':
        return <RoutineFields {...fieldProps} />;
      case 'diet':
        return <DietFields {...fieldProps} />;
      case 'panchakarma':
        return <PanchakarmaFields {...fieldProps} />;
      case 'remedies':
      case 'medicines':
        return <RemedyFields {...fieldProps} />;
      default:
        return null;
    }
  };

  // Portalled to <body>: rendered in place it sat inside the page's stacking
  // context, so on a phone the bottom tab bar painted over the Save button
  // whatever z-index the overlay had.
  return createPortal(
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
    </AnimatePresence>,
    document.body,
  );
}
