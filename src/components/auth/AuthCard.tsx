import { cn } from '@/lib/utils'

/**
 * Wrapper for the auth pages: centred logo above the content.
 *
 * Set off from the page by a flat fill only — no border, no shadow, no gradient.
 *
 * Three-step value scale, measured against the dark page colour #13120a:
 *   page  #13120a
 *   panel #24231b  (white/0.07, 1.19:1 vs page — visible but quiet)
 *   input #13120a  (page colour, so fields read as recessed wells in the panel)
 *
 * `bg-card` is deliberately not used: the dark theme's `--card` is neutral
 * oklch(0.12), which is darker than the warm `--background`, so it made the
 * panel recede and left the inputs looking lighter than their container.
 */
export function AuthCard({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('w-full max-w-md bg-white/[0.07] px-8 py-10', className)}>
      <img
        src="/logo.svg"
        alt=""
        className="mx-auto mb-8 h-8 w-8"
        aria-hidden
      />
      {children}
    </div>
  )
}
