import { Wind, Flame, Waves } from 'lucide-react'

export const DOSHA_COLORS = {
  vata: 'var(--vata-color, #a08cf0)',
  pitta: 'var(--pitta-color, #fb923c)',
  kapha: 'var(--kapha-color, #5cab74)',
  satva: '#10b981',
  rajas: '#f59e0b',
  tamas: '#6366f1',
}

export const DOSHA_LABELS = { vata: 'Vata', pitta: 'Pitta', kapha: 'Kapha', satva: 'Satva', rajas: 'Rajas', tamas: 'Tamas' }
export const DOSHA_ICONS = { vata: Wind, pitta: Flame, kapha: Waves }

export const DOSHA_GUNAS = {
  vata:  ['Ruksha (dry)', 'Laghu (light)', 'Sheeta (cold)', 'Khara (rough)', 'Chala (mobile)'],
  pitta: ['Ushna (hot)', 'Tikshna (sharp)', 'Sara (flowing)', 'Laghu (light)', 'Snigdha (glossy)'],
  kapha: ['Guru (heavy)', 'Manda (slow)', 'Snigdha (oily)', 'Sthira (stable)', 'Sheeta (cold)'],
}

export const CHARAKA_REFS = {
  vata:      'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana',
  pitta:     'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana',
  kapha:     'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana',
  tridoshic: 'Ashtanga Hridayam, Sharira Sthana 3 — Sama Tridosha type',
}

export const CLASSICAL_TYPE_DISPLAY = {
  vata:        'Vata Prakriti',
  pitta:       'Pitta Prakriti',
  kapha:       'Kapha Prakriti',
  vata_pitta:  'Vata-Pitta Prakriti (Dvidoshaja)',
  pitta_vata:  'Pitta-Vata Prakriti (Dvidoshaja)',
  pitta_kapha: 'Pitta-Kapha Prakriti (Dvidoshaja)',
  kapha_pitta: 'Kapha-Pitta Prakriti (Dvidoshaja)',
  vata_kapha:  'Vata-Kapha Prakriti (Dvidoshaja)',
  kapha_vata:  'Kapha-Vata Prakriti (Dvidoshaja)',
  tridoshic:   'Sama Tridosha Prakriti (Sannipata)',
}

export const AMA_COLORS = {
  none:     'var(--ayura-teal, #5cab74)',
  low:      'var(--ayura-teal, #5cab74)',
  mild:     'var(--ayura-amber, #f59e0b)',
  moderate: '#fb923c',
  high:     '#f87171',
}

export const TRAIT_PRIORITY_LABEL = {
  body_frame: 'Primary', digestion: 'Primary', stress_response: 'Primary',
  memory: 'Primary', agni_type: 'Primary',
  temperature: 'Strong', sleep: 'Strong',
  decision_making: 'Strong', emotional_nature: 'Strong', anger_style: 'Strong', stool_pattern: 'Strong',
  nadi_rhythm: 'Strong',
  energy: 'Moderate', skin: 'Moderate', eating_habits: 'Moderate', speech: 'Moderate',
  eye_quality: 'Moderate', voice_quality: 'Moderate', mutra_pattern: 'Moderate',
  walk_pace: 'Secondary', hair: 'Secondary',
  motivation_source: 'Manasa', mind_clarity: 'Manasa', emotional_quality: 'Manasa',
  daily_discipline: 'Manasa', conflict_approach: 'Manasa',
}

export const TRAIT_DISPLAY_NAMES = {
  body_frame: 'Body Frame', skin: 'Skin', digestion: 'Digestion', sleep: 'Sleep',
  temperature: 'Temperature', hair: 'Hair', energy: 'Energy',
  stress_response: 'Stress Response', memory: 'Memory', decision_making: 'Decisions',
  speech: 'Speech', emotional_nature: 'Emotions', eating_habits: 'Eating',
  walk_pace: 'Walk', anger_style: 'Anger',
  agni_type: 'Agni (Digestive Fire)', stool_pattern: 'Bowel Pattern (Mala)',
  nadi_rhythm: 'Pulse (Nadi)', mutra_pattern: 'Urine (Mutra)',
  eye_quality: 'Eyes (Drik)', voice_quality: 'Voice (Shabda)',
  motivation_source: 'Motivation (Manasa)', mind_clarity: 'Mental Clarity (Manasa)',
  emotional_quality: 'Emotions (Manasa)', daily_discipline: 'Discipline (Manasa)',
  conflict_approach: 'Conflict Style (Manasa)',
}
