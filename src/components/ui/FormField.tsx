import { AlertCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { Alert, AlertDescription } from './alert'
import { Input } from './input'

export interface FormFieldProps {
  label: string
  error?: string | null
  required?: boolean
  hint?: string
  children: ReactNode
}

export function FormField({ label, error, required = false, hint, children }: FormFieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-foreground/90">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {error && (
        <div className="flex items-center gap-1.5 text-red-600 dark:text-red-300">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <p className="text-xs font-medium">{error}</p>
        </div>
      )}
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

export interface FormInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  error?: string | null
  size?: 'sm' | 'md' | 'lg'
}

/** Thin wrapper around Input for use inside FormField; error styling only (FormField shows message). */
export function FormInput({ error, className = '', size, ...props }: FormInputProps) {
  return (
    <Input
      {...props}
      className={className}
      error={error ?? undefined}
      hideErrorMessage
      size={size}
    />
  )
}

export interface FormTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string | null
}

export function FormTextarea({ error, className = '', ...props }: FormTextareaProps) {
  return (
    <textarea
      className={`w-full px-3 py-2 bg-background border rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 transition-colors resize-none ${
        error
          ? 'border-red-500 dark:border-red-600 focus:ring-red-500/20 dark:focus:ring-red-600/20'
          : 'border-input focus:ring-ring/20'
      } ${className}`}
      {...props}
    />
  )
}

export interface FormErrorProps {
  message: string | null
}

export function FormError({ message }: FormErrorProps) {
  if (!message) return null

  return (
    <Alert variant="destructive" className="p-3">
      <AlertCircle className="w-4 h-4 flex-shrink-0" />
      <AlertDescription>
        <p className="text-sm">{message}</p>
      </AlertDescription>
    </Alert>
  )
}

export interface FormSuccessProps {
  message: string | null
}

export function FormSuccess({ message }: FormSuccessProps) {
  if (!message) return null

  return (
    <div className="p-3 bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-700 rounded-none flex items-center gap-2">
      <div className="w-4 h-4 rounded-none bg-green-600 dark:bg-green-300 flex-shrink-0" />
      <p className="text-sm text-green-700 dark:text-green-200">{message}</p>
    </div>
  )
}
