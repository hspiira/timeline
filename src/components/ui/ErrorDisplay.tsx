/**
 * Inline error display with optional retry. Use for API/form errors.
 */

import { AlertCircle, RefreshCw } from 'lucide-react'
import { getApiErrorDisplay } from '@/lib/api-utils'
import type { ApiErrorDisplay } from '@/lib/api-utils'

export interface ErrorDisplayProps {
  error: unknown
  defaultMessage?: string
  status?: number
  onRetry?: () => void
  className?: string
}

function isRetryable(status?: number): boolean {
  if (status == null) return false
  return status >= 500 || status === 0
}

export function ErrorDisplay({
  error,
  defaultMessage = 'An unexpected error occurred',
  status,
  onRetry,
  className = '',
}: ErrorDisplayProps) {
  const display: ApiErrorDisplay = getApiErrorDisplay({ error, status }, defaultMessage)
  const retryable = isRetryable(status) && !!onRetry

  return (
    <div
      className={`flex items-start gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-[var(--radius)] text-destructive ${className}`}
      role="alert"
    >
      <AlertCircle size={20} className="shrink-0 mt-0.5" aria-hidden />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground">{display.message}</p>
        {display.fieldErrors && display.fieldErrors.length > 0 && (
          <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
            {display.fieldErrors.map((fe) => (
              <li key={fe.field}>
                <span className="font-medium">{fe.field}:</span> {fe.message}
              </li>
            ))}
          </ul>
        )}
        {retryable && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground hover:opacity-90 text-sm font-medium rounded-[var(--radius)] transition-opacity"
          >
            <RefreshCw size={16} aria-hidden />
            Retry
          </button>
        )}
      </div>
    </div>
  )
}
