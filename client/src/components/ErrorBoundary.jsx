import React from 'react';
import { motion } from 'framer-motion';
import { useLocation } from 'react-router-dom';

class ErrorBoundaryInner extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidUpdate(prevProps) {
    if (this.state.hasError && this.props.location.pathname !== prevProps.location.pathname) {
      this.setState({ hasError: false, error: null });
    }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          textAlign: 'center',
          background: 'var(--bg-color)'
        }}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              maxWidth: '400px',
              padding: '2rem',
              background: 'var(--card-bg)',
              borderRadius: '16px',
              border: '1px solid var(--dash-edge)'
            }}
          >
            <h1 style={{ marginBottom: '1rem', color: 'var(--text-color)' }}>Something went wrong.</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
              We've encountered an unexpected error. You can try navigating away or refreshing the page.
            </p>
            <button
              className="btn btn-primary"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Try Again
            </button>
          </motion.div>
        </div>
      );
    }

    return this.props.children; 
  }
}

export default function ErrorBoundary(props) {
  const location = useLocation();
  return <ErrorBoundaryInner location={location} {...props} />;
}
