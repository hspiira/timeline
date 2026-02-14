import { ButtonHTMLAttributes, ReactNode, forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

export type ButtonVariant = 'primary' | 'secondary' | 'destructive' | 'ghost' | 'outline'
export type ButtonSize = 'sm' | 'md' | 'lg' | 'icon'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 font-medium rounded-none transition-colors focus:outline-none focus:ring-2 focus:ring-offset-0 disabled:opacity-50 disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        primary:
          'bg-primary text-primary-foreground hover:bg-primary/90 focus:ring-primary/30 active:bg-primary/80',
        secondary:
          'bg-secondary text-secondary-foreground hover:bg-secondary/90 focus:ring-secondary/30 active:bg-secondary/80',
        destructive:
          'bg-destructive text-destructive-foreground hover:bg-destructive/90 focus:ring-destructive/30 active:bg-destructive/80',
        outline:
          'border border-input bg-background text-foreground hover:bg-muted/30 focus:ring-ring/30 active:bg-muted/50',
        ghost:
          'text-foreground hover:bg-muted/50 focus:ring-ring/20 active:bg-muted/70',
      },
      size: {
        sm: 'px-3 py-1.5 text-sm',
        md: 'px-4 py-2 text-sm',
        lg: 'px-6 py-2.5 text-base',
        icon: 'size-9 shrink-0',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

export { buttonVariants }

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  children?: ReactNode
  isLoading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      disabled = false,
      isLoading = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      >
        {children}
      </button>
    )
  }
)
Button.displayName = 'Button'

export type ButtonIconProps = ButtonProps & {
  icon?: ReactNode
}

export function ButtonIcon({
  icon,
  children,
  ...props
}: ButtonIconProps) {
  return (
    <Button {...props}>
      {icon && <span className="shrink-0">{icon}</span>}
      {children && <span>{children}</span>}
    </Button>
  )
}
