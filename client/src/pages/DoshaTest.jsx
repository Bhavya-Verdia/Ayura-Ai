import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { useAuth } from '../providers/AuthContext'
import { Wind, Flame, Mountain, ClipboardList, Sparkles, HeartPulse, Salad, Sun } from 'lucide-react'
import './Landing.css'
import './DoshaTest.css'

const DOSHAS = [
  {
    name: 'Vata',
    sanskrit: 'वात',
    elements: 'Air + Ether',
    Icon: Wind,
    color: '#a78bfa',
    summary: 'The energy of movement — governs breath, circulation, and the nervous system.',
    balanced: 'Creative, energetic, quick-thinking, adaptable.',
    imbalanced: 'Anxiety, dry skin, bloating, restlessness, irregular sleep.',
    traits: ['Light, lean frame', 'Dry skin & hair', 'Fast, active mind', 'Variable appetite'],
  },
  {
    name: 'Pitta',
    sanskrit: 'पित्त',
    elements: 'Fire + Water',
    Icon: Flame,
    color: '#f97316',
    summary: 'The energy of transformation — governs digestion, metabolism, and intellect.',
    balanced: 'Focused, ambitious, sharp intellect, strong digestion.',
    imbalanced: 'Irritability, acidity, inflammation, skin rashes, overheating.',
    traits: ['Medium, athletic build', 'Warm body, strong appetite', 'Sharp, goal-driven mind', 'Sound but light sleep'],
  },
  {
    name: 'Kapha',
    sanskrit: 'कफ',
    elements: 'Earth + Water',
    Icon: Mountain,
    color: '#34d399',
    summary: 'The energy of structure — governs immunity, strength, and stability.',
    balanced: 'Calm, loving, patient, strong stamina and immunity.',
    imbalanced: 'Weight gain, sluggishness, congestion, attachment, low motivation.',
    traits: ['Solid, sturdy build', 'Smooth, oily skin', 'Calm, steady temperament', 'Deep, long sleep'],
  },
]

const STEPS = [
  { Icon: ClipboardList, title: 'Answer a guided assessment', desc: 'A short questionnaire rooted in the classical Ashtavidha Pariksha — covering your body, digestion, energy, sleep, and temperament.' },
  { Icon: Sparkles, title: 'AI analyses your constitution', desc: 'Ayura AI scores your responses across Vata, Pitta, and Kapha to determine your dominant dosha — your Prakriti.' },
  { Icon: HeartPulse, title: 'Get your dosha profile', desc: 'See your dominant dosha with a confidence reading and a clear explanation of what it means for your mind and body.' },
  { Icon: Salad, title: 'Unlock personalised plans', desc: 'Turn your result into tailored diet, yoga, daily-routine, detox, and herbal-remedy plans built around your constitution.' },
]

const BENEFITS = [
  { Icon: Salad, title: 'Eat for your body type', desc: 'Know which foods balance your dosha and which aggravate it — no generic diets.' },
  { Icon: Sun, title: 'Build the right daily routine', desc: 'A Dinacharya (daily rhythm) matched to your constitution and the season.' },
  { Icon: HeartPulse, title: 'Prevent imbalance early', desc: 'Spot the signs of Vata, Pitta, or Kapha excess before they become problems.' },
  { Icon: Sparkles, title: 'Train and rest smarter', desc: 'Yoga, pranayama, and exercise intensities suited to your energy and tendencies.' },
]

const FAQS = [
  {
    q: 'What is a dosha test?',
    a: 'A dosha test is an Ayurvedic assessment that identifies your Prakriti — your natural mind-body constitution, made up of three doshas: Vata, Pitta, and Kapha. Knowing your dominant dosha lets you tailor diet, exercise, and lifestyle to keep yourself in balance.',
  },
  {
    q: 'Is the Ayura AI dosha test free?',
    a: 'Yes. The dosha test is completely free. Create an account, answer the guided questions, and get your dosha profile plus personalised wellness plans at no cost — no credit card required.',
  },
  {
    q: 'What are Vata, Pitta, and Kapha?',
    a: 'They are the three doshas — the biological energies that govern every function in the body. Vata (Air + Ether) controls movement, Pitta (Fire + Water) controls metabolism and digestion, and Kapha (Earth + Water) controls structure and immunity. Everyone has all three, in a unique ratio.',
  },
  {
    q: 'How accurate is the Ayura AI dosha test?',
    a: 'The test uses a deterministic scoring system based on the classical Ashtavidha Pariksha (eightfold examination) rather than a generic personality quiz, and it reports a confidence level with your result so you know how clear your dominant dosha is.',
  },
  {
    q: 'How long does the dosha test take?',
    a: 'Most people complete the assessment in just a few minutes. You answer a short set of questions about your physical traits, digestion, energy, sleep, and temperament.',
  },
  {
    q: 'Can my dosha change over time?',
    a: 'Your Prakriti (birth constitution) stays the same for life, but your current state — called Vikriti — shifts with diet, season, stress, and age. Ayura AI tracks both so your plans adapt as your balance changes.',
  },
]

