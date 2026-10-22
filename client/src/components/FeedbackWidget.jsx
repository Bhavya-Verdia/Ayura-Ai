import { useState, useEffect } from 'react'
import { m, AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import { toast } from 'sonner'
import { feedbackAPI } from '../api/client'
import { X } from 'lucide-react'
import { tr } from '../lib/tr'
import { Trans } from 'react-i18next'
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

  // This component renders NO trigger of its own — it is opened by an event.
  // It used to own a floating FAB, which was `position: fixed` over scrollable
  // content and won the hit-test against whatever scrolled under it: Chat's
  // send button, Community's "Share", Herb Safety's "Check safety", a
  // dosha-quiz answer card, and on desktop the "Report a reaction" button on
  // the dashboard plan cards. Hiding it per page was whack-a-mole because the
  // collisions are content-dependent. Triggers now live in fixed chrome that
  // never overlays content: the sidebar (MainLayout) and Settings.
  useEffect(() => {
    const open = () => setIsOpen(true)
    window.addEventListener('ayura:open-feedback', open)
    return () => window.removeEventListener('ayura:open-feedback', open)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (description.trim().length < 5) {
      toast.warning(tr('ui.feedbackWidget.pleaseProvideABitMore', 'Please provide a bit more detail (min 5 characters).'))
      return
    }

    setIsSubmitting(true)
    try {
      await feedbackAPI.submit({
        type,
        description,
        url: location.pathname + location.search
      })
      toast.success(tr('ui.feedbackWidget.feedbackSubmittedThankYou', 'Feedback submitted! Thank you.'))
      setIsOpen(false)
      setDescription('')
      setType('General')
    } catch {
      toast.error(tr('ui.feedbackWidget.failedToSubmitFeedbackPlease', 'Failed to submit feedback. Please try again later.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
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
                <h3>{tr('ui.feedbackWidget.shareFeedback', 'Share Feedback')}</h3>
                <button className="feedback-close" onClick={() => setIsOpen(false)} aria-label={tr('ui.feedbackWidget.close', 'Close')}><X size={16} strokeWidth={2} /></button>
              </div>
              
              <form onSubmit={handleSubmit} className="feedback-form">
                <div className="feedback-field">
                  <label>{tr('ui.feedbackWidget.typeOfFeedback', 'Type of Feedback')}</label>
                  <select value={type} onChange={e => setType(e.target.value)}>
                    <option value="Bug">{tr('ui.feedbackWidget.reportABug', 'Report a Bug')}</option>
                    <option value="Content Error">{tr('ui.feedbackWidget.medicalContentError', 'Medical/Content Error')}</option>
                    <option value="Feature Request">{tr('ui.feedbackWidget.featureRequest', 'Feature Request')}</option>
                    <option value="General">{tr('ui.feedbackWidget.generalFeedback', 'General Feedback')}</option>
                  </select>
                </div>

                <div className="feedback-field">
                  <label>{tr('ui.feedbackWidget.description', 'Description')}</label>
                  <textarea 
                    placeholder={tr('ui.feedbackWidget.whatDidYouNoticeHow', 'What did you notice? How can we improve?')}
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    rows={4}
                    autoFocus
                  />
                </div>

                <div className="feedback-context">
                  <small><Trans i18nKey="ui.feedbackWidget.context" defaults={"Context: {{pathname}}"} values={{ pathname: location.pathname }} /></small>
                </div>

                <button 
                  type="submit" 
                  className="btn btn-primary feedback-submit"
                  disabled={isSubmitting || description.trim().length < 5}
                >
                  {isSubmitting ? tr('ui.feedbackWidget.sending', 'Sending...') : tr('ui.feedbackWidget.sendToTeam', 'Send to Team')}
                </button>
              </form>
            </m.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
