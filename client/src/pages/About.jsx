import { Helmet } from 'react-helmet-async'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, GraduationCap, MapPin } from 'lucide-react'
import { tr } from '../lib/tr'
import { FOUNDER } from '../lib/founder'
import './Legal.css'
import './About.css'

const LINKS = [
  { href: FOUNDER.linkedin, label: 'LinkedIn' },
  { href: FOUNDER.github, label: 'GitHub' },
  { href: FOUNDER.website, label: 'bhavyaverdia.me' },
]

export default function About() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'AboutPage',
    url: 'https://ayuraai.in/about',
    name: 'About Ayura AI',
    mainEntity: {
      '@type': 'Person',
      name: FOUNDER.name,
      jobTitle: 'Founder, Ayura AI',
      url: FOUNDER.website,
      sameAs: [FOUNDER.linkedin, FOUNDER.github],
      alumniOf: { '@type': 'CollegeOrUniversity', name: 'MIT ADT University' },
      worksFor: { '@id': 'https://ayuraai.in/#organization' },
    },
  }

  return (
    <div className="legal-page about-page">
      <Helmet>
        <title>About the Founder | Ayura AI</title>
        <meta name="description" content="Ayura AI is built by Bhavya Verdia, an AI engineer from Udaipur, Rajasthan: personalised Ayurvedic plans built from authored knowledge and screened for your health before you see them." />
        <link rel="canonical" href="https://ayuraai.in/about" />
        <meta property="og:url" content="https://ayuraai.in/about" />
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      </Helmet>

      <Link to="/" className="legal-back">
        <ArrowLeft size={16} /> {tr('ui.about.back', 'Back to Home')}
      </Link>

      <div className="legal-header">
        <h1>{tr('ui.about.title', 'Meet the founder')}</h1>
        <p>{tr('ui.about.subtitle', 'The person behind Ayura AI, and why it is built the way it is.')}</p>
      </div>

      <section className="about-card" aria-labelledby="about-name">
        <div className="about-avatar" aria-hidden="true">BV</div>
        <div>
          <h2 id="about-name" className="about-name">{FOUNDER.name}</h2>
          <p className="about-role">{tr('ui.about.role', 'Founder, Ayura AI · AI & Analytics Engineer')}</p>
          <ul className="about-facts">
            <li><MapPin size={15} aria-hidden="true" /> {tr('ui.about.location', 'Udaipur, Rajasthan, India')}</li>
            <li><GraduationCap size={15} aria-hidden="true" /> {tr('ui.about.education', 'B.Tech Computer Science (AI & Analytics), MIT ADT University, Pune')}</li>
          </ul>
          <ul className="about-links">
            {LINKS.map(({ href, label }) => (
              <li key={href}>
                <a href={href} target="_blank" rel="noopener noreferrer me">
                  {label} <ArrowUpRight size={14} aria-hidden="true" />
                </a>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div className="legal-content">
        <h2>{tr('ui.about.bioHeading', 'About Bhavya')}</h2>
        <p>
          {tr('ui.about.bio1', 'Bhavya Verdia is an AI engineer who works on the gap between a promising model and a system people can rely on: evaluation, guardrails, and the last-mile engineering that makes AI safe to put in front of real users.')}
        </p>

        <h2>{tr('ui.about.whyHeading', 'Why Ayura AI is built this way')}</h2>
        <p>
          {tr('ui.about.why1', 'A general-purpose chatbot will happily invent a herbal formulation or a yoga pose that does not exist. For health guidance, that is not good enough. Ayura AI is built the other way round:')}
        </p>
        <ul>
          <li>{tr('ui.about.point1', 'Your plan comes from rule engines over hand-authored Ayurvedic knowledge: foods, exercises, asanas, remedies and therapies. AI adds explanation and coaching on top; it does not invent the plan.')}</li>
          <li>{tr('ui.about.point2', 'Every plan is checked against your health conditions, allergies, medicines, injuries, age and pregnancy before you see it, and anything withheld is shown with the reason.')}</li>
          <li>{tr('ui.about.point3', 'It is made for India: vegetarian and vegan meals, regional cuisines, Indian medicine brand names, and eight languages.')}</li>
        </ul>

        <div className="legal-important">
          <strong>{tr('ui.about.noteHeading', 'A note on safety')}</strong>
          <p style={{ marginBottom: 0, color: 'inherit' }}>
            {tr('ui.about.note', 'Ayura AI offers wellness guidance, not medical care. It does not replace a doctor or a qualified Vaidya. See the Terms of Service for details.')}{' '}
            <Link to="/terms">{tr('ui.about.termsLink', 'Terms of Service')}</Link>
          </p>
        </div>

        <h2>{tr('ui.about.contactHeading', 'Get in touch')}</h2>
        <p>
          {tr('ui.about.contact', 'For feedback, partnerships or press, reach Bhavya on LinkedIn.')}
        </p>
      </div>
    </div>
  )
}
