import { Loader2, AlertCircle, type LucideIcon } from 'lucide-react'
import type { LucideProps } from 'lucide-react'

export type IconSize = 'sm' | 'md' | 'lg'

interface IconComponentProps extends Omit<LucideProps, 'size'> {
  size?: IconSize
}

const sizeClasses: Record<IconSize, string> = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
}

/**
 * Centrally managed loading spinner icon
 * Usage: <LoadingIcon size="sm" /> or <LoadingIcon size="md" /> or <LoadingIcon size="lg" />
 */
export function LoadingIcon({ size = 'md', className = '', ...props }: IconComponentProps) {
  return (
    <Loader2
      className={`animate-spin ${sizeClasses[size]} ${className}`}
      {...props}
    />
  )
}

/**
 * Centrally managed error/alert icon
 * Usage: <ErrorIcon size="sm" /> or <ErrorIcon size="md" /> or <ErrorIcon size="lg" />
 */
export function ErrorIcon({ size = 'lg', className = '', ...props }: IconComponentProps) {
  return (
    <AlertCircle
      className={`shrink-0 ${sizeClasses[size]} ${className}`}
      {...props}
    />
  )
}

/**
 * Generic icon wrapper with size management
 */
export function Icon({
  icon: IconComponent,
  size = 'md',
  className = '',
  ...props
}: IconComponentProps & { icon: LucideIcon }) {
  return (
    <IconComponent
      className={`${sizeClasses[size]} ${className}`}
      {...props}
    />
  )
}
