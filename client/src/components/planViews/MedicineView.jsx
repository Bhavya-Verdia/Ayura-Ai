import React, { useState } from 'react'
import {
  Leaf, Pill, Sparkles, Droplets, Calendar, ShieldCheck, Flame, ChevronDown, ChevronUp, UtensilsCrossed, Clock, BookOpen, Stethoscope, Layers, TriangleAlert, Snowflake,
} from 'lucide-react'
import { DOSHA_COLORS_R } from '../../constants/dosha'
import { RoutineView } from './RoutineView'

const TIER_LABEL = { 1: 'OTC Safe', 2: 'Practitioner Advised' }

const TIER_COLOR = { 1: '#22c55e', 2: '#f59e0b' }

const TYPE_COLOR = {
  'churna (powder)':                     '#a78bfa',
  'avaleha (jam)':                       '#fb923c',
  'arishta (fermented decoction)':       '#34d399',
  'asava (fermented)':                   '#34d399',
  'vati (tablet)':                       '#60a5fa',
  'vati/guggulu (tablet)':               '#60a5fa',
  'kashayam (decoction)':                '#2dd4bf',
  'ghrita (medicated ghee)':             '#fde68a',
  'taila (oil)':                         '#fbbf24',
  'satva (extract)':                     '#e879f9',
  'bhasma (ash)':                        '#94a3b8',
  'pishti (powder of gems/minerals)':    '#c4b5fd',
  'pak (confection)':                    '#f97316',
}

const RASA_COLOR = {
  madhura: '#22c55e',
  amla:    '#f59e0b',
  lavana:  '#60a5fa',
  katu:    '#ef4444',
  tikta:   '#a78bfa',
  kashaya: '#6b7280',
}

const KARMA_COLOR = {
  'Deepana':     '#f59e0b',
  'Pachana':     '#fb923c',
  'Vatahara':    '#60a5fa',
  'Pittahara':   '#34d399',
  'Kaphahara':   '#a78bfa',
  'Tridoshahara':'#e879f9',
  'Rasayana':    '#22c55e',
  'Balya':       '#2dd4bf',
  'Medhya':      '#818cf8',
  'Brimhana':    '#fde68a',
  'Shodhana':    '#f97316',
  'Anulomana':   '#94a3b8',
}


