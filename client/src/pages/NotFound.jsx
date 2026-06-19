import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Compass, LayoutDashboard, Home } from 'lucide-react'
import './NotFound.css'

export default function NotFound() {
  return (
    <>
      <Helmet><title>Page Not Found | Ayura AI</title></Helmet>
      <div className="notfound-page">
        <div className="notfound-orb notfound-orb-a" />
        <div className="notfound-orb notfound-orb-b" />

        <motion.div
          className="notfound-content"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <motion.div
            className="notfound-icon-wrap"
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 3.2, ease: 'easeInOut', repeat: Infinity }}
          >
            <Compass size={52} strokeWidth={1.5} />
          </motion.div>

          <h1 className="notfound-heading">404</h1>

          <p className="notfound-subtext">
            This page has wandered off the path.<br />Let's guide you back to balance.
          </p>

          <div className="notfound-actions">
            <Link to="/" className="btn btn-primary notfound-btn">
              <Home size={16} strokeWidth={2} />
              Return Home
            </Link>
            <Link to="/dashboard" className="btn btn-glass notfound-btn">
              <LayoutDashboard size={16} strokeWidth={2} />
              Dashboard
            </Link>
          </div>
        </motion.div>
      </div>
    </>
  )
}
