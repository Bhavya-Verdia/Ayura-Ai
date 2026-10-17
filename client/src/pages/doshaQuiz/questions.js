// The Prakriti instrument's questions. `server/tests/test_dosha_instrument.py`
// reads every `id:` in this file and holds them against the scorer's weights,
// so a question removed here fails that test rather than silently scoring 0.

// ── Physical trait questions — NO dosha labels shown ──────────────────────────
export const TRAIT_QUESTIONS = [
  {
    id: 'body_frame',
    question: 'What best describes your natural body frame?',
    hint: 'Think about your lifelong tendency, not your current weight',
    options: [
      { value: 'vata', label: 'Slim & light', desc: 'Naturally lean, fine-boned. Hard to gain weight even eating a lot. Small wrists and ankles.' },
      { value: 'pitta', label: 'Medium & athletic', desc: 'Medium build, well-proportioned. Gain and lose weight fairly easily. Natural muscle tone.' },
      { value: 'kapha', label: 'Solid & sturdy', desc: 'Larger, well-built frame. Tend to gain weight easily and lose it slowly. Strong and resilient.' },
    ],
  },
  {
    id: 'skin',
    question: 'How does your skin behave in normal conditions?',
    hint: 'Not during illness or stress — your everyday baseline',
    options: [
      { value: 'vata', label: 'Dry & delicate', desc: 'Tends to be dry, rough, or cracked — especially hands, lips, and heels. Gets tight in cold weather.' },
      { value: 'pitta', label: 'Warm & reactive', desc: 'Tends to be warm, sometimes oily. Prone to breakouts, redness, or flushing. Sensitive to products.' },
      { value: 'kapha', label: 'Smooth & moist', desc: 'Generally smooth, cool, and soft. Rarely dry. Naturally dewy — may feel slightly thick or retain moisture.' },
    ],
  },
  {
    id: 'digestion',
    question: 'How would you describe your natural digestion?',
    hint: 'Your lifelong digestive pattern, not a recent stomach issue',
    options: [
      { value: 'vata', label: 'Variable & sensitive', desc: 'Irregular — sometimes fast, sometimes slow. Often experience bloating, gas, or alternating habits. Appetite comes and goes.' },
      { value: 'pitta', label: 'Strong & intense', desc: 'Digest quickly and thoroughly. Get very irritable or uncomfortable when meals are delayed. Strong, sharp appetite.' },
      { value: 'kapha', label: 'Slow & steady', desc: 'Digest slowly but steadily. Can skip meals without much discomfort. Rarely feel intense hunger. Stay full a long time.' },
    ],
  },
  {
    id: 'sleep',
    question: 'How do you naturally sleep?',
    hint: 'Without sleep aids, in a normal period of life',
    options: [
      { value: 'vata', label: 'Light & restless', desc: 'Wake easily to sounds or thoughts. Sometimes hard to fall asleep. Have vivid, anxious, or busy dreams. Often feel I need more rest.' },
      { value: 'pitta', label: 'Moderate & refreshing', desc: 'Fall asleep without much trouble. Occasionally wake but go back to sleep. Feel genuinely rested with 6–7 hours.' },
      { value: 'kapha', label: 'Deep & heavy', desc: 'Sleep heavily and very deeply. Hard to wake up, especially in the morning. Need 8+ hours. Often feel groggy even after long sleep.' },
    ],
  },
  {
    id: 'temperature',
    question: 'How do you naturally respond to temperature?',
    hint: 'Your default preference, not during illness',
    options: [
      { value: 'vata', label: 'Love warmth', desc: 'Dislike cold intensely. Always first to reach for a sweater. Hands and feet tend to be cold. Prefer warm food and drinks.' },
      { value: 'pitta', label: 'Love cool', desc: 'Uncomfortable in heat. Prefer cool or air-conditioned spaces. Tend to run warm. Enjoy cold water, cold weather, and shade.' },
      { value: 'kapha', label: 'Comfortable & adaptable', desc: "Handle most temperatures well. Don't have strong preferences, though you might feel a little more comfortable with some warmth." },
    ],
  },
  {
    id: 'hair',
    question: 'How would you describe your hair naturally?',
    hint: 'Think of your hair before any styling, treatments, or colouring',
    options: [
      { value: 'vata', label: 'Fine & dry', desc: 'Thin, dry, frizzy, or brittle — prone to split ends and dandruff. Gets flyaway in wind.' },
      { value: 'pitta', label: 'Fine & silky', desc: 'Fine, silky, and gets oily quickly. Prone to premature graying or early thinning.' },
      { value: 'kapha', label: 'Thick & lustrous', desc: 'Thick, wavy, naturally oily, and strong. Grows well and rarely breaks easily.' },
    ],
  },
  {
    id: 'energy',
    question: 'How would you describe your natural energy pattern?',
    hint: 'Your default energy — not during illness or high stress',
    options: [
      { value: 'vata', label: 'Bursts & crashes', desc: 'Energy comes in intense bursts that drop quickly. Poor long-term stamina. Need frequent rest.' },
      { value: 'pitta', label: 'Strong & sustained', desc: 'Good consistent energy, especially mid-day. Driven, purposeful, and goal-oriented.' },
      { value: 'kapha', label: 'Slow start, high stamina', desc: 'Slow to get going in the morning, but once warmed up have excellent endurance all day.' },
    ],
  },
  {
    id: 'stress_response',
    question: 'When you feel overwhelmed or under pressure, you tend to:',
    hint: 'Think about your most consistent pattern — not the best version of yourself',
    options: [
      { value: 'vata', label: 'Worry & scatter', desc: 'Get anxious, overthink, freeze up, or feel scattered. Mind races, hard to focus. Might avoid the situation.' },
      { value: 'pitta', label: 'Get sharp & push', desc: 'Get impatient or irritated. Confront the problem head-on, sometimes too aggressively. Driven to solve it fast.' },
      { value: 'kapha', label: 'Withdraw & slow down', desc: 'Go quiet, pull back, or feel heavy and stuck. Take a long time to process. May comfort-eat or over-sleep.' },
    ],
  },
  {
    id: 'memory',
    question: 'How does your memory naturally work?',
    hint: 'Your baseline pattern over a lifetime — not when stressed or sleep-deprived',
    options: [
      { value: 'vata', label: 'Quick to learn, quick to forget', desc: 'Pick up new things fast and make creative connections — but details and names fade quickly. Many ideas, less follow-through.' },
      { value: 'pitta', label: 'Sharp and precise', desc: 'Learn things systematically and remember them accurately. Good recall for facts, events, and details. Strong focus when motivated.' },
      { value: 'kapha', label: 'Slow to learn, never forget', desc: "Take more time to absorb new information, but once it's in — it stays forever. Excellent long-term retention." },
    ],
  },
  {
    id: 'decision_making',
    question: 'How do you naturally make decisions?',
    hint: 'Especially important ones — not trivial daily choices',
    options: [
      { value: 'vata', label: 'Change my mind often', desc: 'Hard to decide. Consider many options, feel pulled in different directions. May regret decisions and second-guess yourself.' },
      { value: 'pitta', label: 'Decide quickly and firmly', desc: 'Assess the facts, decide fast, and commit with confidence. Rarely second-guess yourself. Can be too rigid sometimes.' },
      { value: 'kapha', label: 'Deliberate for a long time', desc: 'Take your time, weigh everything carefully, and consult others before deciding. Once decided, very hard to change.' },
    ],
  },
  {
    id: 'speech',
    question: 'How would others describe the way you naturally speak?',
    hint: 'In everyday relaxed conversation — not in formal or high-stress settings',
    options: [
      { value: 'vata', label: 'Fast and expressive', desc: 'Talk fast, jump between topics, use lots of gestures. Enthusiastic and creative but sometimes hard to follow. Trail off mid-thought.' },
      { value: 'pitta', label: 'Clear and direct', desc: 'Precise, articulate, and confident. Get to the point. Can come across as blunt or critical without meaning to.' },
      { value: 'kapha', label: 'Calm and melodious', desc: 'Speak slowly and thoughtfully. Pleasant voice, measured words, considerate. Sometimes take too long to get to the point.' },
    ],
  },
  {
    id: 'emotional_nature',
    question: 'What best describes your natural emotional baseline?',
    hint: 'In a normal period of life — not during a crisis or exceptionally happy time',
    options: [
      { value: 'vata', label: 'Enthusiastic but variable', desc: 'Quick to feel excited, creative, and inspired — but also quick to worry, feel anxious, or lose enthusiasm. Emotions shift fast.' },
      { value: 'pitta', label: 'Intense and purposeful', desc: "Feel things deeply and strongly. Passionate, ambitious, sometimes perfectionistic. Prone to frustration when things don't go to plan." },
      { value: 'kapha', label: 'Stable and nurturing', desc: 'Naturally calm, steady, and caring. Rarely rattled by small things. But can become attached, possessive, or hold onto grudges.' },
    ],
  },
  {
    id: 'eating_habits',
    question: 'How do you naturally approach eating?',
    hint: 'Your default pattern when life is normal — not during illness or extreme stress',
    options: [
      { value: 'vata', label: 'Quick & irregular', desc: 'Eat fast, often while distracted or standing. Skip meals without noticing, then overeat. Appetite varies day to day.' },
      { value: 'pitta', label: 'Precise & scheduled', desc: 'Eat at set times, fully focused on the meal. Get irritable or headachy when meals are delayed. Strong, consistent appetite.' },
      { value: 'kapha', label: 'Slow & social', desc: 'Eat slowly and enjoy every bite. Linger at the table. Never really starving but always happy to eat. Metabolism is slow.' },
    ],
  },
  {
    id: 'walk_pace',
    question: 'How do you naturally walk?',
    hint: "When you're not in a hurry — your default gait",
    options: [
      { value: 'vata', label: 'Fast & light', desc: 'Quick, light steps with variable pace. Often change direction. Hard to keep still. People say you move fast.' },
      { value: 'pitta', label: 'Purposeful & medium', desc: "Walk with clear intention and direction. Medium pace, heel-to-toe. People can tell you're going somewhere." },
      { value: 'kapha', label: 'Slow & grounded', desc: 'Steady, unhurried, stable stride. Hard to rush. Feel planted and solid when you walk.' },
    ],
  },
  {
    id: 'anger_style',
    question: 'When you get angry, what typically happens?',
    hint: 'Your most natural pattern — not what you wish you did',
    options: [
      { value: 'vata', label: 'Quick flare, quick fade', desc: 'Get agitated or anxious fast, but the feeling passes quickly. Often forget what upset you. May avoid confrontation.' },
      { value: 'pitta', label: 'Sharp & direct', desc: 'Get visibly angry, may say cutting or critical things. Express it clearly. Hold it for a short while, then move on.' },
      { value: 'kapha', label: 'Slow burn, long memory', desc: 'Slow to get angry, but once there it stays. Hold grudges for a long time. Rarely blow up but simmer internally.' },
    ],
  },
  {
    id: 'agni_type',
    question: 'How would you describe your Agni — your digestive fire?',
    hint: 'Agni is the cornerstone of Ayurvedic health (Charaka Sutrasthana 15.3). Think about your lifelong digestive pattern.',
    options: [
      { value: 'sama', label: 'Sama Agni — Balanced', desc: 'Consistent appetite, digest most foods well, regular elimination, feel energised after meals. Rarely have digestive complaints.' },
      { value: 'vata', label: 'Vishama Agni — Irregular', desc: 'Appetite and digestion vary unpredictably — sometimes strong, sometimes weak. Bloating, gas, alternating constipation/looseness. Nervous-type digestion.' },
      { value: 'pitta', label: 'Tikshna Agni — Sharp/Intense', desc: 'Strong, sometimes excessive appetite. Digest quickly and thoroughly. Prone to acidity, heartburn, or loose stools. Get very irritable when meals are skipped.' },
      { value: 'kapha', label: 'Manda Agni — Slow', desc: 'Slow metabolism. Feel heavy or sluggish after meals. Low appetite especially in the morning. Food takes long to digest. Tendency toward weight gain.' },
    ],
  },
  {
    id: 'stool_pattern',
    question: 'How are your bowel habits normally? (Mala Pareeksha)',
    hint: 'Without dietary changes — your lifelong default. Mala (stool) quality is a primary Ayurvedic diagnostic indicator.',
    options: [
      { value: 'vata', label: 'Irregular & dry', desc: 'Tend toward constipation — dry, hard pellets, or with excessive gas. Frequency varies: sometimes twice a day, sometimes every 2 days. Incomplete feeling.' },
      { value: 'pitta', label: 'Loose & urgent', desc: 'Soft, formed, sometimes loose or semi-formed. May have urgency. Regular once or twice daily. Occasionally burning sensation. Yellowish.' },
      { value: 'kapha', label: 'Slow & heavy', desc: 'Once daily, well-formed, heavy, and complete. Sometimes slow to move but consistent. Pale or mucus-coated occasionally. Feel satisfied after.' },
    ],
  },
  {
    id: 'eye_quality',
    question: 'How would you describe your eyes naturally? (Drik Pareeksha)',
    hint: 'Not after illness or screen fatigue — your everyday baseline eye quality',
    options: [
      { value: 'vata', label: 'Small & dry', desc: 'Small or narrow eyes, tend to be dry or gritty. Irregular blinking or occasional twitching. Gaze can be restless or darting. Appear slightly dull.' },
      { value: 'pitta', label: 'Sharp & penetrating', desc: 'Moderate size, bright, intense, and sharp. Tend toward redness or sensitivity to light when tired or stressed. Whites may have slight reddish tinge.' },
      { value: 'kapha', label: 'Large & lustrous', desc: 'Large, moist, calm, and pleasant. Steady, unhurried gaze. Clear whites. Naturally attractive eyes with good luster. Rarely dry.' },
    ],
  },
  {
    id: 'voice_quality',
    question: 'How would you describe your natural speaking voice? (Shabda Pareeksha)',
    hint: 'Your everyday voice — not during illness or presentation anxiety',
    options: [
      { value: 'vata', label: 'Thin & quick', desc: 'Thin, somewhat low volume — can crack or go hoarse under stress. Speak quickly, may run out of breath mid-sentence. Voice trails off at ends.' },
      { value: 'pitta', label: 'Clear & sharp', desc: 'Clear, crisp, well-projected, and articulate. Commands attention naturally. Can become cutting or sharp-edged when under pressure or emotional.' },
      { value: 'kapha', label: 'Deep & resonant', desc: 'Deep, melodious, slow, and steady. Very pleasant to listen to. Rarely raises voice. Could be a singer — naturally musical quality. Projects without effort.' },
    ],
  },
  {
    id: 'nadi_rhythm',
    question: 'How would you describe your natural pulse? (Nadi Pareeksha — self-report)',
    hint: 'Feel your radial pulse (wrist, below thumb) lightly. Classical Nadi Pareeksha requires a Vaidya — this question provides a digital approximation only.',
    options: [
      { value: 'vata', label: 'Sarpa — snake-like', desc: 'Irregular, thin, thready, fast. Hard to feel — seems to disappear when you press slightly. Wriggles and varies. Classical Vata Nadi (Sarpa gati per Sharangadhara Samhita 1.7.3).' },
      { value: 'pitta', label: 'Manduka — frog-like', desc: 'Strong, bounding, sharp, moderate speed. Feels prominent and forceful. Jumps under fingers. Classical Pitta Nadi (Manduka gati).' },
      { value: 'kapha', label: 'Hamsa — swan-like', desc: 'Slow, broad, wave-like, steady. Feels deep and stable. Glides smoothly under light pressure. Classical Kapha Nadi (Hamsa gati).' },
    ],
  },
  {
    id: 'mutra_pattern',
    question: 'How is your urine normally? (Mutra Pareeksha)',
    hint: 'When well-hydrated and healthy — your default pattern. Mutra (urine) is a key Ashtavidha examination indicator.',
    options: [
      { value: 'vata', label: 'Scanty & variable', desc: 'Scanty in volume, variable frequency, sometimes dark or cloudy. Can get dehydrated easily. Occasional discomfort.' },
      { value: 'pitta', label: 'Yellow & concentrated', desc: 'Yellow or amber coloured, often strong odour. May feel slight warmth or burning. Frequent in hot weather. Darkens with stress.' },
      { value: 'kapha', label: 'Pale & copious', desc: 'Pale, large volume, infrequent but heavy. Occasionally turbid or slightly foamy. Rarely burning. Steady and predictable.' },
    ],
  },
  // ── Manasa Prakriti — Triguna assessment (Charaka Samhita Shareera Sthana 4) ─
  {
    // Consistency probe: re-asks the `temperature` construct from the opposite
    // angle (aversion rather than preference) and far away from it in the
    // sequence. It carries no scoring weight — disagreement with `temperature`
    // lowers confidence instead, which is how an inattentive or random
    // run gets caught now that permuted options make straight-lining look
    // like noise rather than like a clean single dosha.
    id: 'temperature_check',
    question: 'Which kind of weather leaves you feeling worst?',
    hint: 'The conditions you actively avoid, not just mildly dislike',
    options: [
      { value: 'vata', label: 'Cold, dry, windy', desc: 'Bitter wind and dry cold get into you — stiff joints, dry skin, hard to warm up again.' },
      { value: 'pitta', label: 'Hot, bright, humid', desc: 'High sun and heat drain you — you get flushed, irritable, and seek shade or air-conditioning.' },
      { value: 'kapha', label: 'Damp, grey, heavy', desc: 'Overcast, wet, muggy days make you feel sluggish, congested, and hard to get moving.' },
    ],
  },
  {
    id: 'motivation_source',
    question: 'What primarily drives you to act or make decisions?',
    hint: 'Your most honest motivation, not your ideal',
    options: [
      { value: 'satva', label: 'Principle', desc: 'I weigh what seems right or worthwhile, and that usually settles it.' },
      { value: 'rajas', label: 'Achievement', desc: 'I move toward a target — progress, results, and being recognised for them.' },
      { value: 'tamas', label: 'Continuity', desc: 'I stay with what is familiar and settled, and change when there is clear reason to.' },
    ],
  },
  {
    id: 'mind_clarity',
    question: 'How would you describe your typical mental state?',
    hint: 'On a regular day — not when you are at your best',
    options: [
      { value: 'satva', label: 'Quiet', desc: 'Usually one thought at a time, with space between them.' },
      { value: 'rajas', label: 'Busy', desc: 'Usually several threads at once — planning, weighing, running ahead.' },
      { value: 'tamas', label: 'Slow', desc: 'Usually unhurried and low-key; takes a while to get moving on something new.' },
    ],
  },
  {
    id: 'emotional_quality',
    question: 'When you feel a strong emotion, what characterises it most?',
    hint: 'Think of anger, fear, grief, or excitement',
    options: [
      { value: 'satva', label: 'Passes through', desc: 'It arrives clearly, I register it, and it moves on fairly quickly.' },
      { value: 'rajas', label: 'Runs hot', desc: 'It arrives strongly and stays with me; I go back over the situation afterwards.' },
      { value: 'tamas', label: 'Stays under the surface', desc: 'It registers quietly and settles in the background rather than showing outwardly.' },
    ],
  },
  {
    id: 'daily_discipline',
    question: 'How consistent are you with daily routines and self-care?',
    hint: 'Sleep, diet, exercise, spiritual or reflective practice',
    options: [
      { value: 'satva', label: 'Even', desc: 'Roughly the same rhythm most days — sleep, meals and practice land around the same time.' },
      { value: 'rajas', label: 'Variable', desc: 'Intense stretches of routine alternating with stretches where it all goes out the window.' },
      { value: 'tamas', label: 'Loose', desc: 'Days take their own shape; I follow how I feel rather than a set structure.' },
    ],
  },
  {
    id: 'conflict_approach',
    question: 'When you face a conflict or difficult conversation:',
    hint: 'Your first natural impulse',
    options: [
      { value: 'satva', label: 'Work it through', desc: 'Talk it out then and there, and try to land somewhere both sides can accept.' },
      { value: 'rajas', label: 'Take it on', desc: 'State my case directly and push until the disagreement is settled.' },
      { value: 'tamas', label: 'Let it sit', desc: 'Step back and give it time rather than taking it up immediately.' },
    ],
  },
]

