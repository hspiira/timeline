import { forwardRef, type InputHTMLAttributes } from 'react'

export type InputVariant = 'default' | 'error' | 'success'
export type InputSize = 'sm' | 'md' | 'lg'

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  variant?: InputVariant
  size?: InputSize
  error?: string
  helperText?: string
  /** When true, only apply error styling; do not render error message (e.g. when FormField shows it) */
  hideErrorMessage?: boolean
}

const variantStyles: Record<InputVariant, string> = {
  default: 'border-border/50 focus:border-blue-500 focus:ring-blue-500',
  error: 'border-red-500 focus:border-red-500 focus:ring-red-500',
  success: 'border-green-500 focus:border-green-500 focus:ring-green-500',
}

const sizeStyles: Record<InputSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-3 py-2 text-sm',
  lg: 'px-4 py-2.5 text-base',
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      variant = 'default',
      size = 'md',
      error,
      helperText,
      hideErrorMessage = false,
      className = '',
      disabled = false,
      ...props
    },
    ref,
  ) => {
    const baseStyles =
      'w-full rounded-none bg-background border border-input text-foreground transition-colors placeholder:text-muted-foreground disabled:opacity-50 disabled:cursor-not-allowed'
    const focusStyles = 'focus:outline-none focus:ring-1'

    const activeVariant = error ? 'error' : variant

    return (
      <div className="w-full">
        <input
          ref={ref}
          disabled={disabled}
          className={`${baseStyles} ${variantStyles[activeVariant]} ${sizeStyles[size]} ${focusStyles} ${className}`}
          {...props}
        />
        {error && !hideErrorMessage && (
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>
        )}
        {helperText && !error && <p className="mt-1 text-xs text-muted-foreground">{helperText}</p>}
      </div>
    )
  },
)

Input.displayName = 'Input'
