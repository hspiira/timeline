/**
 * 404 page. Use fullPage for the router notFoundComponent (full-screen card layout).
 */

import { Link } from '@tanstack/react-router'
import { Home, ArrowLeft, FileQuestion } from 'lucide-react'

export interface NotFoundProps {
  title?: string
  message?: string
  showBackButton?: boolean
  backUrl?: string
  backLabel?: string
  /** When true, renders full-screen card layout (e.g. for router notFoundComponent). */
  fullPage?: boolean
  className?: string
}

export function NotFound({
  title = 'Page not found',
  message = "The page you're looking for doesn't exist or has been moved.",
  showBackButton = true,
  backUrl = '/',
  backLabel = 'Go to dashboard',
  fullPage = false,
  className = '',
}: NotFoundProps) {
  const actions = showBackButton && (
    <div className={fullPage ? 'flex flex-col gap-3' : 'flex flex-wrap gap-4 justify-center'}>
      <Link
        to={backUrl}
        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-primary text-primary-foreground hover:opacity-90 font-semibold rounded-[var(--radius)] transition-opacity"
      >
        <Home size={18} aria-hidden />
        <span>{backLabel}</span>
      </Link>
      <button
        type="button"
        onClick={() => window.history.back()}
        className={`inline-flex items-center justify-center gap-2 px-6 py-3 font-semibold rounded-[var(--radius)] transition-colors ${
          fullPage
            ? 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            : 'bg-muted text-muted-foreground hover:bg-muted/80'
        }`}
      >
        <ArrowLeft size={18} aria-hidden />
        <span>Go back</span>
      </button>
    </div>
  )

  if (fullPage) {
    return (
      <div className={`min-h-screen bg-background flex items-center justify-center px-4 ${className}`}>
        <div className="max-w-md w-full bg-card text-card-foreground p-8 rounded-[var(--radius)] border border-border shadow-sm">
          <div className="text-center">
            <FileQuestion
              size={48}
              className="text-muted-foreground mx-auto mb-4"
              aria-hidden
            />
            <h1 className="text-2xl font-bold text-foreground mb-2">{title}</h1>
            <p className="text-muted-foreground mb-6">{message}</p>
            {actions}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`flex flex-col items-center justify-center min-h-[60vh] p-8 text-center ${className}`}
    >
      <div className="mb-8">
        <p className="text-6xl font-bold text-foreground mb-4">404</p>
        <h1 className="text-2xl font-semibold text-foreground mb-4">{title}</h1>
        <p className="text-muted-foreground max-w-md mx-auto">{message}</p>
      </div>
      {actions}
    </div>
  )
}
