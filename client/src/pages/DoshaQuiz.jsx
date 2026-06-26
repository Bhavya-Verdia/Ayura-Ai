import { useState, useEffect, Suspense, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../providers/AuthContext'
import { profileAPI } from '../api/client'
import { Helmet } from 'react-helmet-async'
import React from 'react'
import './DoshaQuiz.css'

const LazyParticleField = React.lazy(() => import('../components/ParticleField'))

// ── Physical trait questions — NO dosha labels shown ──────────────────────────
const TRAIT_QUESTIONS = [
  {
    id: 'body_frame',
    question: 'What best describes your natural body frame?',
    hint: 'Think about your lifelong tendency, not your current weight',
    options: [
      { value: 'vata', icon: '🪶', label: 'Slim & light', desc: 'Naturally lean, fine-boned. Hard to gain weight even eating a lot. Small wrists and ankles.' },
      { value: 'pitta', icon: '⚡', label: 'Medium & athletic', desc: 'Medium build, well-proportioned. Gain and lose weight fairly easily. Natural muscle tone.' },
      { value: 'kapha', icon: '🏔️', label: 'Solid & sturdy', desc: 'Larger, well-built frame. Tend to gain weight easily and lose it slowly. Strong and resilient.' },
    ],
  },
  {
    id: 'skin',
    question: 'How does your skin behave in normal conditions?',
    hint: 'Not during illness or stress — your everyday baseline',
    options: [
      { value: 'vata', icon: '🌵', label: 'Dry & delicate', desc: 'Tends to be dry, rough, or cracked — especially hands, lips, and heels. Gets tight in cold weather.' },
      { value: 'pitta', icon: '🌡️', label: 'Warm & reactive', desc: 'Tends to be warm, sometimes oily. Prone to breakouts, redness, or flushing. Sensitive to products.' },
      { value: 'kapha', icon: '💧', label: 'Smooth & moist', desc: 'Generally smooth, cool, and soft. Rarely dry. Naturally dewy — may feel slightly thick or retain moisture.' },
    ],
  },
  {
    id: 'digestion',
    question: 'How would you describe your natural digestion?',
    hint: 'Your lifelong digestive pattern, not a recent stomach issue',
    options: [
      { value: 'vata', icon: '🌊', label: 'Variable & sensitive', desc: 'Irregular — sometimes fast, sometimes slow. Often experience bloating, gas, or alternating habits. Appetite comes and goes.' },
      { value: 'pitta', icon: '🔥', label: 'Strong & intense', desc: 'Digest quickly and thoroughly. Get very irritable or uncomfortable when meals are delayed. Strong, sharp appetite.' },
      { value: 'kapha', icon: '🐢', label: 'Slow & steady', desc: 'Digest slowly but steadily. Can skip meals without much discomfort. Rarely feel intense hunger. Stay full a long time.' },
    ],
  },
  {
    id: 'sleep',
    question: 'How do you naturally sleep?',
    hint: 'Without sleep aids, in a normal period of life',
    options: [
      { value: 'vata', icon: '🌙', label: 'Light & restless', desc: 'Wake easily to sounds or thoughts. Sometimes hard to fall asleep. Have vivid, anxious, or busy dreams. Often feel I need more rest.' },
      { value: 'pitta', icon: '⭐', label: 'Moderate & refreshing', desc: 'Fall asleep without much trouble. Occasionally wake but go back to sleep. Feel genuinely rested with 6–7 hours.' },
      { value: 'kapha', icon: '😴', label: 'Deep & heavy', desc: 'Sleep heavily and very deeply. Hard to wake up, especially in the morning. Need 8+ hours. Often feel groggy even after long sleep.' },
    ],
  },
  {
    id: 'temperature',
    question: 'How do you naturally respond to temperature?',
    hint: 'Your default preference, not during illness',
    options: [
      { value: 'vata', icon: '🧣', label: 'Love warmth', desc: 'Dislike cold intensely. Always first to reach for a sweater. Hands and feet tend to be cold. Prefer warm food and drinks.' },
      { value: 'pitta', icon: '❄️', label: 'Love cool', desc: 'Uncomfortable in heat. Prefer cool or air-conditioned spaces. Tend to run warm. Enjoy cold water, cold weather, and shade.' },
      { value: 'kapha', icon: '☁️', label: 'Comfortable & adaptable', desc: "Handle most temperatures well. Don't have strong preferences, though you might feel a little more comfortable with some warmth." },
    ],
  },
  {
    id: 'hair',
    question: 'How would you describe your hair naturally?',
    hint: 'Think of your hair before any styling, treatments, or colouring',
    options: [
      { value: 'vata', icon: '🌾', label: 'Fine & dry', desc: 'Thin, dry, frizzy, or brittle — prone to split ends and dandruff. Gets flyaway in wind.' },
      { value: 'pitta', icon: '✨', label: 'Fine & silky', desc: 'Fine, silky, and gets oily quickly. Prone to premature graying or early thinning.' },
      { value: 'kapha', icon: '🌊', label: 'Thick & lustrous', desc: 'Thick, wavy, naturally oily, and strong. Grows well and rarely breaks easily.' },
    ],
  },
  {
    id: 'energy',
    question: 'How would you describe your natural energy pattern?',
    hint: 'Your default energy — not during illness or high stress',
    options: [
      { value: 'vata', icon: '⚡', label: 'Bursts & crashes', desc: 'Energy comes in intense bursts that drop quickly. Poor long-term stamina. Need frequent rest.' },
      { value: 'pitta', icon: '🔥', label: 'Strong & sustained', desc: 'Good consistent energy, especially mid-day. Driven, purposeful, and goal-oriented.' },
      { value: 'kapha', icon: '🌿', label: 'Slow start, high stamina', desc: 'Slow to get going in the morning, but once warmed up have excellent endurance all day.' },
    ],
  },
  {
    id: 'stress_response',
    question: 'When you feel overwhelmed or under pressure, you tend to:',
    hint: 'Think about your most consistent pattern — not the best version of yourself',
    options: [
      { value: 'vata', icon: '🌀', label: 'Worry & scatter', desc: 'Get anxious, overthink, freeze up, or feel scattered. Mind races, hard to focus. Might avoid the situation.' },
      { value: 'pitta', icon: '⚡', label: 'Get sharp & push', desc: 'Get impatient or irritated. Confront the problem head-on, sometimes too aggressively. Driven to solve it fast.' },
      { value: 'kapha', icon: '🐢', label: 'Withdraw & slow down', desc: 'Go quiet, pull back, or feel heavy and stuck. Take a long time to process. May comfort-eat or over-sleep.' },
    ],
  },
  {
    id: 'memory',
    question: 'How does your memory naturally work?',
    hint: 'Your baseline pattern over a lifetime — not when stressed or sleep-deprived',
    options: [
      { value: 'vata', icon: '⚡', label: 'Quick to learn, quick to forget', desc: 'Pick up new things fast and make creative connections — but details and names fade quickly. Many ideas, less follow-through.' },
      { value: 'pitta', icon: '🎯', label: 'Sharp and precise', desc: 'Learn things systematically and remember them accurately. Good recall for facts, events, and details. Strong focus when motivated.' },
      { value: 'kapha', icon: '🏛️', label: 'Slow to learn, never forget', desc: "Take more time to absorb new information, but once it's in — it stays forever. Excellent long-term retention." },
    ],
  },
  {
    id: 'decision_making',
    question: 'How do you naturally make decisions?',
    hint: 'Especially important ones — not trivial daily choices',
    options: [
      { value: 'vata', icon: '🌊', label: 'Change my mind often', desc: 'Hard to decide. Consider many options, feel pulled in different directions. May regret decisions and second-guess yourself.' },
      { value: 'pitta', icon: '🎯', label: 'Decide quickly and firmly', desc: 'Assess the facts, decide fast, and commit with confidence. Rarely second-guess yourself. Can be too rigid sometimes.' },
      { value: 'kapha', icon: '⚓', label: 'Deliberate for a long time', desc: 'Take your time, weigh everything carefully, and consult others before deciding. Once decided, very hard to change.' },
    ],
  },
  {
    id: 'speech',
    question: 'How would others describe the way you naturally speak?',
    hint: 'In everyday relaxed conversation — not in formal or high-stress settings',
    options: [
      { value: 'vata', icon: '🌬️', label: 'Fast and expressive', desc: 'Talk fast, jump between topics, use lots of gestures. Enthusiastic and creative but sometimes hard to follow. Trail off mid-thought.' },
      { value: 'pitta', icon: '🎯', label: 'Clear and direct', desc: 'Precise, articulate, and confident. Get to the point. Can come across as blunt or critical without meaning to.' },
      { value: 'kapha', icon: '🎵', label: 'Calm and melodious', desc: 'Speak slowly and thoughtfully. Pleasant voice, measured words, considerate. Sometimes take too long to get to the point.' },
    ],
  },
  {
    id: 'emotional_nature',
    question: 'What best describes your natural emotional baseline?',
    hint: 'In a normal period of life — not during a crisis or exceptionally happy time',
    options: [
      { value: 'vata', icon: '🦋', label: 'Enthusiastic but variable', desc: 'Quick to feel excited, creative, and inspired — but also quick to worry, feel anxious, or lose enthusiasm. Emotions shift fast.' },
      { value: 'pitta', icon: '🔥', label: 'Intense and purposeful', desc: "Feel things deeply and strongly. Passionate, ambitious, sometimes perfectionistic. Prone to frustration when things don't go to plan." },
      { value: 'kapha', icon: '🌳', label: 'Stable and nurturing', desc: 'Naturally calm, steady, and caring. Rarely rattled by small things. But can become attached, possessive, or hold onto grudges.' },
    ],
  },
  {
    id: 'eating_habits',
    question: 'How do you naturally approach eating?',
    hint: 'Your default pattern when life is normal — not during illness or extreme stress',
    options: [
      { value: 'vata', icon: '🏃', label: 'Quick & irregular', desc: 'Eat fast, often while distracted or standing. Skip meals without noticing, then overeat. Appetite varies day to day.' },
      { value: 'pitta', icon: '🎯', label: 'Precise & scheduled', desc: 'Eat at set times, fully focused on the meal. Get irritable or headachy when meals are delayed. Strong, consistent appetite.' },
      { value: 'kapha', icon: '🍽️', label: 'Slow & social', desc: 'Eat slowly and enjoy every bite. Linger at the table. Never really starving but always happy to eat. Metabolism is slow.' },
    ],
  },
  {
    id: 'walk_pace',
    question: 'How do you naturally walk?',
    hint: "When you're not in a hurry — your default gait",
    options: [
      { value: 'vata', icon: '🌬️', label: 'Fast & light', desc: 'Quick, light steps with variable pace. Often change direction. Hard to keep still. People say you move fast.' },
      { value: 'pitta', icon: '🚶', label: 'Purposeful & medium', desc: "Walk with clear intention and direction. Medium pace, heel-to-toe. People can tell you're going somewhere." },
      { value: 'kapha', icon: '⚓', label: 'Slow & grounded', desc: 'Steady, unhurried, stable stride. Hard to rush. Feel planted and solid when you walk.' },
    ],
  },
  {
    id: 'anger_style',
    question: 'When you get angry, what typically happens?',
    hint: 'Your most natural pattern — not what you wish you did',
    options: [
      { value: 'vata', icon: '🌀', label: 'Quick flare, quick fade', desc: 'Get agitated or anxious fast, but the feeling passes quickly. Often forget what upset you. May avoid confrontation.' },
      { value: 'pitta', icon: '⚡', label: 'Sharp & direct', desc: 'Get visibly angry, may say cutting or critical things. Express it clearly. Hold it for a short while, then move on.' },
      { value: 'kapha', icon: '🌋', label: 'Slow burn, long memory', desc: 'Slow to get angry, but once there it stays. Hold grudges for a long time. Rarely blow up but simmer internally.' },
    ],
  },
  {
    id: 'agni_type',
    question: 'How would you describe your Agni — your digestive fire?',
    hint: 'Agni is the cornerstone of Ayurvedic health (Charaka Sutrasthana 15.3). Think about your lifelong digestive pattern.',
    options: [
      { value: 'sama', icon: '🌿', label: 'Sama Agni — Balanced', desc: 'Consistent appetite, digest most foods well, regular elimination, feel energised after meals. Rarely have digestive complaints.' },
      { value: 'vata', icon: '🌊', label: 'Vishama Agni — Irregular', desc: 'Appetite and digestion vary unpredictably — sometimes strong, sometimes weak. Bloating, gas, alternating constipation/looseness. Nervous-type digestion.' },
      { value: 'pitta', icon: '🔥', label: 'Tikshna Agni — Sharp/Intense', desc: 'Strong, sometimes excessive appetite. Digest quickly and thoroughly. Prone to acidity, heartburn, or loose stools. Get very irritable when meals are skipped.' },
      { value: 'kapha', icon: '🐢', label: 'Manda Agni — Slow', desc: 'Slow metabolism. Feel heavy or sluggish after meals. Low appetite especially in the morning. Food takes long to digest. Tendency toward weight gain.' },
    ],
  },
  {
    id: 'stool_pattern',
    question: 'How are your bowel habits normally? (Mala Pareeksha)',
    hint: 'Without dietary changes — your lifelong default. Mala (stool) quality is a primary Ayurvedic diagnostic indicator.',
    options: [
      { value: 'vata', icon: '🌵', label: 'Irregular & dry', desc: 'Tend toward constipation — dry, hard pellets, or with excessive gas. Frequency varies: sometimes twice a day, sometimes every 2 days. Incomplete feeling.' },
      { value: 'pitta', icon: '💧', label: 'Loose & urgent', desc: 'Soft, formed, sometimes loose or semi-formed. May have urgency. Regular once or twice daily. Occasionally burning sensation. Yellowish.' },
      { value: 'kapha', icon: '⚓', label: 'Slow & heavy', desc: 'Once daily, well-formed, heavy, and complete. Sometimes slow to move but consistent. Pale or mucus-coated occasionally. Feel satisfied after.' },
    ],
  },
  {
    id: 'eye_quality',
    question: 'How would you describe your eyes naturally? (Drik Pareeksha)',
    hint: 'Not after illness or screen fatigue — your everyday baseline eye quality',
    options: [
      { value: 'vata', icon: '👁️', label: 'Small & dry', desc: 'Small or narrow eyes, tend to be dry or gritty. Irregular blinking or occasional twitching. Gaze can be restless or darting. Appear slightly dull.' },
      { value: 'pitta', icon: '⚡', label: 'Sharp & penetrating', desc: 'Moderate size, bright, intense, and sharp. Tend toward redness or sensitivity to light when tired or stressed. Whites may have slight reddish tinge.' },
      { value: 'kapha', icon: '🌊', label: 'Large & lustrous', desc: 'Large, moist, calm, and pleasant. Steady, unhurried gaze. Clear whites. Naturally attractive eyes with good luster. Rarely dry.' },
    ],
  },
  {
    id: 'voice_quality',
    question: 'How would you describe your natural speaking voice? (Shabda Pareeksha)',
    hint: 'Your everyday voice — not during illness or presentation anxiety',
    options: [
      { value: 'vata', icon: '🌬️', label: 'Thin & quick', desc: 'Thin, somewhat low volume — can crack or go hoarse under stress. Speak quickly, may run out of breath mid-sentence. Voice trails off at ends.' },
      { value: 'pitta', icon: '🎯', label: 'Clear & sharp', desc: 'Clear, crisp, well-projected, and articulate. Commands attention naturally. Can become cutting or sharp-edged when under pressure or emotional.' },
      { value: 'kapha', icon: '🎵', label: 'Deep & resonant', desc: 'Deep, melodious, slow, and steady. Very pleasant to listen to. Rarely raises voice. Could be a singer — naturally musical quality. Projects without effort.' },
    ],
  },
  {
    id: 'nadi_rhythm',
    question: 'How would you describe your natural pulse? (Nadi Pareeksha — self-report)',
    hint: 'Feel your radial pulse (wrist, below thumb) lightly. Classical Nadi Pareeksha requires a Vaidya — this question provides a digital approximation only.',
    options: [
      { value: 'vata', icon: '🐍', label: 'Sarpa — snake-like', desc: 'Irregular, thin, thready, fast. Hard to feel — seems to disappear when you press slightly. Wriggles and varies. Classical Vata Nadi (Sarpa gati per Sharangadhara Samhita 1.7.3).' },
      { value: 'pitta', icon: '🐸', label: 'Manduka — frog-like', desc: 'Strong, bounding, sharp, moderate speed. Feels prominent and forceful. Jumps under fingers. Classical Pitta Nadi (Manduka gati).' },
      { value: 'kapha', icon: '🦢', label: 'Hamsa — swan-like', desc: 'Slow, broad, wave-like, steady. Feels deep and stable. Glides smoothly under light pressure. Classical Kapha Nadi (Hamsa gati).' },
    ],
  },
  {
    id: 'mutra_pattern',
    question: 'How is your urine normally? (Mutra Pareeksha)',
    hint: 'When well-hydrated and healthy — your default pattern. Mutra (urine) is a key Ashtavidha examination indicator.',
    options: [
      { value: 'vata', icon: '🌵', label: 'Scanty & variable', desc: 'Scanty in volume, variable frequency, sometimes dark or cloudy. Can get dehydrated easily. Occasional discomfort.' },
      { value: 'pitta', icon: '🌡️', label: 'Yellow & concentrated', desc: 'Yellow or amber coloured, often strong odour. May feel slight warmth or burning. Frequent in hot weather. Darkens with stress.' },
      { value: 'kapha', icon: '💧', label: 'Pale & copious', desc: 'Pale, large volume, infrequent but heavy. Occasionally turbid or slightly foamy. Rarely burning. Steady and predictable.' },
    ],
  },
  // ── Manasa Prakriti — Triguna assessment (Charaka Samhita Shareera Sthana 4) ─
  {
    id: 'motivation_source',
    question: 'What primarily drives you to act or make decisions?',
    hint: 'Your most honest motivation, not your ideal',
    options: [
      { value: 'satva', icon: '🌟', label: 'Purpose & wisdom', desc: 'I act from a genuine desire to grow, help others, and do what\'s right — even when hard.' },
      { value: 'rajas', icon: '🏆', label: 'Goals & recognition', desc: 'I act to achieve, succeed, and be seen for my accomplishments. Winning and status matter to me.' },
      { value: 'tamas', icon: '💤', label: 'Habit & inertia', desc: 'I often act from routine, comfort, or to avoid discomfort. Hard to change what I know.' },
    ],
  },
  {
    id: 'mind_clarity',
    question: 'How would you describe your typical mental state?',
    hint: 'On a regular day — not when you are at your best',
    options: [
      { value: 'satva', icon: '💎', label: 'Clear & focused', desc: 'Generally calm, clear-headed, and able to think through things without much mental noise.' },
      { value: 'rajas', icon: '⚡', label: 'Active & scattered', desc: 'Mind is usually busy, planning, thinking, evaluating. Hard to completely switch off.' },
      { value: 'tamas', icon: '🌫️', label: 'Heavy & foggy', desc: 'Often feel mentally dull, cloudy, or unmotivated. Heavy feeling that makes starting things hard.' },
    ],
  },
  {
    id: 'emotional_quality',
    question: 'When you feel a strong emotion, what characterises it most?',
    hint: 'Think of anger, fear, grief, or excitement',
    options: [
      { value: 'satva', icon: '🌊', label: 'Felt, processed, released', desc: 'I can feel emotions fully, reflect on them, and let them go without much residue.' },
      { value: 'rajas', icon: '🔥', label: 'Intense & lingering', desc: 'Emotions tend to be strong, sometimes overwhelming, and I replay situations mentally.' },
      { value: 'tamas', icon: '🌑', label: 'Suppressed & numb', desc: 'Emotions feel muted or stuck. I tend to avoid confronting them or feel emotionally flat.' },
    ],
  },
  {
    id: 'daily_discipline',
    question: 'How consistent are you with daily routines and self-care?',
    hint: 'Sleep, diet, exercise, spiritual or reflective practice',
    options: [
      { value: 'satva', icon: '🌅', label: 'Consistent & disciplined', desc: 'Follow a fairly regular routine. Make time for sleep, meals, and some form of reflection or practice.' },
      { value: 'rajas', icon: '📱', label: 'Inconsistent & driven', desc: 'Very active but irregular — sometimes extremely disciplined, other times completely off-track due to busyness.' },
      { value: 'tamas', icon: '🛋️', label: 'Irregular & passive', desc: 'Struggle to maintain routines. Days feel unstructured. Self-care habits are hard to sustain.' },
    ],
  },
  {
    id: 'conflict_approach',
    question: 'When you face a conflict or difficult conversation:',
    hint: 'Your first natural impulse',
    options: [
      { value: 'satva', icon: '🕊️', label: 'Seek understanding', desc: 'Try to understand both sides, stay calm, and look for a fair resolution.' },
      { value: 'rajas', icon: '⚔️', label: 'Assert & argue', desc: 'Feel the urge to defend my position, argue, or ensure I am not wronged.' },
      { value: 'tamas', icon: '🐚', label: 'Avoid & withdraw', desc: 'Prefer to avoid the conflict entirely, go silent, or delay dealing with it.' },
    ],
  },
]

// ── Symptom clusters — Vikriti indicators ─────────────────────────────────────
const SYMPTOM_CLUSTERS = [
  { id: 'anxiety_worry', icon: '🌀', label: 'Anxiety or worry', desc: 'Racing thoughts, nervousness, or feeling overwhelmed' },
  { id: 'dry_skin_constipation', icon: '🌵', label: 'Dryness or constipation', desc: 'Dry skin, lips, constipation, or cracking joints' },
  { id: 'trouble_sleeping', icon: '🌙', label: 'Trouble sleeping', desc: 'Insomnia, light sleep, or feeling scattered/ungrounded' },
  { id: 'bloating_gas', icon: '💨', label: 'Bloating or gas', desc: 'Irregular digestion, bloating, gas, or alternating bowels' },
  { id: 'heartburn_acidity', icon: '🔥', label: 'Acidity or inflammation', desc: 'Heartburn, acid reflux, or stomach inflammation' },
  { id: 'skin_rashes', icon: '🌡️', label: 'Skin flare-ups', desc: 'Rashes, acne, or feeling consistently overheated' },
  { id: 'irritability', icon: '⚡', label: 'Irritability or frustration', desc: 'Impatience, anger, or being overly critical' },
  { id: 'weight_gain', icon: '🏔️', label: 'Weight or sluggishness', desc: 'Weight gain, water retention, or feeling heavy' },
  { id: 'low_energy', icon: '😶', label: 'Low energy or motivation', desc: 'Lethargy, lack of motivation, or mild depression' },
  { id: 'congestion', icon: '🌫️', label: 'Congestion or mucus', desc: 'Sinus congestion, excess mucus, or slow metabolism' },
  { id: 'joint_stiffness', icon: '🦴', label: 'Joint or body aches', desc: 'Stiffness, dryness in joints, or general body aches' },
  { id: 'brain_fog', icon: '🌁', label: 'Brain fog', desc: 'Difficulty concentrating, mental cloudiness, or forgetfulness' },
  { id: 'coated_tongue_ama', icon: '👅', label: 'Coated tongue', desc: 'White/yellow coating on tongue in the morning — classical Ama (Jihva Pareeksha)' },
  { id: 'morning_heaviness', icon: '🪨', label: 'Morning heaviness', desc: 'Body feels heavy, dull, or unrefreshed despite adequate sleep — Ama in channels' },
  { id: 'feeling_balanced', icon: '✨', label: 'Feeling balanced', desc: 'No major complaints — generally feeling well' },
]

const LOADING_STEPS = [
  'Analyzing your physical constitution…',
  'Reading your mental and behavioral patterns…',
  'Cross-referencing with classical Ayurvedic texts…',
  'Mapping Prakriti and current Vikriti state…',
]

const CLARIFY_QUESTIONS = [
  {
    id: 'chronic_pattern',
    question: 'Over the last year or more (not just recently), your most persistent pattern has been:',
    hint: 'Ignore temporary phases — think about your consistent baseline',
    options: [
      { value: 'vata', icon: '🌊', label: 'Irregular & anxious', desc: 'Variable energy, scattered focus, anxious or unsettled as a baseline state.' },
      { value: 'pitta', icon: '🔥', label: 'Intense & driven', desc: 'Strong drive, tendency toward inflammation/acidity, sharp emotional responses.' },
      { value: 'kapha', icon: '🌳', label: 'Stable & slow', desc: 'Consistent but slow pace, steady mood, tendency toward heaviness or congestion.' },
    ],
  },
  {
    id: 'recovery_style',
    question: 'When you get sick or run down, you typically:',
    hint: 'Your natural recovery pattern — not what you do deliberately',
    options: [
      { value: 'vata', icon: '🌀', label: 'Recover erratically', desc: 'Get sick fast, symptoms are variable and shifting. Hard to predict. Anxiety spikes during illness.' },
      { value: 'pitta', icon: '⚡', label: 'Fight it intensely', desc: 'Fever, inflammation, or sharp symptoms. Recover relatively fast when you rest, but struggle to slow down.' },
      { value: 'kapha', icon: '🐢', label: 'Get stuck slowly', desc: 'Congestion, heaviness, slow onset. Recovery takes longer but eventual. Tend toward mucus and fatigue.' },
    ],
  },
]

const DOSHA_COLORS = {
  vata: 'var(--vata-color, #818cf8)',
  pitta: 'var(--pitta-color, #fb923c)',
  kapha: 'var(--kapha-color, #34d399)',
  satva: '#10b981',
  rajas: '#f59e0b',
  tamas: '#6366f1',
}

const DOSHA_LABELS = { vata: 'Vata', pitta: 'Pitta', kapha: 'Kapha', satva: 'Satva', rajas: 'Rajas', tamas: 'Tamas' }
const DOSHA_EMOJIS = { vata: '💨', pitta: '🔥', kapha: '🌊' }

const DOSHA_GUNAS = {
  vata:  ['Ruksha (dry)', 'Laghu (light)', 'Sheeta (cold)', 'Khara (rough)', 'Chala (mobile)'],
  pitta: ['Ushna (hot)', 'Tikshna (sharp)', 'Sara (flowing)', 'Laghu (light)', 'Snigdha (glossy)'],
  kapha: ['Guru (heavy)', 'Manda (slow)', 'Snigdha (oily)', 'Sthira (stable)', 'Sheeta (cold)'],
}

const CHARAKA_REFS = {
  vata:      'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana',
  pitta:     'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana',
  kapha:     'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana',
  tridoshic: 'Ashtanga Hridayam, Sharira Sthana 3 — Sama Tridosha type',
}

const CLASSICAL_TYPE_DISPLAY = {
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

const AMA_COLORS = {
  none:     'var(--ayura-teal, #2dd4bf)',
  low:      'var(--ayura-teal, #2dd4bf)',
  mild:     'var(--ayura-amber, #f59e0b)',
  moderate: '#fb923c',
  high:     '#f87171',
}

const stepVariants = {
  enter: (d) => ({ x: d > 0 ? 56 : -56, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (d) => ({ x: d > 0 ? -56 : 56, opacity: 0 }),
}

function qualitativeLabel(pct) {
  if (pct >= 66) return { text: 'Dominant', color: 'var(--ayura-teal)' }
  if (pct >= 46) return { text: 'Elevated', color: 'var(--ayura-amber)' }
  if (pct >= 26) return { text: 'Moderate', color: 'var(--text-secondary)' }
  return { text: 'Low', color: 'var(--text-secondary)' }
}

function SpectrumSection({ title, scores, highlightDominant }) {
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1])
  return (
    <div className="da-spectrum-section">
      <h4 className="da-spectrum-title">{title}</h4>
      {sorted.map(([dosha, pct]) => {
        const ql = qualitativeLabel(pct)
        return (
          <div key={dosha} className={`da-dosha-bar-row ${highlightDominant && dosha === sorted[0][0] ? 'dominant' : ''}`}>
            <span className="da-dosha-bar-label" style={{ color: DOSHA_COLORS[dosha] }}>
              {DOSHA_LABELS[dosha]}
            </span>
            <div className="da-dosha-bar-track">
              <motion.div
                className="da-dosha-bar-fill"
                style={{ background: DOSHA_COLORS[dosha] }}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
            <div className="da-dosha-bar-right">
              <span className="da-dosha-bar-pct">{pct}%</span>
              <span className="da-dosha-bar-qual" style={{ color: ql.color }}>{ql.text}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

const MANASA_TRAIT_IDS = ['motivation_source', 'mind_clarity', 'emotional_quality', 'daily_discipline', 'conflict_approach']

function detectContradiction(traits) {
  const PHYSICAL_TRAITS = ['body_frame', 'skin', 'digestion', 'sleep', 'temperature', 'hair', 'energy']
  const MENTAL_TRAITS = ['stress_response', 'memory', 'decision_making', 'speech', 'emotional_nature']
  const doshTraits = Object.fromEntries(Object.entries(traits).filter(([k]) => !MANASA_TRAIT_IDS.includes(k)))
  const physCounts = { vata: 0, pitta: 0, kapha: 0 }
  const mentCounts = { vata: 0, pitta: 0, kapha: 0 }
  PHYSICAL_TRAITS.forEach(t => { if (doshTraits[t]) physCounts[doshTraits[t]]++ })
  MENTAL_TRAITS.forEach(t => { if (doshTraits[t]) mentCounts[doshTraits[t]]++ })
  const physDom = Object.entries(physCounts).sort((a, b) => b[1] - a[1])[0]?.[0]
  const mentDom = Object.entries(mentCounts).sort((a, b) => b[1] - a[1])[0]?.[0]
  return physDom && mentDom && physDom !== mentDom
}

const TRAIT_PRIORITY_LABEL = {
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

const TRAIT_DISPLAY_NAMES = {
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

function TraitBreakdown({ traits }) {
  if (!traits || Object.keys(traits).length === 0) return null
  const sortOrder = ['Primary', 'Strong', 'Moderate', 'Manasa', 'Secondary']
  const entries = Object.entries(traits)
    .filter(([, v]) => v)
    .sort((a, b) => {
      const ai = sortOrder.indexOf(TRAIT_PRIORITY_LABEL[a[0]] || 'Secondary')
      const bi = sortOrder.indexOf(TRAIT_PRIORITY_LABEL[b[0]] || 'Secondary')
      return (ai === -1 ? sortOrder.length : ai) - (bi === -1 ? sortOrder.length : bi)
    })
  return (
    <div className="da-trait-breakdown">
      <span className="da-breakdown-title">What drove your result</span>
      <div className="da-breakdown-rows">
        {entries.map(([trait, dosha]) => (
          <div key={trait} className="da-breakdown-row">
            <span className="da-breakdown-trait">{TRAIT_DISPLAY_NAMES[trait] || trait}</span>
            <span className="da-breakdown-arrow">→</span>
            <span className="da-breakdown-dosha" style={{ color: DOSHA_COLORS[dosha] || 'var(--text-secondary)' }}>
              {DOSHA_LABELS[dosha] || dosha}
            </span>
            <span className="da-breakdown-priority">{TRAIT_PRIORITY_LABEL[trait] || ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function TongueUploader({ onResult }) {
  const [state, setState] = useState('idle') // idle | selected | uploading | done | error
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const [errMsg, setErrMsg] = useState('')
  const inputRef = useRef(null)

  function handleFile(f) {
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setState('selected')
    setErrMsg('')
  }

  async function upload() {
    if (!file) return
    setState('uploading')
    try {
      const res = await profileAPI.tongueAssessment(file)
      onResult(res.data)
      setState('done')
    } catch (e) {
      setErrMsg(e.response?.data?.detail || 'Upload failed. Please try again.')
      setState('error')
    }
  }

  if (state === 'done') {
    return (
      <div className="da-tongue-done">
        <span>✅</span> Tongue analysis applied to your Vikriti scores.
      </div>
    )
  }

  return (
    <div className="da-tongue-uploader">
      <span className="da-tongue-label">Optional: Tongue Analysis (Jihva Pareeksha)</span>
      <span className="da-tongue-hint">Upload a clear photo of your tongue in natural light — GPT-4o will read Ayurvedic signals.</span>
      {preview && (
        <div className="da-tongue-preview-wrap">
          <img src={preview} alt="Tongue preview" className="da-tongue-preview" />
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {state === 'idle' && (
        <button type="button" className="btn btn-secondary" onClick={() => inputRef.current?.click()}>
          Choose Photo
        </button>
      )}
      {state === 'selected' && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" className="btn btn-primary" onClick={upload}>
            Analyse Tongue
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => inputRef.current?.click()}>
            Change
          </button>
        </div>
      )}
      {state === 'uploading' && <span className="da-tongue-hint">Analysing…</span>}
      {state === 'error' && (
        <>
          <span style={{ color: 'var(--color-error, #f87171)', fontSize: '0.85rem' }}>{errMsg}</span>
          <button type="button" className="btn btn-secondary" onClick={() => setState('selected')}>Retry</button>
        </>
      )}
    </div>
  )
}

export default function DoshaQuiz() {
  const [phase, setPhase] = useState('traits') // traits | symptoms | loading | clarify | confirm | result
  const [traitIndex, setTraitIndex] = useState(0)
  const [direction, setDirection] = useState(1)
  const [traits, setTraits] = useState({})
  const [symptoms, setSymptoms] = useState([])
  const [loadingStep, setLoadingStep] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [rejectedSignals, setRejectedSignals] = useState([])
  const [clarifyAnswers, setClarifyAnswers] = useState({})
  const { updateProfile, user } = useAuth()
  const navigate = useNavigate()

  const currentTraitQ = TRAIT_QUESTIONS[traitIndex]
  const traitProgress = (traitIndex / TRAIT_QUESTIONS.length) * 100

  // Cycle loading messages during assessment
  useEffect(() => {
    if (phase !== 'loading') return
    const interval = setInterval(() => {
      setLoadingStep((s) => (s + 1) % LOADING_STEPS.length)
    }, 1500)
    return () => clearInterval(interval)
  }, [phase])

  function selectTrait(value) {
    const updated = { ...traits, [currentTraitQ.id]: value }
    setTraits(updated)
    if (traitIndex < TRAIT_QUESTIONS.length - 1) {
      setTimeout(() => {
        setDirection(1)
        setTraitIndex((i) => i + 1)
      }, 220)
    } else {
      setTimeout(() => setPhase('symptoms'), 220)
    }
  }

  function goBackTrait() {
    if (traitIndex > 0) {
      setDirection(-1)
      setTraitIndex((i) => i - 1)
    }
  }

  function toggleSymptom(id) {
    setSymptoms((prev) => {
      if (id === 'feeling_balanced') return ['feeling_balanced']
      const withoutBalanced = prev.filter((s) => s !== 'feeling_balanced')
      return withoutBalanced.includes(id)
        ? withoutBalanced.filter((s) => s !== id)
        : [...withoutBalanced, id]
    })
  }

  async function runAssessment() {
    setError('')
    setPhase('loading')
    setLoadingStep(0)
    try {
      const dehaTraits = {}
      const manasaTraits = {}
      for (const [k, v] of Object.entries(traits)) {
        if (MANASA_TRAIT_IDS.includes(k)) manasaTraits[k] = v
        else dehaTraits[k] = v
      }
      const response = await profileAPI.doshaAssessment({
        physical_traits: dehaTraits,
        current_symptoms: symptoms,
        manasa_traits: Object.keys(manasaTraits).length > 0 ? manasaTraits : undefined,
      })
      const assessResult = response.data
      setResult(assessResult)
      await updateProfile({})
      // The API returns dosha_confidence as a 0-100 score and dosha_contradictions
      // as a list — derive the qualitative state from those (not the non-existent
      // `confidence`/`contradictions` fields). When the read is shaky — conflicting
      // trait groups or low confidence — we ask two clarifying follow-ups rather
      // than commit to an uncertain constitution.
      const isLowConfidence = (assessResult.dosha_confidence ?? 0) < 45
      const hasContradiction = detectContradiction(traits) || (assessResult.dosha_contradictions?.length > 0)
      if (hasContradiction || isLowConfidence) {
        setPhase('clarify')
      } else {
        setPhase('confirm')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Assessment failed. Please try again.')
      setPhase('symptoms')
    }
  }

  function retake() {
    setPhase('traits')
    setTraitIndex(0)
    setDirection(1)
    setTraits({})
    setSymptoms([])
    setResult(null)
    setError('')
    setRejectedSignals([])
    setClarifyAnswers({})
  }

  // ── Clarify phase ────────────────────────────────────────────────────────────
  if (phase === 'clarify') {
    const allAnswered = CLARIFY_QUESTIONS.every(q => clarifyAnswers[q.id])
    return (
      <div className="da-root">
        <Helmet><title>Clarify Your Profile | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <div className="da-orb da-orb-b" />
        <motion.div
          className="da-shell"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="da-clarify-header">
            <span className="da-clarify-icon">🔍</span>
            <h2 className="da-clarify-title">A couple of follow-up questions</h2>
            <p className="da-clarify-sub">
              Your physical and mental signals show some contrast — these two questions help us resolve the pattern accurately.
            </p>
          </div>

          {CLARIFY_QUESTIONS.map((q) => (
            <div key={q.id} className="da-clarify-section">
              <h3 className="da-question">{q.question}</h3>
              <p className="da-hint">{q.hint}</p>
              <div className="da-trait-options">
                {q.options.map(opt => {
                  const selected = clarifyAnswers[q.id] === opt.value
                  return (
                    <motion.button
                      key={opt.value}
                      type="button"
                      className={`da-trait-card ${selected ? 'selected' : ''}`}
                      onClick={() => setClarifyAnswers(prev => ({ ...prev, [q.id]: opt.value }))}
                      whileHover={{ scale: 1.015 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <span className="da-trait-icon">{opt.icon}</span>
                      <span className="da-trait-label">{opt.label}</span>
                      <span className="da-trait-desc">{opt.desc}</span>
                      {selected && <span className="da-trait-check">✓</span>}
                    </motion.button>
                  )
                })}
              </div>
            </div>
          ))}

          <div className="da-confirm-actions" style={{ marginTop: 24 }}>
            <motion.button
              className="btn btn-primary btn-lg"
              disabled={!allAnswered}
              onClick={() => {
                if (result) {
                  const boost = { vata: 0, pitta: 0, kapha: 0 }
                  Object.values(clarifyAnswers).forEach(v => { if (boost[v] !== undefined) boost[v] += 8 })
                  const newVikriti = { ...result.vikriti_scores }
                  Object.entries(boost).forEach(([d, b]) => {
                    newVikriti[d] = Math.min(70, (newVikriti[d] || 33) + b)
                  })
                  const total = Object.values(newVikriti).reduce((s, v) => s + v, 0) || 1
                  const norm = Object.fromEntries(Object.entries(newVikriti).map(([d, v]) => [d, Math.round(v / total * 100)]))
                  const diff = 100 - Object.values(norm).reduce((s, v) => s + v, 0)
                  if (diff !== 0) norm[Object.entries(norm).sort((a, b) => b[1] - a[1])[0][0]] += diff
                  setResult(prev => ({
                    ...prev,
                    vikriti_scores: norm,
                    vikriti_dominant: Object.entries(norm).sort((a, b) => b[1] - a[1])[0][0],
                    dosha_confidence: Math.min(85, (prev.dosha_confidence || 35) + 15),
                  }))
                }
                setPhase('confirm')
              }}
              whileTap={{ scale: 0.97 }}
            >
              Continue →
            </motion.button>
            <motion.button
              className="btn btn-secondary"
              onClick={() => setPhase('confirm')}
              whileTap={{ scale: 0.97 }}
            >
              Skip — use initial result
            </motion.button>
          </div>
        </motion.div>
      </div>
    )
  }

  // ── Loading phase ────────────────────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <div className="da-root">
        <Helmet><title>Analyzing Your Dosha | Ayura AI</title></Helmet>
        <Suspense fallback={null}><LazyParticleField count={30} spread={18} style={{ opacity: 0.2 }} /></Suspense>
        <div className="da-shell da-shell-loading">
          <div className="da-loading-orb">
            <div className="da-loading-ring" />
            <div className="da-loading-ring da-loading-ring-2" />
            <span className="da-loading-icon">🌿</span>
          </div>
          <AnimatePresence mode="wait">
            <motion.p
              key={loadingStep}
              className="da-loading-text"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.4 }}
            >
              {LOADING_STEPS[loadingStep]}
            </motion.p>
          </AnimatePresence>
          <p className="da-loading-sub">Scoring your constitution with a deterministic Ashtavidha Pareeksha engine — AI writes the explanation.</p>
        </div>
      </div>
    )
  }

  // ── Confirm phase ────────────────────────────────────────────────────────────
  if (phase === 'confirm' && result) {
    const vikritiDominant = result.vikriti_dominant
    const keySignals = result.dosha_key_signals || []
    const constitutionType = result.dosha_constitution_type || result.dominant_dosha || ''

    return (
      <div className="da-root">
        <Helmet><title>Confirm Your Results | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <Suspense fallback={null}><LazyParticleField count={30} spread={18} style={{ opacity: 0.2 }} /></Suspense>
        <motion.div
          className="da-shell"
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="da-confirm-header">
            <span className="da-confirm-icon">🌿</span>
            <h2 className="da-confirm-title">Your Vaidya Assessment</h2>
            <p className="da-confirm-sub">
              Based on your {TRAIT_QUESTIONS.length} constitutional traits (Shareera + Manas Prakriti) and current symptoms:
            </p>
          </div>

          <div className="da-confirm-constitution">
            <span style={{ opacity: 0.7, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Constitution</span>
            <strong style={{ fontSize: '1.1rem' }}>
              {constitutionType.replace(/_/g, '–').replace(/\b\w/g, (c) => c.toUpperCase())}
            </strong>
          </div>

          {vikritiDominant && (
            <div className="da-confirm-imbalance" style={{ borderColor: DOSHA_COLORS[vikritiDominant] }}>
              <span style={{ fontSize: '1.5rem' }}>{DOSHA_EMOJIS[vikritiDominant]}</span>
              <div>
                <span style={{ opacity: 0.7, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Primary imbalance right now</span>
                <strong style={{ display: 'block', color: DOSHA_COLORS[vikritiDominant], fontSize: '1.05rem' }}>
                  {DOSHA_LABELS[vikritiDominant]} excess
                </strong>
              </div>
            </div>
          )}

          {keySignals.length > 0 && (
            <div className="da-confirm-signals">
              <span className="da-confirm-signals-label">Tap to dismiss signals that don't apply to you</span>
              <div className="da-confirm-chips">
                {keySignals.slice(0, 6).map((sig, i) => {
                  const rejected = rejectedSignals.includes(sig)
                  return (
                    <motion.button
                      key={i}
                      type="button"
                      className={`da-confirm-chip${rejected ? ' rejected' : ''}`}
                      onClick={() => setRejectedSignals(prev =>
                        rejected ? prev.filter(s => s !== sig) : [...prev, sig]
                      )}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.05 + i * 0.06 }}
                    >
                      {rejected ? '✕' : '✓'} {sig}
                    </motion.button>
                  )
                })}
              </div>
              {rejectedSignals.length > 0 && (
                <p className="da-confirm-adjust-note">
                  {rejectedSignals.length} signal{rejectedSignals.length > 1 ? 's' : ''} dismissed — scores will adjust when you confirm.
                </p>
              )}
            </div>
          )}

          <div className="da-confirm-actions">
            <motion.button
              className="btn btn-primary btn-lg"
              onClick={() => {
                if (rejectedSignals.length > 0 && result) {
                  const vikriti = { ...result.vikriti_scores }
                  const dominant = result.vikriti_dominant
                  const reduction = Math.min(rejectedSignals.length * 4, 15)
                  if (dominant && vikriti[dominant] !== undefined) {
                    vikriti[dominant] = Math.max(10, vikriti[dominant] - reduction)
                    const others = Object.keys(vikriti).filter(d => d !== dominant)
                    const perOther = Math.floor(reduction / others.length)
                    others.forEach(d => { vikriti[d] = (vikriti[d] || 0) + perOther })
                    const total = Object.values(vikriti).reduce((a, b) => a + b, 0)
                    Object.keys(vikriti).forEach(d => { vikriti[d] = Math.round(vikriti[d] / total * 100) })
                    const diff = 100 - Object.values(vikriti).reduce((a, b) => a + b, 0)
                    if (diff !== 0) vikriti[dominant] += diff
                    setResult(prev => ({
                      ...prev,
                      vikriti_scores: vikriti,
                      vikriti_dominant: Object.entries(vikriti).sort((a, b) => b[1] - a[1])[0][0],
                      dosha_key_signals: (prev?.dosha_key_signals || []).filter(s => !rejectedSignals.includes(s)),
                    }))
                  }
                }
                setPhase('result')
              }}
              whileTap={{ scale: 0.97 }}
            >
              Yes, this looks right →
            </motion.button>
            <motion.button
              className="btn btn-secondary"
              onClick={retake}
              whileTap={{ scale: 0.97 }}
            >
              Not quite — retake
            </motion.button>
          </div>
        </motion.div>
      </div>
    )
  }

  // ── Result phase ─────────────────────────────────────────────────────────────
  if (phase === 'result' && result) {
    const prakriti = result.dosha_scores || {}
    const vikriti = result.vikriti_scores || {}
    const vikritiDominant = result.vikriti_dominant
    const constitutionType = result.dosha_constitution_type || result.dominant_dosha || ''
    const explanation = result.dosha_explanation
    const immediateFocus = result.dosha_immediate_focus
    const keySignals = result.dosha_key_signals || []
    const confidence = result.dosha_confidence >= 70 ? 'high' : result.dosha_confidence >= 45 ? 'medium' : 'low'

    function handleTongueResult(tongueData) {
      setResult((r) => ({
        ...r,
        vikriti_scores: tongueData.vikriti_scores,
        vikriti_dominant: tongueData.vikriti_dominant,
      }))
    }

    return (
      <div className="da-root">
        <Helmet><title>Your Ayurvedic Profile | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <div className="da-orb da-orb-b" />
        <Suspense fallback={null}><LazyParticleField count={40} spread={18} style={{ opacity: 0.25 }} /></Suspense>

        <motion.div
          className="da-shell"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          {user?.prakriti_locked && (
            <div className="da-prakriti-lock-notice">
              <strong>Prakriti already determined.</strong> Your constitutional type is set for life — only your Vikriti (current imbalance) has been updated from this session.
            </div>
          )}
          <div className="da-result-header">
            <h1 className="da-result-title">Your Ayurvedic Profile</h1>
            <span className="da-constitution-badge">
              {CLASSICAL_TYPE_DISPLAY[result.prakriti_classical_type || constitutionType] ||
               constitutionType.replace(/_/g, '-').replace(/\b\w/g, c => c.toUpperCase()) + ' Prakriti'}
            </span>
          </div>

          <div className="da-result-dual">
            <SpectrumSection
              title="Constitution (Prakriti)"
              scores={prakriti}
              highlightDominant={false}
            />
            <SpectrumSection
              title="Current Imbalance (Vikriti)"
              scores={vikriti}
              highlightDominant={true}
            />
          </div>

          <TraitBreakdown traits={traits} />

          {/* ── Guna Profile ─────────────────────────────────── */}
          {(() => {
            const gunas = result.primary_gunas?.length
              ? result.primary_gunas
              : (DOSHA_GUNAS[result.dominant_dosha || result.vikriti_dominant] || [])
            if (!gunas.length) return null
            return (
              <div className="da-guna-profile">
                <span className="da-guna-title">Your Dominant Gunas (Qualities)</span>
                <div className="da-guna-tags">
                  {gunas.map((g, i) => (
                    <span key={i} className="da-guna-tag">{g}</span>
                  ))}
                </div>
                <span className="da-guna-ref">Per Charaka Sutrasthana 1.59–61 (Vimshatika Guna)</span>
              </div>
            )
          })()}

          {/* ── Manas Prakriti ─────────────────────────────────── */}
          {result.manasa_prakriti && typeof result.manasa_prakriti === 'object' ? (
            <div className="da-manas-box">
              <span className="da-manas-label">Manasa Prakriti — Triguna Balance</span>
              <span className="da-manas-ref">Charaka Samhita Shareera Sthana 4 — Triguna Prakriti</span>
              <div className="da-manas-guna-badge" style={{ color: DOSHA_COLORS[result.manasa_prakriti.dominant_guna] }}>
                {result.manasa_prakriti.label} ({result.manasa_prakriti.dominant_guna?.charAt(0).toUpperCase() + result.manasa_prakriti.dominant_guna?.slice(1)} dominant)
              </div>
              {['satva', 'rajas', 'tamas'].map(guna => (
                <div key={guna} className="da-dosha-bar-row">
                  <span className="da-dosha-bar-label" style={{ color: DOSHA_COLORS[guna] }}>
                    {guna.charAt(0).toUpperCase() + guna.slice(1)}
                  </span>
                  <div className="da-dosha-bar-track">
                    <motion.div
                      className="da-dosha-bar-fill"
                      style={{ background: DOSHA_COLORS[guna] }}
                      initial={{ width: 0 }}
                      animate={{ width: `${result.manasa_prakriti[guna] || 0}%` }}
                      transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                  <span className="da-dosha-bar-pct">{result.manasa_prakriti[guna] || 0}%</span>
                </div>
              ))}
              <p className="da-manas-text">{result.manasa_prakriti.description}</p>
            </div>
          ) : result.manas_prakriti ? (
            <div className="da-manas-box">
              <span className="da-manas-label">Manas Prakriti (Mental Constitution)</span>
              <p className="da-manas-text">{result.manas_prakriti}</p>
            </div>
          ) : null}

          {/* ── Ama Score ─────────────────────────────────────────── */}
          {result.ama_indicator && result.ama_indicator !== 'none' && (
            <div className="da-ama-row">
              <span className="da-ama-label">Ama Level</span>
              <span
                className="da-ama-badge"
                style={{ color: AMA_COLORS[result.ama_indicator] || AMA_COLORS.mild }}
              >
                {result.ama_indicator.charAt(0).toUpperCase() + result.ama_indicator.slice(1)}
              </span>
              <span className="da-ama-hint">
                {result.ama_indicator === 'high'
                  ? '— Digestive toxins significantly indicated. Prioritise Agni kindling and light diet.'
                  : result.ama_indicator === 'moderate'
                  ? '— Some Ama accumulation. Support digestion and avoid heavy foods.'
                  : '— Mild Ama present. Monitor with weekly check-ins.'}
              </span>
            </div>
          )}

          {result.dosha_contradictions?.length > 0 && (
            <div className="da-contradiction-note">
              <span className="da-contradiction-icon">⚡</span>
              <div>
                <strong>Mixed signals detected</strong>
                <p>{result.dosha_contradictions[0]}</p>
                <p className="da-contradiction-hint">Weekly check-ins will resolve this over time as more data accumulates.</p>
              </div>
            </div>
          )}

          {vikritiDominant && (
            <div className="da-vikriti-note" style={{ borderColor: DOSHA_COLORS[vikritiDominant] }}>
              <span className="da-vikriti-icon" style={{ color: DOSHA_COLORS[vikritiDominant] }}>⚠</span>
              <span>Your current <strong style={{ color: DOSHA_COLORS[vikritiDominant] }}>{DOSHA_LABELS[vikritiDominant]}</strong> imbalance is the primary focus for your wellness plans.</span>
            </div>
          )}

          {explanation && (
            <div className="da-explanation-box">
              <p className="da-explanation-text">{explanation}</p>
            </div>
          )}

          {immediateFocus && (
            <div className="da-focus-box">
              <span className="da-focus-label">What your plans will target</span>
              <p className="da-focus-text">{immediateFocus}</p>
            </div>
          )}

          {keySignals.length > 0 && (
            <div className="da-key-signals">
              <span className="da-signals-label">Key signals from your assessment</span>
              <ul className="da-signals-list">
                {keySignals.map((sig, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 + i * 0.1 }}
                  >
                    {sig}
                  </motion.li>
                ))}
              </ul>
            </div>
          )}

          <TongueUploader onResult={handleTongueResult} />

          <div className="da-confidence-row">
            <span className="da-confidence-label">Assessment confidence</span>
            <span className={`da-confidence-badge da-confidence-${confidence}`}>
              {confidence.charAt(0).toUpperCase() + confidence.slice(1)}
            </span>
          </div>

          <div className="da-classical-ref">
            <span className="da-classical-ref-icon">📜</span>
            <span>
              {CHARAKA_REFS[result.prakriti_classical_type] || CHARAKA_REFS[result.dominant_dosha] || 'Charaka Samhita, Vimana Sthana 8 — Prakriti Prakarana'}
            </span>
          </div>

          <div className="da-result-actions">
            <motion.button
              className="btn btn-primary btn-lg"
              onClick={() => navigate('/dashboard')}
              whileTap={{ scale: 0.97 }}
            >
              Generate My Plans →
            </motion.button>
            <motion.button
              className="btn btn-secondary"
              onClick={retake}
              whileTap={{ scale: 0.97 }}
            >
              Retake Assessment
            </motion.button>
          </div>

          <div className="da-disclaimer-block">
            <p className="da-disclaimer">
              This assessment follows the CCRAS (Central Council for Research in Ayurvedic Sciences) Prakriti evaluation framework, adapted for digital self-screening. It is a wellness guidance tool — not a clinical diagnosis or a replacement for examination by a qualified Vaidya.
            </p>
            <p className="da-disclaimer da-disclaimer-nadi">
              Note: Classical Nadi Pareeksha (pulse examination) requires physical assessment by a qualified Ayurvedic practitioner and cannot be fully replicated through self-report. For definitive Prakriti determination, consult a trained Vaidya.
            </p>
          </div>
        </motion.div>
      </div>
    )
  }

  // ── Symptom phase ────────────────────────────────────────────────────────────
  if (phase === 'symptoms') {
    return (
      <div className="da-root">
        <Helmet><title>Current Symptoms | Ayura AI</title></Helmet>
        <div className="da-orb da-orb-a" />
        <Suspense fallback={null}><LazyParticleField count={25} spread={20} style={{ opacity: 0.2 }} /></Suspense>

        <motion.div
          className="da-shell"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="da-phase-header">
            <button type="button" className="btn btn-secondary da-back-btn" onClick={() => { setPhase('traits'); setTraitIndex(TRAIT_QUESTIONS.length - 1) }}>← Back</button>
            <div className="da-phase-steps">
              <span className="da-step done">Physical Traits</span>
              <span className="da-step-sep">›</span>
              <span className="da-step active">Current State</span>
            </div>
          </div>

          <div className="da-symptom-intro">
            <h2 className="da-question">How are you feeling right now?</h2>
            <p className="da-hint">Select everything that applies over the past few weeks. Pick as many as you like — or choose "Feeling balanced" if things are good.</p>
          </div>

          <div className="da-symptom-grid">
            {SYMPTOM_CLUSTERS.map((cluster) => {
              const selected = symptoms.includes(cluster.id)
              return (
                <motion.button
                  key={cluster.id}
                  type="button"
                  className={`da-symptom-chip ${selected ? 'selected' : ''}`}
                  onClick={() => toggleSymptom(cluster.id)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                >
                  <span className="da-chip-icon">{cluster.icon}</span>
                  <span className="da-chip-label">{cluster.label}</span>
                  <span className="da-chip-desc">{cluster.desc}</span>
                  {selected && <span className="da-chip-check">✓</span>}
                </motion.button>
              )
            })}
          </div>

          {error && (
            <motion.div className="da-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              {error}
            </motion.div>
          )}

          <div className="da-symptom-footer">
            <motion.button
              type="button"
              className="btn btn-primary btn-lg"
              onClick={runAssessment}
              whileTap={{ scale: 0.97 }}
            >
              Assess My Dosha →
            </motion.button>
            <p className="da-symptom-note">Your answers are scored by a deterministic classical Ayurvedic engine — AI only writes your personalised explanation.</p>
          </div>
        </motion.div>
      </div>
    )
  }

  // ── Traits phase ─────────────────────────────────────────────────────────────
  return (
    <div className="da-root">
      <Helmet><title>Dosha Assessment | Ayura AI</title></Helmet>
      <div className="da-orb da-orb-a" />
      <div className="da-orb da-orb-b" />
      <Suspense fallback={null}><LazyParticleField count={25} spread={20} style={{ opacity: 0.2 }} /></Suspense>

      <motion.div
        className="da-shell"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="da-phase-header">
          <button
            type="button"
            className="btn btn-secondary da-back-btn"
            onClick={traitIndex > 0 ? goBackTrait : () => navigate(-1)}
          >
            ← Back
          </button>
          <div className="da-phase-steps">
            <span className="da-step active">Physical Traits</span>
            <span className="da-step-sep">›</span>
            <span className="da-step">Current State</span>
          </div>
        </div>

        <div className="da-progress-track">
          <motion.div
            className="da-progress-fill"
            animate={{ width: `${traitProgress}%` }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        <p className="da-progress-label">Question {traitIndex + 1} of {TRAIT_QUESTIONS.length}</p>

        <div className="da-trait-card-area">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={traitIndex}
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <h2 className="da-question">{currentTraitQ.question}</h2>
              <p className="da-hint">{currentTraitQ.hint}</p>
              <div className={`da-trait-options${currentTraitQ.options.length === 4 ? ' da-trait-options-4' : ''}`}>
                {currentTraitQ.options.map((opt) => {
                  const selected = traits[currentTraitQ.id] === opt.value
                  return (
                    <motion.button
                      key={opt.value}
                      type="button"
                      className={`da-trait-card ${selected ? 'selected' : ''}`}
                      onClick={() => selectTrait(opt.value)}
                      whileHover={{ scale: 1.015 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <span className="da-trait-icon">{opt.icon}</span>
                      <span className="da-trait-label">{opt.label}</span>
                      <span className="da-trait-desc">{opt.desc}</span>
                      {selected && <span className="da-trait-check">✓</span>}
                    </motion.button>
                  )
                })}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        <p className="da-disclaimer">
          Answer honestly based on your lifelong patterns — not what you wish were true. This helps build an accurate Ayurvedic profile.
        </p>
      </motion.div>
    </div>
  )
}
