import { useRef, useEffect, useState, Suspense } from 'react'
import { Link } from 'react-router-dom'
import Lenis from 'lenis'
import { m, AnimatePresence, MotionConfig } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import useLowPowerMode from '../hooks/useLowPowerMode'
import { useAuth } from '../providers/AuthContext'
import { useTheme } from '../providers/ThemeProvider'
import { SUPPORTED_LANGUAGES, setLanguage } from '../i18n'
// English source strings, used directly (not via t()) for SEO structured data
// so the JSON-LD stays canonical-English even after a visitor switches language.
import enLocale from '../locales/en.json'
import { Helmet } from 'react-helmet-async'
import React from 'react'
import CursorGlow from '../components/CursorGlow'
import MagneticButton from '../components/MagneticButton'
import CountUp from '../components/CountUp'
import { DOSHA_COLOR } from '../constants/dosha'
import {
  ShieldCheck, Sparkles, Leaf, Zap, Dna, Dumbbell,
  Salad, Pill, Flower2, Soup, HeartPulse, TriangleAlert, Check,
  Sun, Moon, Languages,
} from 'lucide-react'
import './Landing.css'

// ─── Animation variants ───────────────────────────────────────
// NO filter/blur here: the per-word blur entrance left every hero word in its
// own filtered render surface (even blur(0px) counts), and they flashed empty
// whenever drag-selection over the headline changed. Opacity+y only.
const wordVariants = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0 },
}
const stagger = { visible: { transition: { staggerChildren: 0.09 } } }
const fadeUp   = { hidden: { opacity: 0, y: 36 }, visible: { opacity: 1, y: 0 } }
const fadeLeft = { hidden: { opacity: 0, x: -48 }, visible: { opacity: 1, x: 0 } }
const fadeRight= { hidden: { opacity: 0, x:  48 }, visible: { opacity: 1, x: 0 } }
const VP       = { once: true, margin: '-60px' }

// Hero title is word-staggered at render time: t('landing.hero_title') split
// on spaces, plus the shimmer accent word from landing.hero_title_accent.

// True when this module loads over PRERENDERED HTML (cold visit to "/"): the
// hero already exists in the DOM before React hydrates. In that case skip the
// hero entrance animations — re-animating content the visitor is already
// reading looks like a glitch, and the re-paint pushes the LCP timestamp from
// first paint (~1.6s) to post-hydration (~3s) on slow devices. Client-side
// navigations to "/" (no prerendered DOM at module load) keep the entrance.
const PRERENDERED = typeof document !== 'undefined' && !!document.querySelector('.lnd-hero-subtitle')

// All user-visible copy lives in the locale files under "landing.*" — arrays
// below hold translation keys, resolved with t() at render so the language
// switcher re-renders the whole page.

// ─── How it works cards ───────────────────────────────────────
const HOW_CARDS = [
  { id: 'profile', step: 'landing.how1_step', Icon: Dna,        title: 'landing.how1_title', desc: 'landing.how1_desc' },
  { id: 'plans',   step: 'landing.how2_step', Icon: Sparkles,   title: 'landing.how2_title', desc: 'landing.how2_desc' },
  { id: 'sync',    step: 'landing.how3_step', Icon: HeartPulse, title: 'landing.how3_title', desc: 'landing.how3_desc' },
]

// ─── Feature sections ─────────────────────────────────────────
const FEATURES = [
  {
    tag: 'landing.feat1_tag',
    title: 'landing.feat1_title',
    desc: 'landing.feat1_desc',
    list: ['landing.feat1_li1', 'landing.feat1_li2', 'landing.feat1_li3'],
    Icon: Dna,
    reversed: false,
    Visual: DoshaFeatureVisual,
  },
  {
    tag: 'landing.feat2_tag',
    title: 'landing.feat2_title',
    desc: 'landing.feat2_desc',
    list: ['landing.feat2_li1', 'landing.feat2_li2', 'landing.feat2_li3'],
    Icon: Dumbbell,
    reversed: true,
    Visual: PlansFeatureVisual,
  },
  {
    tag: 'landing.feat3_tag',
    title: 'landing.feat3_title',
    desc: 'landing.feat3_desc',
    list: ['landing.feat3_li1', 'landing.feat3_li2', 'landing.feat3_li3'],
    Icon: ShieldCheck,
    reversed: false,
    Visual: SafetyFeatureVisual,
  },
]