// ── Symptom clusters — Vikriti indicators ─────────────────────────────────────
export const SYMPTOM_CLUSTERS = [
  { id: 'anxiety_worry', label: 'Anxiety or worry', desc: 'Racing thoughts, nervousness, or feeling overwhelmed' },
  { id: 'dry_skin_constipation', label: 'Dryness or constipation', desc: 'Dry skin, lips, constipation, or cracking joints' },
  { id: 'trouble_sleeping', label: 'Trouble sleeping', desc: 'Insomnia, light sleep, or feeling scattered/ungrounded' },
  { id: 'bloating_gas', label: 'Bloating or gas', desc: 'Irregular digestion, bloating, gas, or alternating bowels' },
  { id: 'heartburn_acidity', label: 'Acidity or inflammation', desc: 'Heartburn, acid reflux, or stomach inflammation' },
  { id: 'skin_rashes', label: 'Skin flare-ups', desc: 'Rashes, acne, or feeling consistently overheated' },
  { id: 'irritability', label: 'Irritability or frustration', desc: 'Impatience, anger, or being overly critical' },
  { id: 'weight_gain', label: 'Weight or sluggishness', desc: 'Weight gain, water retention, or feeling heavy' },
  { id: 'low_energy', label: 'Low energy or motivation', desc: 'Lethargy, lack of motivation, or mild depression' },
  { id: 'congestion', label: 'Congestion or mucus', desc: 'Sinus congestion, excess mucus, or slow metabolism' },
  { id: 'joint_stiffness', label: 'Joint or body aches', desc: 'Stiffness, dryness in joints, or general body aches' },
  { id: 'brain_fog', label: 'Brain fog', desc: 'Difficulty concentrating, mental cloudiness, or forgetfulness' },
  { id: 'coated_tongue_ama', label: 'Coated tongue', desc: 'White/yellow coating on tongue in the morning — classical Ama (Jihva Pareeksha)' },
  { id: 'morning_heaviness', label: 'Morning heaviness', desc: 'Body feels heavy, dull, or unrefreshed despite adequate sleep — Ama in channels' },
  { id: 'feeling_balanced', label: 'Feeling balanced', desc: 'No major complaints — generally feeling well' },
]

