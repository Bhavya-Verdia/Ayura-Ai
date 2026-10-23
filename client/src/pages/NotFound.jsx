import { m } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Compass, LayoutDashboard, Home } from 'lucide-react'
import { tr } from '../lib/tr'
import { Trans } from 'react-i18next'
import './NotFound.css'

export default function NotFound() {
  return (
    <>
      <Helmet><title>{tr('ui.notFound.pageNotFoundAyuraAi', 'Page Not Found | Ayura AI')}</title></Helmet>
      <div className="notfound-page">
        <div className="notfound-orb notfound-orb-a" />
        <div className="notfound-orb notfound-orb-b" />

        <m.div
          className="notfound-content"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <m.div
            className="notfound-icon-wrap"
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 3.2, ease: 'easeInOut', repeat: Infinity }}
          >
            <Compass size={52} strokeWidth={1.5} />
          </m.div>

          <h1 className="notfound-heading">404</h1>

          <p className="notfound-subtext"><Trans i18nKey="ui.notFound.thisPageHasWanderedOff" defaults={"This page has wandered off the path.<0/>Let's guide you back to balance."} components={[<br />]} /></p>

          <div className="notfound-actions">
            <Link to="/" className="btn btn-primary notfound-btn">
              <Home size={16} strokeWidth={2} />
              {tr('ui.notFound.returnHome', 'Return Home')}
            </Link>
            <Link to="/dashboard" className="btn btn-glass notfound-btn">
              <LayoutDashboard size={16} strokeWidth={2} />
              {tr('ui.notFound.dashboard', 'Dashboard')}
            </Link>
          </div>
        </m.div>
      </div>
    </>
  )
}