// ─── Testimonials ─────────────────────────────────────────────
const TESTIMONIALS = [
  { id: 't1', name: 'landing.t1_name', location: 'landing.t1_loc', dosha: 'dosha_pitta', doshaColor: DOSHA_COLOR.pitta, initials: 'PS', quote: 'landing.t1_quote', stars: 5 },
  { id: 't2', name: 'landing.t2_name', location: 'landing.t2_loc', dosha: 'dosha_vata',  doshaColor: DOSHA_COLOR.vata,  initials: 'AM', quote: 'landing.t2_quote', stars: 5 },
  { id: 't3', name: 'landing.t3_name', location: 'landing.t3_loc', dosha: 'dosha_kapha', doshaColor: DOSHA_COLOR.kapha, initials: 'NK', quote: 'landing.t3_quote', stars: 5 },
]

// ─── Plan showcase ────────────────────────────────────────────
const mix = (v, pct) => `color-mix(in srgb, ${v} ${pct}%, transparent)`
const PLAN_SHOWCASE = [
  { id: 'yoga',        Icon: Flower2,  tint: 'var(--ayura-teal)',    title: 'landing.plan_yoga_t', desc: 'landing.plan_yoga_d', clr: mix('var(--ayura-teal)', 10) },
  { id: 'gym',         Icon: Dumbbell, tint: 'var(--vata-color)',    title: 'landing.plan_gym_t',  desc: 'landing.plan_gym_d',  clr: mix('var(--vata-color)', 10) },
  { id: 'diet',        Icon: Salad,    tint: 'var(--ayura-violet)',  title: 'landing.plan_diet_t', desc: 'landing.plan_diet_d', clr: mix('var(--ayura-violet)', 10) },
  { id: 'panchakarma', Icon: Leaf,     tint: 'var(--ayura-emerald)', title: 'landing.plan_pk_t',   desc: 'landing.plan_pk_d',   clr: mix('var(--ayura-emerald)', 10) },
  { id: 'remedies',    Icon: Soup,     tint: 'var(--ayura-rose)',    title: 'landing.plan_rem_t',  desc: 'landing.plan_rem_d',  clr: mix('var(--ayura-rose)', 9) },
  { id: 'medicines',   Icon: Pill,     tint: 'var(--ayura-amber)',   title: 'landing.plan_med_t',  desc: 'landing.plan_med_d',  clr: mix('var(--ayura-amber)', 10) },
]

// ─── Trust bar items ──────────────────────────────────────────
const TRUST_ITEMS = [
  { Icon: ShieldCheck, label: 'landing.trust_privacy' },
  { Icon: Sparkles,    label: 'landing.trust_ai' },
  { Icon: Leaf,        label: 'landing.trust_ayurveda' },
  { Icon: Zap,         label: 'landing.trust_free' },
]

// ─── Stats strip data ─────────────────────────────────────────
const STATS = [
  { id: 'plans',   label: 'landing.stats_plans',   countTo: 5200, suffix: '+' },
  { id: 'pillars', label: 'landing.stats_pillars', countTo: 6 },
  { id: 'safety',  label: 'landing.stats_safety',  countTo: 100,  suffix: '%' },
  { id: 'advisor', label: 'landing.stats_advisor', static: '24/7' },
]

// ─── Feature Mini-UI Visual components ───────────────────────
const DOSHA_BARS = [
  { label: 'dosha_vata',  cls: 'vata',  color: DOSHA_COLOR.vata,  pct: '65%', val: 65 },
  { label: 'dosha_pitta', cls: 'pitta', color: DOSHA_COLOR.pitta, pct: '45%', val: 45 },
  { label: 'dosha_kapha', cls: 'kapha', color: DOSHA_COLOR.kapha, pct: '30%', val: 30 },
]

