/**
 * Inline error display with optional retry. Use for API/form errors.
 * Composes Alert (shadcn-style) + getApiErrorDisplay + optional retry action.
 */

import { AlertCircle, RefreshCw } from 'lucide-react'
import { getApiErrorDisplay } from '@/lib/api-utils'
import type { ApiErrorDisplay } from '@/lib/api-utils'
import { Alert, AlertDescription } from './alert'
import { Button } from './button'

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
    <Alert variant="destructive" className={className}>
      <AlertCircle size={20} className="shrink-0" aria-hidden />
      <div className="flex-1 min-w-0">
        <AlertDescription>
          <p className="font-medium text-foreground">{display.message}</p>
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
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={onRetry}
              className="mt-3"
            >
              <RefreshCw size={16} className="mr-2" aria-hidden />
              Retry
            </Button>
          )}
        </AlertDescription>
      </div>
    </Alert>
  )
}