export const CLARIFY_QUESTIONS = [
  {
    id: 'chronic_pattern',
    question: 'Over the last year or more (not just recently), your most persistent pattern has been:',
    hint: 'Ignore temporary phases — think about your consistent baseline',
    options: [
      { value: 'vata', label: 'Irregular & anxious', desc: 'Variable energy, scattered focus, anxious or unsettled as a baseline state.' },
      { value: 'pitta', label: 'Intense & driven', desc: 'Strong drive, tendency toward inflammation/acidity, sharp emotional responses.' },
      { value: 'kapha', label: 'Stable & slow', desc: 'Consistent but slow pace, steady mood, tendency toward heaviness or congestion.' },
    ],
  },
  {
    id: 'recovery_style',
    question: 'When you get sick or run down, you typically:',
    hint: 'Your natural recovery pattern — not what you do deliberately',
    options: [
      { value: 'vata', label: 'Recover erratically', desc: 'Get sick fast, symptoms are variable and shifting. Hard to predict. Anxiety spikes during illness.' },
      { value: 'pitta', label: 'Fight it intensely', desc: 'Fever, inflammation, or sharp symptoms. Recover relatively fast when you rest, but struggle to slow down.' },
      { value: 'kapha', label: 'Get stuck slowly', desc: 'Congestion, heaviness, slow onset. Recovery takes longer but eventual. Tend toward mucus and fatigue.' },
    ],
  },
]

