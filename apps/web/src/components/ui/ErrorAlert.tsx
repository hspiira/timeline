import { Alert, AlertDescription } from './alert'
import { ErrorIcon } from './icons'

export interface ErrorAlertProps {
  message: string
  className?: string
}

/** Inline error message. Prefer Alert variant="destructive" for new code; this is the unified form/alert error. */
export function ErrorAlert({ message, className = '' }: ErrorAlertProps) {
  return (
    <Alert variant="destructive" className={className}>
      <ErrorIcon size="md" className="shrink-0" />
      <AlertDescription>
        <p className="text-sm">{message}</p>
      </AlertDescription>
    </Alert>
  )
}