export default function DoshaTest() {
  const { user } = useAuth()
  const ctaPath = user ? '/dosha-quiz' : '/register'

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebPage',
        '@id': 'https://ayuraai.in/dosha-test#webpage',
        url: 'https://ayuraai.in/dosha-test',
        name: 'Free Dosha Test — Discover Your Ayurvedic Body Type',
        description: 'Take a free Ayurvedic dosha test to find your Prakriti (Vata, Pitta, or Kapha) and unlock personalised diet, yoga, and lifestyle plans from Ayura AI.',
        isPartOf: { '@id': 'https://ayuraai.in/#website' },
        inLanguage: 'en-IN',
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://ayuraai.in' },
          { '@type': 'ListItem', position: 2, name: 'Dosha Test', item: 'https://ayuraai.in/dosha-test' },
        ],
      },
      {
        '@type': 'FAQPage',
        '@id': 'https://ayuraai.in/dosha-test#faq',
        mainEntity: FAQS.map(f => ({
          '@type': 'Question',
          name: f.q,
          acceptedAnswer: { '@type': 'Answer', text: f.a },
        })),
      },
    ],
  }

  return (
    <div className="landing-root">
      <Helmet>
        <title>Free Dosha Test — Find Your Ayurvedic Body Type (Vata, Pitta, Kapha) | Ayura AI</title>
        <meta name="description" content="Take Ayura AI's free dosha test to discover your Prakriti — Vata, Pitta, or Kapha. Get an accurate Ayurvedic body-type result and personalised diet, yoga, and lifestyle plans." />
        <link rel="canonical" href="https://ayuraai.in/dosha-test" />
        <meta name="keywords" content="dosha test, free dosha test, prakriti test, vata pitta kapha test, ayurveda body type quiz, ayurvedic constitution test, what is my dosha" />
        <meta property="og:title" content="Free Dosha Test — Find Your Ayurvedic Body Type | Ayura AI" />
        <meta property="og:description" content="Discover your Prakriti (Vata, Pitta, or Kapha) with Ayura AI's free Ayurvedic dosha test, then get personalised wellness plans." />
        <meta property="og:url" content="https://ayuraai.in/dosha-test" />
        <meta name="twitter:title" content="Free Dosha Test — Find Your Ayurvedic Body Type | Ayura AI" />
        <meta name="twitter:description" content="Discover your Prakriti (Vata, Pitta, or Kapha) with Ayura AI's free Ayurvedic dosha test." />
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      </Helmet>

      {/* ── NAVBAR ── */}
      <header className="lnd-nav-wrap scrolled">
        <nav className="lnd-nav">
          <Link to="/" className="lnd-brand">
            <div className="lnd-brand-mark-wrap">
              <img src="/favicon.svg" alt="Ayura AI Logo" className="lnd-brand-mark" />
            </div>
            <span className="lnd-brand-text">
              Ayura <span style={{ color: 'var(--ayura-teal)', fontWeight: 800 }}>AI</span>
            </span>
          </Link>
          <div className="lnd-nav-actions">
            {user ? (
              <Link to="/dashboard" className="lnd-nav-link">Dashboard</Link>
            ) : (
              <Link to="/login" className="lnd-nav-link">Sign In</Link>
            )}
            <Link to={ctaPath} className="lnd-cta-pill">Take the test ↗</Link>
          </div>
        </nav>
      </header>

      {/* ── HERO ── */}
      <section className="dt-hero">
        <span className="lnd-section-kicker">Free Ayurvedic Assessment</span>
        <h1 className="dt-hero-title">
          Free Dosha Test — discover your <span className="dt-grad">Ayurvedic body type</span>
        </h1>
        <p className="dt-hero-sub">
          Find out whether you are <strong>Vata</strong>, <strong>Pitta</strong>, or <strong>Kapha</strong>.
          Ayura AI's dosha test reveals your Prakriti — your natural mind-body constitution — and turns it
          into personalised diet, yoga, daily-routine, and herbal-remedy plans.
        </p>
        <div className="dt-hero-actions">
          <Link to={ctaPath} className="lnd-cta-main">Take the free dosha test →</Link>
          <a href="#three-doshas" className="lnd-cta-secondary">Learn about the doshas</a>
        </div>
        <p className="dt-hero-note">Takes a few minutes · No credit card · Results explained in plain language</p>
      </section>

      {/* ── WHAT IS A DOSHA TEST ── */}
      <section className="lnd-section dt-intro">
        <h2 className="lnd-section-title">What is a dosha test?</h2>
        <p className="lnd-section-desc">
          In Ayurveda, your <strong>Prakriti</strong> is your unique constitution — the balance of the three
          doshas you were born with. A dosha test identifies your dominant dosha so you can eat, move, and live
          in a way that keeps you balanced. Unlike a generic personality quiz, Ayura AI's test is grounded in the
          classical <em>Ashtavidha Pariksha</em> and reports how confident the result is.
        </p>
      </section>

      {/* ── THE THREE DOSHAS ── */}
      <section id="three-doshas" className="lnd-section" style={{ paddingTop: 0 }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <span className="lnd-section-kicker">The Foundations</span>
          <h2 className="lnd-section-title">Vata, Pitta & Kapha</h2>
        </div>
        <div className="dt-dosha-grid">
          {DOSHAS.map(d => {
            const { Icon } = d
            return (
              <article key={d.name} className="dt-dosha-card" style={{ '--dosha': d.color }}>
                <div className="dt-dosha-head">
                  <span className="dt-dosha-icon"><Icon size={22} strokeWidth={2} /></span>
                  <div>
                    <h3 className="dt-dosha-name">{d.name} <span className="dt-dosha-sanskrit">{d.sanskrit}</span></h3>
                    <span className="dt-dosha-elements">{d.elements}</span>
                  </div>
                </div>
                <p className="dt-dosha-summary">{d.summary}</p>
                <div className="dt-dosha-row"><span className="dt-dosha-label balanced">In balance</span><span>{d.balanced}</span></div>
                <div className="dt-dosha-row"><span className="dt-dosha-label imbalanced">Out of balance</span><span>{d.imbalanced}</span></div>
                <ul className="dt-dosha-traits">
                  {d.traits.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </article>
            )
          })}
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="lnd-section" style={{ paddingTop: 0 }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <span className="lnd-section-kicker">How it works</span>
          <h2 className="lnd-section-title">How the Ayura AI dosha test works</h2>
        </div>
        <div className="dt-steps-grid">
          {STEPS.map((s, i) => {
            const { Icon } = s
            return (
              <div key={i} className="dt-step-card">
                <span className="dt-step-num">{i + 1}</span>
                <span className="dt-step-icon"><Icon size={20} strokeWidth={2} /></span>
                <h3 className="dt-step-title">{s.title}</h3>
                <p className="dt-step-desc">{s.desc}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── BENEFITS ── */}
      <section className="lnd-section" style={{ paddingTop: 0 }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <span className="lnd-section-kicker">Why it matters</span>
          <h2 className="lnd-section-title">Why know your dosha?</h2>
        </div>
        <div className="dt-benefit-grid">
          {BENEFITS.map((b, i) => {
            const { Icon } = b
            return (
              <div key={i} className="dt-benefit-card">
                <span className="dt-benefit-icon"><Icon size={20} strokeWidth={2} /></span>
                <h3 className="dt-benefit-title">{b.title}</h3>
                <p className="dt-benefit-desc">{b.desc}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="lnd-section" style={{ paddingTop: 0 }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <span className="lnd-section-kicker">Questions</span>
          <h2 className="lnd-section-title">Dosha test — FAQs</h2>
        </div>
        <div className="lnd-faq-list">
          {FAQS.map((item, i) => (
            <details key={i} className="lnd-faq-item">
              <summary className="lnd-faq-q">
                <span>{item.q}</span>
                <span className="lnd-faq-icon" aria-hidden="true">+</span>
              </summary>
              <p className="lnd-faq-a">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="lnd-cta-section">
        <div className="lnd-cta-box">
          <h2 className="lnd-cta-box-title">Discover your dosha in minutes</h2>
          <p className="lnd-cta-box-desc">
            Take the free dosha test and unlock personalised Ayurvedic plans for diet, yoga, daily routine,
            detox, and herbal remedies — all tailored to your constitution.
          </p>
          <div className="lnd-cta-box-actions">
            <Link to={ctaPath} className="lnd-cta-main">{user ? 'Take the dosha test →' : 'Start free — no card needed →'}</Link>
            {!user && <Link to="/login" className="lnd-cta-secondary">Sign In</Link>}
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="dt-footer">
        <div className="dt-footer-inner">
          <Link to="/" className="lnd-brand">
            <img src="/favicon.svg" alt="Ayura AI Logo" className="lnd-brand-mark" />
            <span className="lnd-brand-text">Ayura AI</span>
          </Link>
          <nav className="dt-footer-links">
            <Link to="/">Home</Link>
            <Link to="/register">Get Started</Link>
            <Link to="/terms">Terms</Link>
            <Link to="/privacy">Privacy</Link>
          </nav>
          <p className="dt-footer-copy">
            © {new Date().getFullYear()} Ayura AI. Ayurvedic wellness guidance for informational purposes only — not a substitute for professional medical advice.
          </p>
        </div>
      </footer>
    </div>
  )
}
