import { forwardRef, type ReactNode, type SelectHTMLAttributes } from 'react'

export type SelectVariant = 'default' | 'error' | 'success'
export type SelectSize = 'sm' | 'md' | 'lg'

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  variant?: SelectVariant
  size?: SelectSize
  error?: string
  helperText?: string
  children: ReactNode
}

const variantStyles: Record<SelectVariant, string> = {
  default: 'border-border/50 focus:border-blue-500 focus:ring-blue-500',
  error: 'border-red-500 focus:border-red-500 focus:ring-red-500',
  success: 'border-green-500 focus:border-green-500 focus:ring-green-500',
}

const sizeStyles: Record<SelectSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-3 py-2 text-sm',
  lg: 'px-4 py-2.5 text-base',
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      variant = 'default',
      size = 'md',
      error,
      helperText,
      className = '',
      disabled = false,
      children,
      ...props
    },
    ref,
  ) => {
    const baseStyles =
      'w-full rounded-none bg-background border transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
    const focusStyles = 'focus:outline-none focus:ring-1'

    const activeVariant = error ? 'error' : variant

    return (
      <div className="w-full">
        <select
          ref={ref}
          disabled={disabled}
          className={`${baseStyles} ${variantStyles[activeVariant]} ${sizeStyles[size]} ${focusStyles} ${className}`}
          {...props}
        >
          {children}
        </select>
        {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
        {helperText && !error && <p className="mt-1 text-xs text-muted-foreground">{helperText}</p>}
      </div>
    )
  },
)

Select.displayName = 'Select'
