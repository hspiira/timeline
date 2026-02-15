import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from '@radix-ui/react-slot'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-none text-sm font-medium transition-colors outline-none focus:ring-2 focus:ring-offset-0 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*="size-"])]:size-4 shrink-0 [&_svg]:shrink-0 focus-visible:ring-ring/30 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground hover:bg-primary/90 focus:ring-primary/30',
        primary:
          'bg-primary text-primary-foreground hover:bg-primary/90 focus:ring-primary/30',
        destructive:
          'bg-destructive text-destructive-foreground hover:bg-destructive/90 focus:ring-destructive/30',
        outline:
          'border border-input bg-background text-foreground hover:bg-muted/30 focus:ring-ring/30',
        secondary:
          'bg-secondary text-secondary-foreground hover:bg-secondary/80 focus:ring-secondary/30',
        ghost:
          'hover:bg-accent hover:text-accent-foreground focus:ring-ring/20',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2 has-[>svg]:px-3',
        md: 'h-9 px-4 py-2 has-[>svg]:px-3',
        xs: 'h-6 gap-1 rounded-none px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*="size-"])]:size-3',
        sm: 'h-8 gap-1.5 rounded-none px-3 has-[>svg]:px-2.5',
        lg: 'h-10 rounded-none px-6 has-[>svg]:px-4',
        icon: 'size-9 rounded-none',
        'icon-xs': 'size-6 rounded-none [&_svg:not([class*="size-"])]:size-3',
        'icon-sm': 'size-8 rounded-none',
        'icon-lg': 'size-10 rounded-none',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

function Button({
  className,
  variant = 'default',
  size = 'default',
  asChild = false,
  isLoading = false,
  children,
  disabled,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
    isLoading?: boolean
  }) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled ?? isLoading}
      {...props}
    >
      {!asChild && isLoading && (
        <Loader2 className="size-4 animate-spin shrink-0" />
      )}
      {children}
    </Comp>
  )
}

export { Button, buttonVariants }