function MedCard({ med, rationale }) {
  const [open, setOpen] = useState(false)
  const typeKey   = (med.type || '').toLowerCase()
  const color     = TYPE_COLOR[typeKey] || '#94a3b8'
  const tierColor = TIER_COLOR[med.safety_tier] || '#94a3b8'
  const isExternal = med.application_type === 'external'
  const hasRasa    = med.rasa?.length > 0
  const hasKarma   = med.karma?.length > 0
  const hasDhatu   = med.dhatu_affected?.length > 0
  const durMin     = med.duration_min_weeks
  const durMax     = med.duration_max_weeks

  return (
    <div className="mv-card" style={{ '--mv-accent': color }}>
      {/* ── Header ── */}
      <div className="mv-card-header" onClick={() => setOpen(o => !o)} role="button" tabIndex={0}>
        <div className="mv-card-left">
          <div className="mv-med-name">
            {med.name}
            {med.previously_tried && <span className="mv-tried-badge">Tried before</span>}
          </div>
          <div className="mv-type-chip" style={{ background: color + '22', color }}>{med.type}</div>
        </div>
        <div className="mv-card-right">
          {durMin && <span className="mv-duration-badge">{durMin}–{durMax || durMin} wk</span>}
          <span className="mv-tier-badge" style={{ background: tierColor + '22', color: tierColor }}>
            {TIER_LABEL[med.safety_tier] || 'Consult Vaidya'}
          </span>
          {isExternal && <span className="mv-external-badge">External</span>}
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </div>
      </div>

      {/* ── Panchakosha pharmacology strip (always visible) ── */}
      {(hasRasa || med.virya || med.vipaka) && (
        <div className="mv-pharma-strip">
          {hasRasa && (
            <div className="mv-pharma-group">
              <span className="mv-pharma-label">Rasa</span>
              <div className="mv-rasa-chips">
                {med.rasa.map((r, i) => (
                  <span key={i} className="mv-rasa-chip" style={{ background: (RASA_COLOR[r] || '#94a3b8') + '22', color: RASA_COLOR[r] || '#94a3b8' }}>
                    {r.charAt(0).toUpperCase() + r.slice(1)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {med.virya && (
            <div className="mv-pharma-group">
              <span className="mv-pharma-label">Virya</span>
              <span className={`mv-virya-badge ${med.virya === 'ushna' ? 'ushna' : 'sheeta'}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                {med.virya === 'ushna' ? <><Flame size={13} strokeWidth={2} /> Heating</> : <><Snowflake size={13} strokeWidth={2} /> Cooling</>}
              </span>
            </div>
          )}
          {med.vipaka && (
            <div className="mv-pharma-group">
              <span className="mv-pharma-label">Vipaka</span>
              <span className="mv-vipaka-badge">{med.vipaka.charAt(0).toUpperCase() + med.vipaka.slice(1)}</span>
            </div>
          )}
        </div>
      )}

      {/* ── Expanded body ── */}
      {open && (
        <div className="mv-card-body">
          {/* Rationale (from enricher) */}
          {rationale && (
            <div className="mv-rationale-block">
              {typeof rationale === 'object' ? (
                <>
                  {rationale.rasa_guna_reasoning && <p className="mv-rationale">{rationale.rasa_guna_reasoning}</p>}
                  {rationale.classical_basis && (
                    <div className="mv-classical-basis">
                      <BookOpen size={11} />
                      <span>{rationale.classical_basis}</span>
                    </div>
                  )}
                  {rationale.anupana_reason && (
                    <div className="mv-anupana-reason">
                      <Droplets size={11} />
                      <span>{rationale.anupana_reason}</span>
                    </div>
                  )}
                </>
              ) : (
                <p className="mv-rationale">{rationale}</p>
              )}
            </div>
          )}

          {/* Classical action */}
          {med.classical_action && (
            <div className="mv-action-row">
              <BookOpen size={12} />
              <span>{med.classical_action}</span>
            </div>
          )}

          {/* Karma pills */}
          {hasKarma && (
            <div className="mv-section">
              <div className="mv-section-label">Karma (Actions)</div>
              <div className="mv-karma-row">
                {med.karma.map((k, i) => (
                  <span key={i} className="mv-karma-pill" style={{
                    background: (KARMA_COLOR[k] || '#64748b') + '22',
                    color: KARMA_COLOR[k] || '#94a3b8',
                  }}>{k}</span>
                ))}
              </div>
            </div>
          )}

          {/* Dhatu affected */}
          {hasDhatu && (
            <div className="mv-section">
              <div className="mv-section-label">Dhatu Affected</div>
              <div className="mv-karma-row">
                {med.dhatu_affected.map((d, i) => (
                  <span key={i} className="mv-dhatu-chip">{d.charAt(0).toUpperCase() + d.slice(1)}</span>
                ))}
              </div>
            </div>
          )}

          {/* Guna */}
          {med.guna?.length > 0 && (
            <div className="mv-section">
              <div className="mv-section-label">Guna (Qualities)</div>
              <div className="mv-karma-row">
                {med.guna.map((g, i) => (
                  <span key={i} className="mv-guna-chip">{g.charAt(0).toUpperCase() + g.slice(1)}</span>
                ))}
              </div>
            </div>
          )}

          {/* Ingredients */}
          {med.ingredients?.length > 0 && (
            <div className="mv-section">
              <div className="mv-section-label">Key Ingredients</div>
              <div className="mv-ingredients">
                {med.ingredients.map((ing, i) => (
                  <span key={i} className="mv-ing-chip">{ing}</span>
                ))}
              </div>
            </div>
          )}

          {/* Dosage */}
          <div className="mv-dosage-block">
            <div className="mv-section-label">Dosage & Administration</div>
            <p className="mv-dosage-text">{med.dosage}</p>
            {(med.selected_anupana || med.anupana) && (med.selected_anupana || med.anupana) !== 'External use only' && (
              <div className="mv-anupana">
                <Droplets size={12} />
                <span>Anupana: <strong>{med.selected_anupana || med.anupana}</strong></span>
              </div>
            )}
            {med.dosage_pediatric && (
              <div className="mv-anupana" style={{ color: '#a78bfa' }}>
                <span>Paediatric dose: {med.dosage_pediatric}</span>
              </div>
            )}
          </div>

          {/* Contraindications */}
          {med.contraindications?.length > 0 && (
            <div className="mv-section">
              <div className="mv-section-label" style={{ color: '#f97316' }}>Contraindications</div>
              <div className="mv-contra-chips">
                {med.contraindications.map((c, i) => (
                  <span key={i} className="mv-contra-chip">{c.replace(/_/g, ' ')}</span>
                ))}
              </div>
            </div>
          )}

          {med.drug_interactions?.length > 0 ? (
            <div className="mv-section">
              <div className="mv-section-label" style={{ color: '#c0392b' }}>
                <TriangleAlert size={11} /> Drug–herb interactions — check with your doctor
              </div>
              <div className="mv-contra-chips">
                {med.drug_interactions.map((d, i) => (
                  <span key={i} className="mv-interaction-chip">{String(d).replace(/_/g, ' ')}</span>
                ))}
              </div>
            </div>
          ) : (
            <div className="mv-section">
              <div className="mv-section-label mv-no-interactions">
                <ShieldCheck size={11} /> No known drug–herb interactions documented
              </div>
            </div>
          )}

          {/* AFI / Classical reference */}
          {(med.afi_reference || med.classical_text_reference) && (
            <div className="mv-afi-ref">
              <BookOpen size={11} />
              <div>
                {med.afi_reference && <div><strong>AFI:</strong> {med.afi_reference}</div>}
                {med.classical_text_reference && <div>{med.classical_text_reference}</div>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


export function MedicineView({ plan }) {
  const primary    = plan.primary_formulations || []
  const supporting = plan.supporting_formulations || []
  const external   = plan.external_therapies || []
  const schedule   = plan.dosage_schedule || []
  const protocol   = plan.treatment_protocol || {}
  const outcomes   = plan.expected_outcomes || {}
  const lifestyle  = plan.lifestyle_guidance || {}
  const blocked    = plan.blocked_medicines || []
  const rationale  = plan.formulation_rationale || {}
  const pathya     = plan.pathya || []
  const apathya    = plan.apathya || []
  const viruddha   = plan.viruddha_ahara_alerts || []

  const doshaColor = DOSHA_COLORS_R[plan.vikriti_dominant || plan.user_dosha] || DOSHA_COLORS_R.universal

  return (
    <div className="mv-view">

      {/* ── Intro ── */}
      {plan.personalized_intro && (
        <div className="rv-intro-card">
          <Stethoscope size={18} className="rv-intro-icon" />
          <p>{plan.personalized_intro}</p>
        </div>
      )}

      {/* ── Rare / unmapped condition coverage notice ── */}
      {plan.coverage_note && (
        <div className="mv-coverage-note">
          <TriangleAlert size={14} />
          <div>
            <strong>Limited classical coverage for your condition</strong>
            <p>{plan.coverage_note}</p>
          </div>
        </div>
      )}

      {/* ── Shodhana clinical gate ── */}
      {plan.chikitsa_approach === 'Shodhana' && (
        <div className="mv-shodhana-alert">
          <TriangleAlert size={14} />
          <div>
            <strong>Shodhana (Purification) Protocol Indicated</strong>
            <p>Your Vikriti and condition profile suggest a purification approach (Vamana/Virechana). This requires in-person evaluation and supervision by a qualified Vaidya. The formulations below support this direction but do not replace clinical Panchakarma.</p>
          </div>
        </div>
      )}

      {/* ── Chikitsa Sutra ── */}
      {plan.chikitsa_sutra && (
        <div className="mv-chikitsa-card">
          <div className="mv-chikitsa-label">
            <BookOpen size={14} />
            Chikitsa Sutra
            <span className="mv-approach-badge" style={{ background: plan.chikitsa_approach === 'Shodhana' ? '#f9731622' : '#22c55e22', color: plan.chikitsa_approach === 'Shodhana' ? '#f97316' : '#22c55e' }}>
              {plan.chikitsa_approach || 'Shamana'}
            </span>
          </div>
          <p className="mv-chikitsa-text">{plan.chikitsa_sutra}</p>
          {plan.agni_type && plan.vikriti_dominant && (
            <div className="mv-vitals-chips">
              <span className="mv-vital-chip"><Flame size={10} />{plan.vikriti_dominant} vikriti</span>
              {plan.vikriti_secondary && <span className="mv-vital-chip">{plan.vikriti_secondary} secondary</span>}
              <span className="mv-vital-chip"><Droplets size={10} />{plan.agni_type} agni</span>
              {plan.ama_level && plan.ama_level !== 'low' && <span className="mv-vital-chip" style={{ color: '#f59e0b' }}>ama: {plan.ama_level}</span>}
              {plan.current_season && <span className="mv-vital-chip"><Leaf size={10} />{plan.current_season}</span>}
            </div>
          )}
        </div>
      )}

      {/* ── Conditions banner ── */}
      {plan.active_conditions?.length > 0 && (
        <div className="mv-conditions-row">
          {plan.active_conditions.map((c, i) => (
            <span key={i} className="mv-cond-chip">{c.replace(/_/g, ' ')}</span>
          ))}
        </div>
      )}

      {/* ── Primary formulations ── */}
      {primary.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Pill size={16} />Primary Formulations</div>
          {primary.map((med, i) => <MedCard key={i} med={med} rationale={rationale[med.name]} />)}
        </div>
      )}

      {/* ── Supporting formulations ── */}
      {supporting.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Layers size={16} />Supporting Formulations</div>
          {supporting.map((med, i) => <MedCard key={i} med={med} rationale={rationale[med.name]} />)}
        </div>
      )}

      {/* ── External therapies ── */}
      {external.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Droplets size={16} />External Therapies (Taila)</div>
          {external.map((med, i) => <MedCard key={i} med={med} rationale={rationale[med.name]} />)}
        </div>
      )}

      {/* ── Daily dosage schedule ── */}
      {schedule.length > 0 && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Clock size={16} />Daily Dosage Schedule</div>
          {schedule.map((slot, i) => (
            <div key={i} className="mv-schedule-slot">
              <div className="mv-schedule-time">{slot.time}</div>
              {slot.medicines.map((m, j) => (
                <div key={j} className="mv-schedule-med">{m}</div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* ── Treatment protocol grid ── */}
      {(protocol.week_1_2 || protocol.week_3_4 || protocol.week_5_plus) && (
        <div className="mv-protocol-section">
          <div className="rv-block-title"><Calendar size={16} />Treatment Protocol</div>
          {protocol.dose_note && (
            <div className="mv-dose-note"><Flame size={12} />{protocol.dose_note}</div>
          )}
          <div className="mv-protocol-grid">
            {protocol.week_1_2 && (
              <div className="mv-protocol-col">
                <div className="mv-protocol-week">Week 1–2</div>
                <p className="mv-protocol-text">{protocol.week_1_2}</p>
              </div>
            )}
            {protocol.week_3_4 && (
              <div className="mv-protocol-col">
                <div className="mv-protocol-week">Week 3–4</div>
                <p className="mv-protocol-text">{protocol.week_3_4}</p>
              </div>
            )}
            {protocol.week_5_plus && (
              <div className="mv-protocol-col">
                <div className="mv-protocol-week">Week 5+</div>
                <p className="mv-protocol-text">{protocol.week_5_plus}</p>
              </div>
            )}
          </div>
          {protocol.total_duration && (
            <div className="mv-total-duration"><Clock size={11} />Total duration: <strong>{protocol.total_duration}</strong></div>
          )}
        </div>
      )}

      {/* ── Expected outcomes timeline ── */}
      {(outcomes.week_2 || outcomes.week_4 || outcomes.week_8) && (
        <div className="rv-section-block">
          <div className="rv-block-title"><Sparkles size={16} />Expected Outcomes</div>
          <div className="mv-outcomes-timeline">
            {outcomes.week_2 && (
              <div className="mv-outcome-milestone">
                <div className="mv-milestone-marker">Week 2</div>
                <p className="mv-milestone-text">{outcomes.week_2}</p>
              </div>
            )}
            {outcomes.week_4 && (
              <div className="mv-outcome-milestone">
                <div className="mv-milestone-marker">Week 4</div>
                <p className="mv-milestone-text">{outcomes.week_4}</p>
              </div>
            )}
            {outcomes.week_8 && (
              <div className="mv-outcome-milestone">
                <div className="mv-milestone-marker">Week 8</div>
                <p className="mv-milestone-text">{outcomes.week_8}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Synergy note ── */}
      {plan.synergy_note && (
        <div className="rv-info-card">
          <div className="rv-info-label"><Sparkles size={14} />Synergy of Formulations</div>
          <p className="rv-info-body">{plan.synergy_note}</p>
        </div>
      )}

      {/* ── Pathya-Apathya (structured lists) ── */}
      {(pathya.length > 0 || apathya.length > 0) && (
        <div className="mv-pathya-section">
          <div className="rv-block-title"><UtensilsCrossed size={16} />Pathya & Apathya</div>
          <div className="mv-pathya-grid">
            {pathya.length > 0 && (
              <div className="mv-pathya-col">
                <div className="mv-pathya-col-label do">✓ Pathya (Do)</div>
                {pathya.map((p, i) => <div key={i} className="mv-pathya-row do">{p}</div>)}
              </div>
            )}
            {apathya.length > 0 && (
              <div className="mv-pathya-col">
                <div className="mv-pathya-col-label dont">✗ Apathya (Avoid)</div>
                {apathya.map((p, i) => <div key={i} className="mv-pathya-row dont">{p}</div>)}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Viruddha Ahara alerts ── */}
      {viruddha.length > 0 && (
        <div className="mv-viruddha-card">
          <div className="mv-viruddha-label"><TriangleAlert size={13} />Viruddha Ahara — Incompatible Combinations</div>
          {viruddha.map((v, i) => (
            <div key={i} className="mv-viruddha-row">{v}</div>
          ))}
        </div>
      )}

      {/* ── Lifestyle guidance (Dosha base) ── */}
      {(lifestyle.dietary_note || lifestyle.routine_note || lifestyle.avoid?.length > 0) && (
        <div className="rv-info-card">
          <div className="rv-info-label" style={{ color: doshaColor }}>
            <Leaf size={14} />Lifestyle — {(plan.vikriti_dominant || plan.user_dosha)?.charAt(0).toUpperCase() + (plan.vikriti_dominant || plan.user_dosha)?.slice(1)} Vikriti
          </div>
          {lifestyle.dietary_note && <p className="rv-info-body">{lifestyle.dietary_note}</p>}
          {lifestyle.routine_note && <p className="rv-info-body" style={{ marginTop: 6 }}>{lifestyle.routine_note}</p>}
          {lifestyle.avoid?.length > 0 && (
            <div className="rv-avoid-row">
              {lifestyle.avoid.map((a, i) => <span key={i} className="rv-avoid-chip">{a}</span>)}
            </div>
          )}
        </div>
      )}

      {/* ── Monitoring signs ── */}
      {plan.monitoring_signs && (
        <div className="rv-info-card">
          <div className="rv-info-label"><Stethoscope size={14} />Monitoring & Follow-Up</div>
          <p className="rv-info-body">{plan.monitoring_signs}</p>
        </div>
      )}

      {/* ── When to stop ── */}
      {plan.when_to_stop && (
        <div className="rv-info-card rv-escalate">
          <div className="rv-info-label"><TriangleAlert size={14} />When to Stop & Consult Immediately</div>
          <p className="rv-info-body">{plan.when_to_stop}</p>
        </div>
      )}

      {/* ── Blocked medicines ── */}
      {blocked.length > 0 && (
        <div className="mv-blocked-section">
          <div className="rv-info-label"><TriangleAlert size={14} style={{ color: '#ef4444' }} />Medicines Excluded for Your Safety</div>
          {blocked.map((b, i) => (
            <div key={i} className="mv-blocked-item">
              <span className="mv-blocked-name">{b.name}</span>
              <span className="mv-blocked-reason">{b.reason}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Disclaimer ── */}
      {plan.disclaimer && (
        <div className="rv-disclaimer">
          <ShieldCheck size={12} />
          <span>{plan.disclaimer}</span>
        </div>
      )}
    </div>
  )
}

// ── RoutineView ───────────────────────────────────────────────────────────────
