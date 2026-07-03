// Shared medical-condition catalogue used by both Onboarding and the Dosha Quiz.
// IDs must match the backend condition vocabulary (server/engine/condition_vocab.py)
// so they resolve to the correct dosha signal.
export const CONDITION_CATEGORIES = [
  {
    label: 'Musculoskeletal',
    items: [
      { id: 'arthritis', label: 'Arthritis' },
      { id: 'osteoarthritis', label: 'Osteoarthritis' },
      { id: 'rheumatoid_arthritis', label: 'Rheumatoid Arthritis' },
      { id: 'ankylosing_spondylitis', label: 'Ankylosing Spondylitis' },
      { id: 'gout', label: 'Gout' },
      { id: 'fibromyalgia', label: 'Fibromyalgia' },
      { id: 'osteoporosis', label: 'Osteoporosis' },
      { id: 'sciatica', label: 'Sciatica' },
      { id: 'cervical_spondylosis', label: 'Cervical Spondylosis' },
      { id: 'lumbar_spondylosis', label: 'Lumbar Spondylosis' },
    ],
  },
  {
    label: 'Neurological',
    items: [
      { id: 'migraine', label: 'Migraine' },
      { id: 'epilepsy', label: 'Epilepsy' },
      { id: 'parkinson', label: "Parkinson's" },
      { id: 'multiple_sclerosis', label: 'Multiple Sclerosis' },
      { id: 'tinnitus', label: 'Tinnitus' },
      { id: 'vertigo', label: 'Vertigo' },
      { id: 'chronic_fatigue_syndrome', label: 'Chronic Fatigue' },
      { id: 'peripheral_neuropathy', label: 'Peripheral Neuropathy' },
    ],
  },
  {
    label: 'Mental Health',
    items: [
      { id: 'anxiety', label: 'Anxiety Disorder' },
      { id: 'depression', label: 'Depression' },
      { id: 'bipolar', label: 'Bipolar Disorder' },
      { id: 'ocd', label: 'OCD' },
      { id: 'ptsd', label: 'PTSD' },
      { id: 'adhd', label: 'ADHD' },
      { id: 'insomnia', label: 'Chronic Insomnia' },
    ],
  },
  {
    label: 'Cardiovascular',
    items: [
      { id: 'hypertension', label: 'Hypertension' },
      { id: 'heart_disease', label: 'Heart Disease' },
      { id: 'atrial_fibrillation', label: 'Atrial Fibrillation' },
      { id: 'anemia', label: 'Anaemia' },
      { id: 'varicose_veins', label: 'Varicose Veins' },
      { id: 'low_blood_pressure', label: 'Low Blood Pressure' },
    ],
  },
  {
    label: 'Respiratory',
    items: [
      { id: 'asthma', label: 'Asthma' },
      { id: 'copd', label: 'COPD' },
      { id: 'allergic_rhinitis', label: 'Allergic Rhinitis' },
      { id: 'sinusitis', label: 'Chronic Sinusitis' },
      { id: 'sleep_apnea', label: 'Sleep Apnea' },
      { id: 'chronic_bronchitis', label: 'Chronic Bronchitis' },
    ],
  },
  {
    label: 'Digestive',
    items: [
      { id: 'acid_reflux', label: 'Acid Reflux / GERD' },
      { id: 'ibs', label: 'IBS' },
      { id: 'ibd_crohns', label: "Crohn's Disease" },
      { id: 'ulcerative_colitis', label: 'Ulcerative Colitis' },
      { id: 'fatty_liver', label: 'Fatty Liver' },
      { id: 'gallstones', label: 'Gallstones' },
      { id: 'constipation_chronic', label: 'Chronic Constipation' },
      { id: 'celiac', label: 'Celiac Disease' },
      { id: 'hemorrhoids', label: 'Haemorrhoids' },
    ],
  },
  {
    label: 'Endocrine & Metabolic',
    items: [
      { id: 'diabetes_type2', label: 'Type 2 Diabetes' },
      { id: 'diabetes_type1', label: 'Type 1 Diabetes' },
      { id: 'hypothyroidism', label: 'Hypothyroidism' },
      { id: 'hyperthyroidism', label: 'Hyperthyroidism' },
      { id: 'pcos', label: 'PCOS' },
      { id: 'high_cholesterol', label: 'High Cholesterol' },
      { id: 'obesity', label: 'Obesity (BMI > 30)' },
      { id: 'metabolic_syndrome', label: 'Metabolic Syndrome' },
      { id: 'hashimoto', label: "Hashimoto's Thyroiditis" },
    ],
  },
  {
    label: 'Skin',
    items: [
      { id: 'psoriasis', label: 'Psoriasis' },
      { id: 'eczema', label: 'Eczema' },
      { id: 'acne_severe', label: 'Severe Acne' },
      { id: 'vitiligo', label: 'Vitiligo' },
      { id: 'rosacea', label: 'Rosacea' },
      { id: 'urticaria', label: 'Urticaria / Hives' },
      { id: 'alopecia', label: 'Alopecia' },
    ],
  },
  {
    label: 'Urological & Reproductive',
    items: [
      { id: 'kidney_stones', label: 'Kidney Stones' },
      { id: 'recurrent_uti', label: 'Recurrent UTIs' },
      { id: 'endometriosis', label: 'Endometriosis' },
      { id: 'uterine_fibroids', label: 'Uterine Fibroids' },
      { id: 'dysmenorrhea', label: 'Painful Periods' },
      { id: 'menorrhagia', label: 'Heavy Periods' },
    ],
  },
  {
    label: 'Autoimmune',
    items: [
      { id: 'lupus', label: 'Lupus (SLE)' },
      { id: 'scleroderma', label: 'Scleroderma' },
      { id: 'rheumatoid_arthritis', label: 'Rheumatoid Arthritis' },
    ],
  },
]

// Flat id -> label lookup for rendering prefilled/free-text conditions as chips.
export const CONDITION_LABELS = Object.fromEntries(
  CONDITION_CATEGORIES.flatMap((c) => c.items).map((i) => [i.id, i.label])
)

// Turn a stored condition id (canonical or free-text) into a readable label.
export function conditionLabel(id) {
  if (CONDITION_LABELS[id]) return CONDITION_LABELS[id]
  return String(id).replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase())
}
