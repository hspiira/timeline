/**
 * Single source for semantic status (integrity badges, connector status).
 * Uses CSS variables from design tokens: --status-ok, --status-warn, --status-error, --status-repair.
 */

export type StatusKind = 'ok' | 'warn' | 'error' | 'repair' | 'unknown'

/** Tailwind class names for status backgrounds and text (use with cn()). */
export const statusTokenClasses: Record<StatusKind, { bg: string; text: string }> = {
  ok: { bg: 'bg-status-ok', text: 'text-status-ok-foreground' },
  warn: { bg: 'bg-status-warn', text: 'text-status-warn-foreground' },
  error: { bg: 'bg-status-error', text: 'text-status-error-foreground' },
  repair: { bg: 'bg-status-repair', text: 'text-status-repair-foreground' },
  unknown: { bg: 'bg-muted', text: 'text-muted-foreground' },
}

/** Map integrity/connector status string to StatusKind. */
export function toStatusKind(status: string | null | undefined): StatusKind {
  if (!status) return 'unknown'
  const s = status.toLowerCase()
  if (
    s === 'valid' ||
    s === 'running' ||
    s === 'ok' ||
    s === 'healthy' ||
    s === 'sealed' ||
    s === 'completed'
  )
    return 'ok'
  if (s === 'degraded' || s === 'pending_approval' || s === 'approved' || s === 'broken')
    return 'warn'
  if (s === 'chain_break' || s === 'repaired' || s === 'failed' || s === 'stopped')
    return s === 'repaired' ? 'repair' : 'error'
  if (s === 'repair' || s === 'repaired') return 'repair'
  return 'unknown'
}