export const MANASA_TRAIT_IDS = ['motivation_source', 'mind_clarity', 'emotional_quality', 'daily_discipline', 'conflict_approach']

// ── Localisation ──────────────────────────────────────────────────────────────
// The constants above stay the source of truth for ids, option values and order
// — only the *copy* is looked up. Every lookup passes the English string as the
// i18next default, so an untranslated key renders exactly as it does today
// rather than blanking, and a locale can be filled in one question at a time.
//
// This matters more here than on a marketing page: a self-report instrument is
// only as accurate as the respondent's comprehension, so a Hindi speaker
// guessing at "fine, dry, frizzy — prone to split ends" contributes noise that
// then drives all seven plans. Settings offers eight languages; until now this
// flow was English regardless of the choice.
export function localiseQuestions(t, questions, ns) {
  return questions.map((q) => ({
    ...q,
    question: t(`quiz.${ns}.${q.id}.q`, q.question),
    hint: t(`quiz.${ns}.${q.id}.hint`, q.hint),
    options: q.options.map((o) => ({
      ...o,
      label: t(`quiz.${ns}.${q.id}.opt.${o.value}.label`, o.label),
      desc: t(`quiz.${ns}.${q.id}.opt.${o.value}.desc`, o.desc),
    })),
  }))
}

export function localiseSymptoms(t, clusters) {
  return clusters.map((c) => ({
    ...c,
    label: t(`quiz.symptom.${c.id}.label`, c.label),
    desc: t(`quiz.symptom.${c.id}.desc`, c.desc),
  }))
}
