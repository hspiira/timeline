import { cn } from '@/lib/utils'
import { toStatusKind, type StatusKind } from '@/lib/status-tokens'

export type IntegrityStatus = 'valid' | 'broken' | 'unknown'

const integrityToKind: Record<IntegrityStatus, StatusKind> = {
  valid: 'ok',
  broken: 'error',
  unknown: 'unknown',
}

function toKind(status: IntegrityStatus | StatusKind | string): StatusKind {
  if (status === 'valid' || status === 'broken' || status === 'unknown') {
    return integrityToKind[status]
  }
  if (typeof status === 'string') return toStatusKind(status)
  return status
}

interface StatusBadgeProps {
  status: IntegrityStatus | StatusKind | string
  label?: string
  className?: string
  /** When true, render as a small dot only (for tables/cards) */
  dotOnly?: boolean
}

export function StatusBadge({ status, label, className, dotOnly }: StatusBadgeProps) {
  const kind = toKind(status)

  const displayLabel = label ?? (status === 'valid' ? 'Valid' : status === 'broken' ? 'Broken' : 'Unknown')

  if (dotOnly) {
    return (
      <span
        className={cn(
          'inline-block w-2 h-2 rounded-full shrink-0',
          kind === 'ok' && 'bg-status-ok',
          kind === 'warn' && 'bg-status-warn',
          kind === 'error' && 'bg-status-error',
          kind === 'repair' && 'bg-status-repair',
          kind === 'unknown' && 'bg-muted-foreground/50',
          className
        )}
        title={displayLabel}
        aria-label={displayLabel}
      />
    )
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-none border text-xs font-medium',
        kind === 'ok' && 'border-status-ok/50 bg-status-ok/10 text-status-ok',
        kind === 'warn' && 'border-status-warn/50 bg-status-warn/10 text-status-warn',
        kind === 'error' && 'border-status-error/50 bg-status-error/10 text-status-error',
        kind === 'repair' && 'border-status-repair/50 bg-status-repair/10 text-status-repair',
        kind === 'unknown' && 'border-border bg-muted/50 text-muted-foreground',
        className
      )}
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full shrink-0',
          kind === 'ok' && 'bg-status-ok',
          kind === 'warn' && 'bg-status-warn',
          kind === 'error' && 'bg-status-error',
          kind === 'repair' && 'bg-status-repair',
          kind === 'unknown' && 'bg-muted-foreground/50'
        )}
      />
      {displayLabel}
    </span>
  )
}
