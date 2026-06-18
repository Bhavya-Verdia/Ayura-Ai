import React from 'react'
import { AlertTriangle } from 'lucide-react'
import './SectionBoundary.css'

class SectionBoundaryInner extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('[SectionBoundary]', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="section-boundary-fallback">
          <AlertTriangle size={20} strokeWidth={2} className="section-boundary-icon" />
          <p className="section-boundary-msg">
            {this.props.fallbackMessage || 'This section couldn\'t load.'}
          </p>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => this.setState({ hasError: false })}
          >
            Retry
          </button>
          {this.props.onBack && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={this.props.onBack}
            >
              ← Go Back
            </button>
          )}
        </div>
      )
    }

    return this.props.children
  }
}

export default function SectionBoundary({ children, fallbackMessage, onBack }) {
  return (
    <SectionBoundaryInner fallbackMessage={fallbackMessage} onBack={onBack}>
      {children}
    </SectionBoundaryInner>
  )
}
