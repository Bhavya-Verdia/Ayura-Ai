import { tr } from '../lib/tr'

// Shared medical-condition catalogue used by both Onboarding and the Dosha Quiz.
// IDs must match the backend condition vocabulary (server/engine/condition_vocab.py)
// so they resolve to the correct dosha signal.
export const CONDITION_CATEGORIES = [
  {
    get label() { return tr('ui.conditions.musculoskeletal', 'Musculoskeletal') },
    items: [
      { id: 'arthritis', get label() { return tr('ui.conditions.arthritis', 'Arthritis') } },
      { id: 'osteoarthritis', get label() { return tr('ui.conditions.osteoarthritis', 'Osteoarthritis') } },
      { id: 'rheumatoid_arthritis', get label() { return tr('ui.conditions.rheumatoidArthritis', 'Rheumatoid Arthritis') } },
      { id: 'ankylosing_spondylitis', get label() { return tr('ui.conditions.ankylosingSpondylitis', 'Ankylosing Spondylitis') } },
      { id: 'gout', get label() { return tr('ui.conditions.gout', 'Gout') } },
      { id: 'fibromyalgia', get label() { return tr('ui.conditions.fibromyalgia', 'Fibromyalgia') } },
      { id: 'osteoporosis', get label() { return tr('ui.conditions.osteoporosis', 'Osteoporosis') } },
      { id: 'sciatica', get label() { return tr('ui.conditions.sciatica', 'Sciatica') } },
      { id: 'cervical_spondylosis', get label() { return tr('ui.conditions.cervicalSpondylosis', 'Cervical Spondylosis') } },
      { id: 'lumbar_spondylosis', get label() { return tr('ui.conditions.lumbarSpondylosis', 'Lumbar Spondylosis') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.neurological', 'Neurological') },
    items: [
      { id: 'migraine', get label() { return tr('ui.conditions.migraine', 'Migraine') } },
      { id: 'epilepsy', get label() { return tr('ui.conditions.epilepsy', 'Epilepsy') } },
      { id: 'parkinson', get label() { return tr('ui.conditions.parkinsonS', 'Parkinson\'s') } },
      { id: 'multiple_sclerosis', get label() { return tr('ui.conditions.multipleSclerosis', 'Multiple Sclerosis') } },
      { id: 'tinnitus', get label() { return tr('ui.conditions.tinnitus', 'Tinnitus') } },
      { id: 'vertigo', get label() { return tr('ui.conditions.vertigo', 'Vertigo') } },
      { id: 'chronic_fatigue_syndrome', get label() { return tr('ui.conditions.chronicFatigue', 'Chronic Fatigue') } },
      { id: 'peripheral_neuropathy', get label() { return tr('ui.conditions.peripheralNeuropathy', 'Peripheral Neuropathy') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.mentalHealth', 'Mental Health') },
    items: [
      { id: 'anxiety', get label() { return tr('ui.conditions.anxietyDisorder', 'Anxiety Disorder') } },
      { id: 'depression', get label() { return tr('ui.conditions.depression', 'Depression') } },
      { id: 'bipolar', get label() { return tr('ui.conditions.bipolarDisorder', 'Bipolar Disorder') } },
      { id: 'ocd', label: 'OCD' },
      { id: 'ptsd', label: 'PTSD' },
      { id: 'adhd', label: 'ADHD' },
      { id: 'insomnia', get label() { return tr('ui.conditions.chronicInsomnia', 'Chronic Insomnia') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.cardiovascular', 'Cardiovascular') },
    items: [
      { id: 'hypertension', get label() { return tr('ui.conditions.hypertension', 'Hypertension') } },
      { id: 'heart_disease', get label() { return tr('ui.conditions.heartDisease', 'Heart Disease') } },
      { id: 'atrial_fibrillation', get label() { return tr('ui.conditions.atrialFibrillation', 'Atrial Fibrillation') } },
      { id: 'anemia', get label() { return tr('ui.conditions.anaemia', 'Anaemia') } },
      { id: 'varicose_veins', get label() { return tr('ui.conditions.varicoseVeins', 'Varicose Veins') } },
      { id: 'low_blood_pressure', get label() { return tr('ui.conditions.lowBloodPressure', 'Low Blood Pressure') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.respiratory', 'Respiratory') },
    items: [
      { id: 'asthma', get label() { return tr('ui.conditions.asthma', 'Asthma') } },
      { id: 'copd', label: 'COPD' },
      { id: 'allergic_rhinitis', get label() { return tr('ui.conditions.allergicRhinitis', 'Allergic Rhinitis') } },
      { id: 'sinusitis', get label() { return tr('ui.conditions.chronicSinusitis', 'Chronic Sinusitis') } },
      { id: 'sleep_apnea', get label() { return tr('ui.conditions.sleepApnea', 'Sleep Apnea') } },
      { id: 'chronic_bronchitis', get label() { return tr('ui.conditions.chronicBronchitis', 'Chronic Bronchitis') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.digestive', 'Digestive') },
    items: [
      { id: 'acid_reflux', get label() { return tr('ui.conditions.acidRefluxGerd', 'Acid Reflux / GERD') } },
      { id: 'ibs', label: 'IBS' },
      { id: 'ibd_crohns', get label() { return tr('ui.conditions.crohnSDisease', 'Crohn\'s Disease') } },
      { id: 'ulcerative_colitis', get label() { return tr('ui.conditions.ulcerativeColitis', 'Ulcerative Colitis') } },
      { id: 'fatty_liver', get label() { return tr('ui.conditions.fattyLiver', 'Fatty Liver') } },
      { id: 'gallstones', get label() { return tr('ui.conditions.gallstones', 'Gallstones') } },
      { id: 'constipation_chronic', get label() { return tr('ui.conditions.chronicConstipation', 'Chronic Constipation') } },
      { id: 'celiac', get label() { return tr('ui.conditions.celiacDisease', 'Celiac Disease') } },
      { id: 'hemorrhoids', get label() { return tr('ui.conditions.haemorrhoids', 'Haemorrhoids') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.endocrineMetabolic', 'Endocrine & Metabolic') },
    items: [
      { id: 'diabetes_type2', get label() { return tr('ui.conditions.type2Diabetes', 'Type 2 Diabetes') } },
      { id: 'diabetes_type1', get label() { return tr('ui.conditions.type1Diabetes', 'Type 1 Diabetes') } },
      { id: 'hypothyroidism', get label() { return tr('ui.conditions.hypothyroidism', 'Hypothyroidism') } },
      { id: 'hyperthyroidism', get label() { return tr('ui.conditions.hyperthyroidism', 'Hyperthyroidism') } },
      { id: 'pcos', label: 'PCOS' },
      { id: 'high_cholesterol', get label() { return tr('ui.conditions.highCholesterol', 'High Cholesterol') } },
      { id: 'obesity', get label() { return tr('ui.conditions.obesityBmi30', 'Obesity (BMI > 30)') } },
      { id: 'metabolic_syndrome', get label() { return tr('ui.conditions.metabolicSyndrome', 'Metabolic Syndrome') } },
      { id: 'hashimoto', get label() { return tr('ui.conditions.hashimotoSThyroiditis', 'Hashimoto\'s Thyroiditis') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.skin', 'Skin') },
    items: [
      { id: 'psoriasis', get label() { return tr('ui.conditions.psoriasis', 'Psoriasis') } },
      { id: 'eczema', get label() { return tr('ui.conditions.eczema', 'Eczema') } },
      { id: 'acne_severe', get label() { return tr('ui.conditions.severeAcne', 'Severe Acne') } },
      { id: 'vitiligo', get label() { return tr('ui.conditions.vitiligo', 'Vitiligo') } },
      { id: 'rosacea', get label() { return tr('ui.conditions.rosacea', 'Rosacea') } },
      { id: 'urticaria', get label() { return tr('ui.conditions.urticariaHives', 'Urticaria / Hives') } },
      { id: 'alopecia', get label() { return tr('ui.conditions.alopecia', 'Alopecia') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.urologicalReproductive', 'Urological & Reproductive') },
    items: [
      { id: 'kidney_stones', get label() { return tr('ui.conditions.kidneyStones', 'Kidney Stones') } },
      { id: 'recurrent_uti', get label() { return tr('ui.conditions.recurrentUtis', 'Recurrent UTIs') } },
      { id: 'endometriosis', get label() { return tr('ui.conditions.endometriosis', 'Endometriosis') } },
      { id: 'uterine_fibroids', get label() { return tr('ui.conditions.uterineFibroids', 'Uterine Fibroids') } },
      { id: 'dysmenorrhea', get label() { return tr('ui.conditions.painfulPeriods', 'Painful Periods') } },
      { id: 'menorrhagia', get label() { return tr('ui.conditions.heavyPeriods', 'Heavy Periods') } },
    ],
  },
  {
    get label() { return tr('ui.conditions.autoimmune', 'Autoimmune') },
    items: [
      { id: 'lupus', get label() { return tr('ui.conditions.lupusSle', 'Lupus (SLE)') } },
      { id: 'scleroderma', get label() { return tr('ui.conditions.scleroderma', 'Scleroderma') } },
      { id: 'rheumatoid_arthritis', get label() { return tr('ui.conditions.rheumatoidArthritis', 'Rheumatoid Arthritis') } },
    ],
  },
]

// Flat id -> label lookup for rendering prefilled/free-text conditions as chips.
const CONDITION_LABELS = Object.fromEntries(
  CONDITION_CATEGORIES.flatMap((c) => c.items).map((i) => [i.id, i.label])
)

// Turn a stored condition id (canonical or free-text) into a readable label.
export function conditionLabel(id) {
  if (CONDITION_LABELS[id]) return CONDITION_LABELS[id]
  return String(id).replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase())
}
