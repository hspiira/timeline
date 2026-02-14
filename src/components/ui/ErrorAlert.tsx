import { ErrorIcon } from './icons'

export interface ErrorAlertProps {
  message: string
  className?: string
}

export function ErrorAlert({ message, className = '' }: ErrorAlertProps) {
  return (
    <div
      className={`flex items-start gap-2 p-3 rounded-xs bg-destructive/10 border border-destructive/20 text-destructive ${className}`}
      role="alert"
    >
      <ErrorIcon size="md" className="shrink-0 mt-0.5" />
      <p className="text-sm">{message}</p>
    </div>
  )
}
