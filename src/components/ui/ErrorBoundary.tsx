/**
 * Error Boundary – catches React errors and shows a full-page fallback.
 * Used as the top-level shell so runtime errors don’t white-screen the app.
 */

import { Component, type ReactNode } from 'react'
import { AlertCircle, Home } from 'lucide-react'
import { Link } from '@tanstack/react-router'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error('ErrorBoundary caught:', error, errorInfo)
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-background flex items-center justify-center px-4">
          <div className="max-w-md w-full bg-card text-card-foreground p-8 rounded-[var(--radius)] border border-border shadow-sm">
            <div className="text-center">
              <AlertCircle
                size={48}
                className="text-destructive mx-auto mb-4"
                aria-hidden
              />
              <h1 className="text-2xl font-bold text-foreground mb-2">
                Something went wrong
              </h1>
              <p className="text-muted-foreground mb-6">
                An unexpected error occurred. Try refreshing the page or return to the dashboard.
              </p>

              {this.state.error && import.meta.env.DEV && (
                <div className="mb-6 p-3 bg-muted/50 border border-border rounded-[var(--radius-xs)] text-left">
                  <p className="text-foreground text-xs font-mono break-all">
                    {this.state.error.message}
                  </p>
                </div>
              )}

              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={this.handleReset}
                  className="px-6 py-3 bg-primary text-primary-foreground hover:opacity-90 font-semibold rounded-[var(--radius)] transition-opacity"
                >
                  Try again
                </button>
                <Link
                  to="/"
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-secondary text-secondary-foreground hover:bg-secondary/80 font-semibold rounded-[var(--radius)] transition-colors"
                >
                  <Home size={18} aria-hidden />
                  Go to dashboard
                </Link>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