function DoshaFeatureVisual() {
  const { t } = useTranslation()
  return (
    <div className="lnd-app-preview fmv-fill">
      <div className="lnd-prev-header">
        <span className="lnd-prev-brand">{t('landing.v_constitution')}</span>
        <span className="lnd-prev-badge" style={{ color: 'var(--vata-color)', background: 'color-mix(in srgb, var(--vata-color) 14%, transparent)', borderColor: 'color-mix(in srgb, var(--vata-color) 30%, transparent)' }}>Vata–Pitta</span>
      </div>
      <div className="lnd-dosha-gauge">
        <div className="lnd-dosha-gauge-title">{t('landing.v_dosha_balance')}</div>
        {DOSHA_BARS.map((d, i) => (
          <div key={d.label} className="lnd-dosha-row">
            <span className="lnd-dosha-label" style={{ color: d.color }}>{t(d.label)}</span>
            <div className="lnd-dosha-bar-track">
              <m.div
                className={`lnd-dosha-bar-fill ${d.cls}`}
                initial={{ width: 0 }}
                whileInView={{ width: d.pct }}
                viewport={{ once: true, amount: 0.5 }}
                transition={{ duration: 1.1, delay: 0.12 * i, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
            <span className="lnd-dosha-val">{d.val}</span>
          </div>
        ))}
      </div>
      <div className="fmv-insight-chips">
        {['landing.v_chip_prakriti', 'landing.v_chip_vikriti', 'landing.v_chip_season'].map(chip => (
          <span key={chip} className="fmv-chip">{t(chip)}</span>
        ))}
      </div>
      <div className="fmv-rec-card">
        <span className="fmv-rec-label">{t('landing.v_today_focus')}</span>
        <p className="fmv-rec-val">{t('landing.v_today_focus_text')}</p>
      </div>
    </div>
  )
}

const MINI_PLANS = [
  { Icon: Flower2,  name: 'landing.m_yoga', status: 'ready' },
  { Icon: Dumbbell, name: 'landing.m_gym',  status: 'ready' },
  { Icon: Salad,    name: 'landing.m_diet', status: 'ready' },
  { Icon: Leaf,     name: 'landing.m_pk',   status: 'ready' },
  { Icon: Soup,     name: 'landing.m_rem',  status: 'generating' },
  { Icon: Pill,     name: 'landing.m_med',  status: 'queued' },
]

function PlansFeatureVisual() {
  const { t } = useTranslation()
  return (
    <div className="lnd-app-preview fmv-fill">
      <div className="lnd-prev-header">
        <span className="lnd-prev-brand">{t('landing.v_wellness_plans')}</span>
        <span className="lnd-prev-badge">{t('landing.v_ready_badge')}</span>
      </div>
      <div className="lnd-prev-plans fmv-plans-grid">
        {MINI_PLANS.map(p => (
          <div key={p.name} className={`lnd-prev-plan${p.status === 'generating' ? ' fmv-generating' : ''}`}>
            <div className="lnd-prev-plan-icon"><p.Icon size={20} strokeWidth={1.8} /></div>
            <div className="lnd-prev-plan-name">{t(p.name)}</div>
            <div className={`lnd-prev-plan-status fmv-status-${p.status}`}>
              {p.status === 'ready' ? t('landing.v_ready') : p.status === 'generating' ? t('landing.v_crafting') : t('landing.v_queued')}
            </div>
          </div>
        ))}
      </div>
      <div className="fmv-footer-note">{t('landing.v_plans_note')}</div>
    </div>
  )
}

const SAFETY_CHECKS = [
  { herb: 'landing.v_herb1', result: 'pass', note: 'landing.v_note1' },
  { herb: 'landing.v_herb2', result: 'pass', note: 'landing.v_note2' },
  { herb: 'landing.v_herb3', result: 'pass', note: 'landing.v_note3' },
  { herb: 'landing.v_herb4', result: 'warn', note: 'landing.v_note4' },
  { herb: 'landing.v_herb5', result: 'pass', note: 'landing.v_note5' },
]

function SafetyFeatureVisual() {
  const { t } = useTranslation()
  return (
    <div className="lnd-app-preview fmv-fill">
      <div className="lnd-prev-header">
        <span className="lnd-prev-brand">{t('landing.v_safety')}</span>
        <span className="lnd-prev-badge" style={{ color: 'var(--ayura-sage)', background: 'color-mix(in srgb, var(--ayura-sage) 12%, transparent)', borderColor: 'color-mix(in srgb, var(--ayura-sage) 28%, transparent)' }}>{t('landing.v_all_clear')}</span>
      </div>
      <div className="fmv-check-list">
        {SAFETY_CHECKS.map((item, i) => (
          <m.div
            key={item.herb}
            className="fmv-check-row"
            initial={{ opacity: 0, x: -10 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.35, delay: 0.07 * i }}
          >
            <span className={`fmv-check-icon fmv-check-${item.result}`}>
              {item.result === 'pass' ? <Check size={13} strokeWidth={3} /> : <TriangleAlert size={13} strokeWidth={2.5} />}
            </span>
            <div className="fmv-check-info">
              <span className="fmv-check-name">{t(item.herb)}</span>
              <span className="fmv-check-note">{t(item.note)}</span>
            </div>
          </m.div>
        ))}
      </div>
      <div className="fmv-all-clear-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><ShieldCheck size={15} strokeWidth={2} /> {t('landing.v_zero_contra')}</div>
    </div>
  )
}

// ─── Hero Bento Grid ──────────────
function BentoHeroGrid() {
  const { t } = useTranslation()
  return (
    <div className="lnd-hero-visual">
      <m.div
        className="lnd-bento-grid"
        initial={{ opacity: 0, x: 60 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.9, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <m.div
          className="lnd-bento-tile lnd-bento-tile--tall"
          whileHover={{ scale: 1.02, y: -3 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        >
          <div className="lnd-bento-tile-kicker">{t('landing.b_dosha_kicker')}</div>
          <div className="lnd-bento-dosha-rings">
            {[['dosha_vata', DOSHA_COLOR.vata, 65], ['dosha_pitta', DOSHA_COLOR.pitta, 45], ['dosha_kapha', DOSHA_COLOR.kapha, 30]].map(([name, color, val]) => (
              <div key={name} className="lnd-bento-dosha-row">
                <span style={{ color, fontWeight: 700, fontSize: '0.78rem', width: 40 }}>{t(name)}</span>
                <div className="lnd-bento-dosha-track">
                  <m.div
                    className="lnd-bento-dosha-fill"
                    style={{ background: color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${val}%` }}
                    transition={{ duration: 1.3, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
                  />
                </div>
                <span style={{ color, fontSize: '0.72rem', fontWeight: 700, width: 22 }}>{val}</span>
              </div>
            ))}
          </div>
          <p className="lnd-bento-dosha-note">{t('landing.b_dosha_note')}</p>
          <div className="lnd-bento-badge">{t('landing.b_vata_dominant')}</div>
        </m.div>
        <m.div
          className="lnd-bento-tile lnd-bento-tile--accent"
          whileHover={{ scale: 1.03, y: -3 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        >
          <div className="lnd-bento-tile-icon" style={{ marginBottom: 8 }}><Leaf size={26} strokeWidth={1.6} /></div>
          <div className="lnd-bento-tile-label">{t('landing.b_yoga_plan')}</div>
          <div className="lnd-bento-tile-sub">{t('landing.b_yoga_sub')}</div>
          <div className="lnd-bento-status-dot" />
        </m.div>
        <m.div
          className="lnd-bento-tile lnd-bento-tile--chat"
          whileHover={{ scale: 1.02, y: -3 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        >
          <div className="lnd-bento-chat-bubble lnd-bento-chat-bubble--ai">
            {t('landing.b_chat_q')}
          </div>
          <div className="lnd-bento-chat-bubble lnd-bento-chat-bubble--user">
            {t('landing.b_chat_a')}
          </div>
          <div className="lnd-bento-tile-kicker" style={{ marginTop: 8 }}>{t('landing.b_advisor')}</div>
        </m.div>
        <m.div
          className="lnd-bento-tile lnd-bento-tile--stat"
          whileHover={{ scale: 1.03, y: -3 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        >
          <div className="lnd-bento-stat-num">360°</div>
          <div className="lnd-bento-stat-lbl">{t('landing.b_coverage')}</div>
        </m.div>
      </m.div>
    </div>
  )
}

// ─── FAQ ── visible content translates with t(); the FAQPage JSON-LD below is
// built from the English locale directly so structured data stays canonical.
const FAQS = [1, 2, 3, 4, 5, 6].map(n => ({ q: `landing.faq${n}_q`, a: `landing.faq${n}_a` }))
const FAQS_EN = [1, 2, 3, 4, 5, 6].map(n => ({ q: enLocale.landing[`faq${n}_q`], a: enLocale.landing[`faq${n}_a`] }))

// ─── Nav controls: theme + language switchers ─────────────────
function NavControls() {
  const { t, i18n } = useTranslation()
  const { theme, setThemeAnimated } = useTheme()
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDown = e => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false) }
    const onKey = e => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const current = (i18n.language || 'en').split('-')[0]
  const themeLabel = theme === 'dark' ? t('landing.nav_theme_light') : t('landing.nav_theme_dark')

  return (
    <>
      <button
        type="button"
        className="lnd-nav-icon-btn"
        onClick={e => setThemeAnimated(theme === 'dark' ? 'light' : 'dark', e)}
        aria-label={themeLabel}
        title={themeLabel}
      >
        {theme === 'dark' ? <Sun size={16} strokeWidth={2} /> : <Moon size={16} strokeWidth={2} />}
      </button>
      <div className="lnd-lang-wrap" ref={wrapRef}>
        <button
          type="button"
          className={`lnd-nav-icon-btn${open ? ' open' : ''}`}
          onClick={() => setOpen(o => !o)}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={t('landing.nav_language')}
          title={t('landing.nav_language')}
        >
          <Languages size={16} strokeWidth={2} />
        </button>
        {open && (
          <ul className="lnd-lang-menu" role="listbox" aria-label={t('landing.nav_language')}>
            {SUPPORTED_LANGUAGES.map(lang => (
              <li key={lang.code}>
                <button
                  type="button"
                  role="option"
                  aria-selected={lang.code === current}
                  className={`lnd-lang-item${lang.code === current ? ' active' : ''}`}
                  onClick={() => { setLanguage(lang.code); setOpen(false) }}
                >
                  <span>{lang.label}</span>
                  {lang.code === current && <Check size={14} strokeWidth={2.5} />}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}

// ─── Main Component ───────────────────────────────────────────
export default function Landing() {
  const { user, logout } = useAuth()
  const { t } = useTranslation()
  const [scrolled, setScrolled] = useState(false)
  // Reduced-motion users: disable transform animations entirely; content
  // simply appears.
  const lowPower = useLowPowerMode()
  const lenisRef = useRef(null)
  const rafRef   = useRef(null)

  // Hero parallax is a CSS scroll-driven animation (see .lnd-hero in
  // Landing.css) — the old framer useScroll/useTransform version wrote
  // transform+opacity to the 100vh hero on the MAIN THREAD every scroll frame,
  // which profiled at ~14fps scroll on a 4x-throttled mobile CPU. The CSS
  // timeline runs entirely on the compositor (measured 51+fps, zero long
  // tasks) with the identical y/opacity curve.

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    // Smooth-scroll only on fine-pointer desktops, and never under reduced-motion.
    // On touch (iOS/Android) Lenis fights native momentum + the URL-bar collapse
    // and is a known jank source, so we leave native scrolling alone there.
    if (typeof window === 'undefined' || !window.matchMedia) return
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)')
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (!fine.matches || reduce.matches) return

    const lenis = new Lenis({ duration: 1.2, easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)), smoothWheel: true })
    lenisRef.current = lenis
    function raf(time) { lenis.raf(time); rafRef.current = requestAnimationFrame(raf) }
    rafRef.current = requestAnimationFrame(raf)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); lenis.destroy() }
  }, [])

  useEffect(() => {
    const els = document.querySelectorAll('.reveal, .reveal-left, .reveal-right')
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target) } }),
      { threshold: 0.12, rootMargin: '0px 0px -60px 0px' }
    )
    els.forEach(el => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  // Site-wide structured data lives here (not in index.html) so it only renders
  // on the homepage and never leaks onto other prerendered routes like /dosha-test.
  // FAQPage is built from the FAQS array above → schema always matches visible content.
  const siteJsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebSite',
        '@id': 'https://ayuraai.in/#website',
        url: 'https://ayuraai.in',
        name: 'Ayura AI',
        alternateName: ['AyuraAI', 'Ayura', 'Ayura AI App', 'Ayur AI'],
        inLanguage: 'en-IN',
        description: 'AI-Powered Ayurvedic Wellness Platform',
        publisher: { '@id': 'https://ayuraai.in/#organization' },
        potentialAction: {
          '@type': 'SearchAction',
          target: 'https://ayuraai.in/?q={search_term_string}',
          'query-input': 'required name=search_term_string',
        },
      },
      {
        '@type': 'Organization',
        '@id': 'https://ayuraai.in/#organization',
        name: 'Ayura AI',
        alternateName: ['AyuraAI', 'Ayura', 'Ayur AI'],
        url: 'https://ayuraai.in',
        logo: { '@type': 'ImageObject', url: 'https://ayuraai.in/pwa-512x512.png', width: 512, height: 512 },
        image: 'https://ayuraai.in/og-image.png',
        slogan: 'Your wellness, finally in sync — AI + Ayurveda.',
        description: "India's AI-powered Ayurvedic wellness platform providing personalized dosha-based plans for diet, yoga, Panchakarma, and herbal medicine.",
        foundingLocation: { '@type': 'Place', name: 'India' },
        areaServed: { '@type': 'Country', name: 'India' },
        // Keep in sync with the twitter:site meta in index.html; append other
        // official profiles (Instagram, LinkedIn, YouTube…) as they launch.
        sameAs: ['https://x.com/ayuraai', 'https://twitter.com/ayuraai'],
      },
      {
        '@type': 'SoftwareApplication',
        '@id': 'https://ayuraai.in/#app',
        name: 'Ayura AI',
        url: 'https://ayuraai.in',
        applicationCategory: 'HealthApplication',
        operatingSystem: 'Web, iOS, Android',
        offers: { '@type': 'Offer', price: '0', priceCurrency: 'INR' },
        description: 'AI-powered Ayurvedic wellness platform for personalized health plans based on Prakriti analysis.',
        screenshot: 'https://ayuraai.in/og-image.png',
      },
      {
        '@type': 'FAQPage',
        '@id': 'https://ayuraai.in/#faq',
        mainEntity: FAQS_EN.map(f => ({
          '@type': 'Question',
          name: f.q,
          acceptedAnswer: { '@type': 'Answer', text: f.a },
        })),
      },
    ],
  }

  return (
    <MotionConfig reducedMotion={lowPower ? 'always' : 'user'}>
    <div className="landing-root">
      <Helmet>
        <title>Ayura AI — AI + Ayurveda Wellness Platform</title>
        <meta name="description" content="Ayura AI blends ancient Ayurvedic wisdom with modern AI to deliver adaptive, personalised wellness plans across fitness, nutrition, detox, and mindfulness." />
        <link rel="canonical" href="https://ayuraai.in" />
        <meta property="og:title" content="Ayura AI — AI-Powered Ayurvedic Wellness" />
        <meta property="og:description" content="India's AI wellness platform rooted in Ayurveda. Personalized plans for diet, yoga, Panchakarma, and herbal medicine based on your dosha." />
        <meta property="og:url" content="https://ayuraai.in" />
        <meta name="twitter:title" content="Ayura AI — AI-Powered Ayurvedic Wellness" />
        <meta name="twitter:description" content="Personalized Ayurvedic diet, yoga, and herbal plans powered by AI. Know your dosha. Live in balance." />
        <script type="application/ld+json">{JSON.stringify(siteJsonLd)}</script>
      </Helmet>

      <CursorGlow />

      {/* ── NAVBAR ──────────────────────────────────────────── */}
      <header className={`lnd-nav-wrap${scrolled ? ' scrolled' : ''}`}>
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
            <NavControls />
            {user ? (
              <>
                <Link to="/dashboard" className="lnd-nav-link">{t('landing.nav_dashboard')}</Link>
                <button className="lnd-cta-pill" onClick={logout}>{t('landing.nav_signout')}</button>
              </>
            ) : (
              <>
                <Link to="/login" className="lnd-nav-link">{t('landing.nav_signin')}</Link>
                <Link to="/register" className="lnd-cta-pill">{t('landing.nav_getstarted')}</Link>
              </>
            )}
          </div>
        </nav>
      </header>

      <main>
        {/* ── HERO ────────────────────────────────────────── */}
        <m.section className="lnd-hero">
          {/* Echo rings behind hero */}
          <div className="lnd-hero-echo" aria-hidden="true">
            <div className="lnd-hero-echo-ring" />
            <div className="lnd-hero-echo-ring" />
            <div className="lnd-hero-echo-ring" />
          </div>
          {/* Left copy */}
          <div className="lnd-hero-copy">
            {/* True page H1 for SEO — keyword/brand-rich, visually hidden so the
                animated tagline below remains the visual focus. */}
            <h1 className="sr-only">Ayura AI — AI-Powered Ayurvedic Wellness Platform</h1>

            <m.span
              className="lnd-hero-kicker"
              initial={PRERENDERED ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className="lnd-hero-kicker-dot" />
              {t('landing.hero_kicker')}
            </m.span>

            {/* Word-by-word stagger (visual tagline, demoted from H1 → H2) */}
            <m.h2
              className="lnd-hero-title"
              variants={stagger}
              initial={PRERENDERED ? false : 'hidden'}
              animate="visible"
            >
              {[...t('landing.hero_title').split(' '), ' accent'].map((word, i) => (
                <m.span
                  key={`${word}-${i}`}
                  variants={wordVariants}
                  transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                  style={{
                    display: 'inline-block',
                    marginRight: '0.25em',
                  }}
                >
                  {word === ' accent'
                    ? <em className="shimmer-text">{t('landing.hero_title_accent')}</em>
                    : word}
                </m.span>
              ))}
            </m.h2>

            {/* Transform-only entrance (opacity stays 1) so this prerendered LCP
                element counts as painted at first paint instead of waiting for a
                fade-in after hydration — big LCP win on slow devices. */}
            <m.p
              className="lnd-hero-subtitle"
              initial={PRERENDERED ? false : { y: 18 }}
              animate={{ y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              {t('landing.hero_subtitle')}
            </m.p>

            <m.div
              className="lnd-hero-cta-row"
              initial={PRERENDERED ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.28 }}
            >
              {user ? (
                <>
                  <MagneticButton as="a" href="/dashboard" className="lnd-cta-main">{t('landing.cta_dashboard')}</MagneticButton>
                  <MagneticButton className="lnd-cta-secondary" onClick={logout}>{t('landing.cta_switch_account')}</MagneticButton>
                </>
              ) : (
                <>
                  <MagneticButton as="a" href="/register" className="lnd-cta-main">{t('landing.cta_create_profile')}</MagneticButton>
                  <MagneticButton as="a" href="#features" className="lnd-cta-secondary">{t('landing.cta_explore')}</MagneticButton>
                </>
              )}
            </m.div>

            {/* Trust bar */}
            <m.div
              className="lnd-trust-bar"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              {TRUST_ITEMS.map(item => (
                <div key={item.label} className="lnd-trust-item">
                  <span className="lnd-trust-icon"><item.Icon size={13} strokeWidth={2.25} /></span>
                  {t(item.label)}
                </div>
              ))}
            </m.div>
          </div>

          {/* Right visual — Bento grid */}
          <BentoHeroGrid />
        </m.section>

        {/* ── HOW IT WORKS ──────────────────────────────── */}
        <div className="lnd-section">
          <div className="lnd-how-header reveal">
            <span className="lnd-section-kicker">{t('landing.how_kicker')}</span>
            <h2 className="lnd-section-title">{t('landing.how_title')}</h2>
            <p className="lnd-section-desc">
              {t('landing.how_desc')}
            </p>
          </div>

          <div className="lnd-cards-row reveal">
            {HOW_CARDS.map(card => (
              <div key={card.id} className="lnd-how-card">
                <span className="lnd-how-card-step">{t(card.step)}</span>
                <div className="lnd-how-card-icon-badge"><card.Icon size={26} strokeWidth={1.6} /></div>
                <div className="lnd-how-card-body">
                  <div className="lnd-how-card-title">{t(card.title)}</div>
                  <p className="lnd-how-card-desc">{t(card.desc)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── STATS STRIP ───────────────────────────── */}
        <div className="lnd-stats-section reveal">
          <div className="lnd-stats-bar">
            {STATS.map(stat => (
              <div key={stat.id} className="lnd-stat">
                <span className="lnd-stat-value">
                  {stat.countTo !== undefined ? (
                    <CountUp
                      to={stat.countTo}
                      suffix={stat.suffix || ''}
                      duration={stat.id === 'pillars' ? 900 : 1800}
                    />
                  ) : stat.static}
                </span>
                <span className="lnd-stat-label">{t(stat.label)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── FEATURE SECTIONS ────────────────────────── */}
        <div id="features" className="lnd-section" style={{ paddingTop: 0 }}>
          {FEATURES.map((f) => (
            <div key={f.tag} className={`lnd-feature${f.reversed ? ' reverse' : ''}`}>
              <m.div
                className="lnd-feature-copy"
                variants={f.reversed ? fadeRight : fadeLeft}
                initial="hidden"
                whileInView="visible"
                viewport={VP}
                transition={{ duration: 0.7, ease: 'easeOut' }}
              >
                <div className="lnd-feature-icon-wrap"><f.Icon size={26} strokeWidth={1.6} /></div>
                <span className="lnd-section-kicker">{t(f.tag)}</span>
                <h2 className="lnd-feature-title">{t(f.title)}</h2>
                <p className="lnd-feature-desc">{t(f.desc)}</p>
                <ul className="lnd-feature-list">
                  {f.list.map(item => <li key={item}>{t(item)}</li>)}
                </ul>
              </m.div>

              <m.div
                className="lnd-feature-visual"
                variants={f.reversed ? fadeLeft : fadeRight}
                initial="hidden"
                whileInView="visible"
                viewport={VP}
                transition={{ duration: 0.7, ease: 'easeOut', delay: 0.15 }}
              >
                <div className="lnd-feature-img-frame">
                  <f.Visual />
                </div>
              </m.div>
            </div>
          ))}
        </div>

        {/* ── PLAN SHOWCASE ──────────────────────────── */}
        <div className="lnd-section" style={{ paddingTop: 0 }}>
          <div className="reveal" style={{ textAlign: 'center', marginBottom: 0 }}>
            <span className="lnd-section-kicker">{t('landing.plans_kicker')}</span>
            <h2 className="lnd-section-title">{t('landing.plans_title')}</h2>
            <p className="lnd-section-desc" style={{ margin: '0 auto' }}>
              {t('landing.plans_desc')}
            </p>
          </div>

          <div className="lnd-plans-grid reveal">
            {PLAN_SHOWCASE.map((plan) => (
              <m.div
                key={plan.id}
                className="lnd-plan-card"
                style={{ '--plan-clr': plan.clr, '--plan-tint': plan.tint }}
                whileHover={{ y: -4 }}
                transition={{ duration: 0.2 }}
              >
                <span className="lnd-plan-emoji" style={{ color: plan.tint }}>
                  <plan.Icon size={24} strokeWidth={1.7} />
                </span>
                <h3 className="lnd-plan-title">{t(plan.title)}</h3>
                <p className="lnd-plan-desc">{t(plan.desc)}</p>
              </m.div>
            ))}
          </div>
        </div>

        {/* ── TESTIMONIALS ───────────────────────────── */}
        <div className="lnd-section" style={{ paddingTop: 0 }}>
          <div className="reveal" style={{ textAlign: 'center', marginBottom: 48 }}>
            <span className="lnd-section-kicker">{t('landing.testi_kicker')}</span>
            <h2 className="lnd-section-title">{t('landing.testi_title')}</h2>
          </div>
          <div className="lnd-testimonials-grid reveal">
            {TESTIMONIALS.map(item => (
              <m.div
                key={item.id}
                className="lnd-testimonial-card"
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
              >
                <div className="lnd-testimonial-stars">{'★'.repeat(item.stars)}</div>
                <p className="lnd-testimonial-quote">"{t(item.quote)}"</p>
                <div className="lnd-testimonial-author">
                  <div
                    className="lnd-testimonial-avatar"
                    style={{ background: `${item.doshaColor}22`, border: `1px solid ${item.doshaColor}44`, color: item.doshaColor }}
                  >
                    {item.initials}
                  </div>
                  <div>
                    <div className="lnd-testimonial-name">{t(item.name)}</div>
                    <div className="lnd-testimonial-meta">
                      <span className="lnd-testimonial-dosha" style={{ color: item.doshaColor }}>{t(item.dosha)}</span>
                      <span className="lnd-testimonial-sep">·</span>
                      <span className="lnd-testimonial-loc">{t(item.location)}</span>
                    </div>
                  </div>
                </div>
              </m.div>
            ))}
          </div>
        </div>

        {/* ── FAQ ──────────────────────────────────────── */}
        <div id="faq" className="lnd-section" style={{ paddingTop: 0 }}>
          <div className="reveal" style={{ textAlign: 'center', marginBottom: 40 }}>
            <span className="lnd-section-kicker">{t('landing.faq_kicker')}</span>
            <h2 className="lnd-section-title">{t('landing.faq_title')}</h2>
          </div>
          <div className="lnd-faq-list reveal">
            {FAQS.map((item, i) => (
              <details key={i} className="lnd-faq-item">
                <summary className="lnd-faq-q">
                  <span>{t(item.q)}</span>
                  <span className="lnd-faq-icon" aria-hidden="true">+</span>
                </summary>
                <p className="lnd-faq-a">{t(item.a)}</p>
              </details>
            ))}
          </div>
        </div>

        {/* ── CTA BLOCK ──────────────────────────────── */}
        <div className="lnd-cta-section">
          <m.div
            className="lnd-cta-box"
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={VP}
            transition={{ duration: 0.7 }}
          >
            <h2 className="lnd-cta-box-title">{t('landing.ctabox_title')}</h2>
            <p className="lnd-cta-box-desc">
              {t('landing.ctabox_desc')}
            </p>
            <div className="lnd-cta-box-actions">
              {user ? (
                <Link to="/dashboard" className="lnd-cta-main">{t('landing.ctabox_dashboard')}</Link>
              ) : (
                <>
                  <MagneticButton as="a" href="/register" className="lnd-cta-main">{t('landing.ctabox_start')}</MagneticButton>
                  <Link to="/login" className="lnd-cta-secondary">{t('landing.ctabox_signin')}</Link>
                </>
              )}
            </div>
          </m.div>
        </div>
      </main>

      {/* ── FOOTER ──────────────────────────────────── */}
      <footer className="lnd-footer">
        <div className="lnd-footer-inner">
          <div className="lnd-footer-top">
            <div>
              <Link to="/" className="lnd-footer-brand">
                <img src="/favicon.svg" alt="Ayura AI Logo" className="lnd-footer-brand-mark" />
                <span className="lnd-footer-brand-text">Ayura AI</span>
              </Link>
              <p className="lnd-footer-tagline">
                {t('landing.footer_tagline')}
              </p>
            </div>
            <div>
              <p className="lnd-footer-links-title">{t('landing.footer_platform')}</p>
              <ul className="lnd-footer-links">
                <li><Link to="/register">{t('landing.footer_getstarted')}</Link></li>
                <li><Link to="/login">{t('landing.footer_signin')}</Link></li>
                <li><Link to="/dosha-test">{t('landing.footer_dosha_free')}</Link></li>
                <li><a href="#features">{t('landing.footer_features')}</a></li>
              </ul>
            </div>
            <div>
              <p className="lnd-footer-links-title">{t('landing.footer_legal')}</p>
              <ul className="lnd-footer-links">
                <li><Link to="/terms">{t('landing.footer_terms')}</Link></li>
                <li><Link to="/privacy">{t('landing.footer_privacy')}</Link></li>
              </ul>
            </div>
            <div>
              <p className="lnd-footer-links-title">{t('landing.footer_wellness')}</p>
              <ul className="lnd-footer-links">
                <li><Link to="/dosha-test">{t('landing.footer_dosha_test')}</Link></li>
                <li><a href="#features">{t('landing.footer_yoga')}</a></li>
                <li><a href="#features">{t('landing.footer_nutrition')}</a></li>
                <li><a href="#features">{t('landing.footer_detox')}</a></li>
              </ul>
            </div>
          </div>
          <div className="lnd-footer-bottom">
            <p className="lnd-footer-copy">© {new Date().getFullYear()} Ayura AI — {t('landing.footer_copy')}</p>
            <p className="lnd-footer-disclaimer">
              {t('landing.footer_disclaimer')}
            </p>
          </div>
        </div>
      </footer>
    </div>
    </MotionConfig>
  )
}
