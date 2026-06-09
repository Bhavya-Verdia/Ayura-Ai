import React from 'react';
import './PlanViewer.css';

// Determines if an array contains objects (which should be rendered as cards)
const isObjectArray = (arr) => Array.isArray(arr) && arr.length > 0 && typeof arr[0] === 'object' && arr[0] !== null;

// Heuristic to pick a title key for a card
const getCardTitle = (obj) => {
const possibleTitleKeys = ['day_name', 'pose', 'name', 'meal', 'remedy_name', 'medicine_name', 'focus', 'therapy'];
  for (const key of possibleTitleKeys) {
    if (obj[key]) return obj[key];
  }
  // Fallback: first string property
  for (const [, v] of Object.entries(obj)) {
    if (typeof v === 'string') return v;
  }
  return 'Item';
};

function renderValue(val) {
  if (!val) return null;
  
  if (typeof val === 'string') {
    return <p className="plan-string-val">{val}</p>;
  }
  
  if (Array.isArray(val)) {
    if (isObjectArray(val)) {
      return (
        <div className="plan-grid">
          {val.map((item, i) => {
            const title = getCardTitle(item);
            const otherEntries = Object.entries(item).filter(([, v]) => v !== title);
            
            return (
              <div key={i} className="plan-card">
                <div className="plan-card-title">✦ {title}</div>
                {otherEntries.map(([k, v]) => {
                  if (k === 'safety_tier' || k === 'safety_level') {
                    const tierStr = String(v).toLowerCase();
                    let tierColor = 'var(--text-primary)';
                    if (tierStr.includes('high') || tierStr.includes('caution')) tierColor = 'var(--ayura-rose)';
                    else if (tierStr.includes('medium')) tierColor = 'var(--ayura-amber)';
                    else if (tierStr.includes('low') || tierStr.includes('safe')) tierColor = 'var(--ayura-teal)';
                    
                    return (
                      <div key={k} className="plan-card-item">
                        <span className="plan-card-label">Safety Tier</span>
                        <span className="plan-card-value" style={{ color: tierColor, fontWeight: 700, padding: '2px 8px', background: `${tierColor}15`, borderRadius: '12px', display: 'inline-block' }}>{v}</span>
                      </div>
                    );
                  }
                  
                  if (typeof v === 'string' || typeof v === 'number') {
                    return (
                      <div key={k} className="plan-card-item">
                        <span className="plan-card-label">{k.replace(/_/g, ' ')}</span>
                        <span className="plan-card-value">{v}</span>
                      </div>
                    );
                  } else if (Array.isArray(v) && v.every(x => typeof x === 'string')) {
                    return (
                      <div key={k} className="plan-card-item">
                        <span className="plan-card-label">{k.replace(/_/g, ' ')}</span>
                        <ul className="plan-list" style={{ marginTop: '4px', marginBottom: 0 }}>
                          {v.map((str, idx) => <li key={idx} className="plan-list-item">{str}</li>)}
                        </ul>
                      </div>
                    );
                  }
                  return (
                    <div key={k} className="plan-card-item-complex" style={{ marginTop: '12px' }}>
                      <span className="plan-card-label" style={{ marginBottom: '4px', display: 'block' }}>{k.replace(/_/g, ' ')}</span>
                      {renderValue(v)}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      );
    } else {
      return (
        <ul className="plan-list">
          {val.map((item, i) => (
            <li key={i} className="plan-list-item">{String(item)}</li>
          ))}
        </ul>
      );
    }
  }
  
  if (typeof val === 'object') {
    return (
      <div className="plan-nested-obj">
        {Object.entries(val).map(([k, v]) => (
          <div key={k}>
            <div className="plan-key-title">{k.replace(/_/g, ' ')}</div>
            {renderValue(v)}
          </div>
        ))}
      </div>
    );
  }
  
  return <span className="plan-string-val">{String(val)}</span>;
}

const SKIP_KEYS = ['user_summary', 'generated_at', 'generation_method', 'model_used', 'id', 'ratings', 'safety_checks', 'daily_tip', 'disclaimer', 'medical_disclaimer', 'plan_id', 'enrichment_model', 'enriched', 'type', 'phase_breakdown'];

const SECTION_KEY_MAP = {
  routine:     'routine_plan',
  yoga:        'yoga_plan',
  gym:         'gym_plan',
  diet:        'diet_plan',
  panchakarma: 'panchakarma_plan',
  remedies:    'home_remedies',
  medicines:   'medicines',
};

const ICONS = {
  routine_plan: '🌅',
  yoga_plan: '🧘‍♀️',
  gym_plan: '🏋️‍♂️',
  diet_plan: '🥗',
  panchakarma_plan: '🌿',
  home_remedies: '🍵',
  medicines: '💊',
};

export default function PlanViewer({ plan, planType }) {
  if (!plan) return <p style={{ color: 'var(--text-secondary)' }}>No plan data available.</p>;

  const sectionKey = planType ? SECTION_KEY_MAP[planType] : null;
  const sections = sectionKey && plan[sectionKey]
    ? { [sectionKey]: plan[sectionKey] }
    : Object.fromEntries(Object.entries(plan).filter(([k]) => !SKIP_KEYS.includes(k) && plan[k]));

  return (
    <div className="plan-viewer-container">
      {/* User summary banner */}
      {plan.user_summary && (
        <div className="plan-summary-banner">
          <div className="plan-summary-name">Good morning, {plan.user_summary.name.split(' ')[0]}</div>
          {plan.user_summary.dominant_dosha && (
            <div style={{ color: '#cbd5e1', fontSize: '0.95rem' }}>
              Your dominant dosha is 
              <span className="plan-dosha-badge">{plan.user_summary.dominant_dosha}</span>
            </div>
          )}
          {plan.daily_tip && (
            <div className="plan-daily-tip">
              <span>💡</span> <span>{plan.daily_tip}</span>
            </div>
          )}
        </div>
      )}

      {/* Main sections */}
      {Object.entries(sections).map(([key, value]) => {
        const icon = ICONS[key] || '✨';
        return value ? (
          <div key={key} className="plan-section">
            <h3 className="plan-section-title">
              <span style={{ fontSize: '1.6rem' }}>{icon}</span> {key.replace(/_/g, ' ')}
            </h3>
            {renderValue(value)}
          </div>
        ) : null;
      })}

      {/* Safety warnings & Disclaimers */}
      {(plan.safety_checks?.warnings?.length > 0 || plan.disclaimer || plan.medical_disclaimer) && (
        <div className="plan-safety-box" style={{ marginTop: '32px', borderLeft: '4px solid var(--ayura-rose)', padding: '16px', background: 'rgba(251, 113, 133, 0.08)', borderRadius: '8px' }}>
          <div className="plan-safety-title" style={{ fontWeight: 'bold', marginBottom: '8px', color: 'var(--text-primary)' }}>⚠️ Important Safety & Medical Notes</div>
          
          {plan.safety_checks?.warnings?.length > 0 && (
            <ul className="plan-safety-list" style={{ marginLeft: '16px', marginBottom: '12px' }}>
              {plan.safety_checks.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}

          {(plan.disclaimer || plan.medical_disclaimer) && (
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
              {plan.disclaimer || plan.medical_disclaimer}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
