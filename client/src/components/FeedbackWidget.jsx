import { useState, useEffect } from 'react'
import { m, AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import { toast } from 'sonner'
import { feedbackAPI } from '../api/client'
import { X } from 'lucide-react'
import './FeedbackWidget.css'

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [type, setType] = useState('General')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const location = useLocation()

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) setIsOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (description.trim().length < 5) {
      toast.warning('Please provide a bit more detail (min 5 characters).')
      return
    }

    setIsSubmitting(true)
    try {
      await feedbackAPI.submit({
        type,
        description,
        url: location.pathname + location.search
      })
      toast.success('Feedback submitted! Thank you.')
      setIsOpen(false)
      setDescription('')
      setType('General')
    } catch {
      toast.error('Failed to submit feedback. Please try again later.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <m.button
        className="feedback-fab"
        onClick={() => setIsOpen(true)}
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Give Feedback"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </m.button>

      <AnimatePresence>
        {isOpen && (
          <div className="feedback-overlay" onClick={() => setIsOpen(false)}>
            <m.div 
              className="feedback-modal"
              onClick={e => e.stopPropagation()}
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.9 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            >
              <div className="feedback-header">
                <h3>Share Feedback</h3>
                <button className="feedback-close" onClick={() => setIsOpen(false)} aria-label="Close"><X size={16} strokeWidth={2} /></button>
              </div>
              
              <form onSubmit={handleSubmit} className="feedback-form">
                <div className="feedback-field">
                  <label>Type of Feedback</label>
                  <select value={type} onChange={e => setType(e.target.value)}>
                    <option value="Bug">Report a Bug</option>
                    <option value="Content Error">Medical/Content Error</option>
                    <option value="Feature Request">Feature Request</option>
                    <option value="General">General Feedback</option>
                  </select>
                </div>

                <div className="feedback-field">
                  <label>Description</label>
                  <textarea 
                    placeholder="What did you notice? How can we improve?"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    rows={4}
                    autoFocus
                  />
                </div>

                <div className="feedback-context">
                  <small>Context: {location.pathname}</small>
                </div>

                <button 
                  type="submit" 
                  className="btn btn-primary feedback-submit"
                  disabled={isSubmitting || description.trim().length < 5}
                >
                  {isSubmitting ? 'Sending...' : 'Send to Team'}
                </button>
              </form>
            </m.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
