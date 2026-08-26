import { Link } from '@tanstack/react-router'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useMemo } from 'react'
import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

const CHART_COLORS = [
  'var(--dashboard-accent)',
  'oklch(0.65 0.15 35)',
  'oklch(0.55 0.12 155)',
  'oklch(0.60 0.10 250)',
  'oklch(0.55 0.08 280)',
  'oklch(0.62 0.12 45)',
]

interface WeekDataCardProps {
  totalEvents: number
  eventsByType?: Record<string, number>
  eventsToday?: number
  comparison?: string | null
  loading?: boolean
}

export function WeekDataCard({
  totalEvents,
  eventsByType = {},
  eventsToday = 0,
  comparison = null,
  loading = false,
}: WeekDataCardProps) {
  const { segments, conicGradient } = useMemo(() => {
    const entries = Object.entries(eventsByType).filter(([, n]) => n > 0)
    const total = entries.reduce((s, [, n]) => s + n, 0) || 1
    let acc = 0
    const segs = entries.map(([label, count], i) => {
      const pct = (count / total) * 100
      const start = acc
      acc += pct
      return { label, count, start, end: acc, color: CHART_COLORS[i % CHART_COLORS.length] }
    })
    const gradient =
      segs.length > 0
        ? `conic-gradient(${segs.map((s) => `${s.color} ${s.start}% ${s.end}%`).join(', ')})`
        : 'transparent'
    return { segments: segs, conicGradient: gradient }
  }, [eventsByType])

  const hasDonut = segments.length > 0

  return (
    <DashboardCard
      title="This week's data"
      action={
        <button
          type="button"
          className="p-1 text-muted-foreground hover:text-foreground"
          aria-label="Filter"
        >
          <ChevronDown className="w-4 h-4" />
        </button>
      }
    >
      <div className="space-y-4">
        <div>
          <Link
            to="/events"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-[var(--dashboard-accent)] mb-2"
          >
            This week's events
            <ChevronRight className="w-3 h-3" />
          </Link>
          <div className="flex items-baseline gap-2 flex-wrap">
            {loading ? (
              <Skeleton className="h-9 w-24" />
            ) : (
              <span className="font-display text-3xl font-bold text-foreground tabular-nums">
                {totalEvents.toLocaleString()}
              </span>
            )}
            {comparison != null && (
              <span className="text-xs text-muted-foreground">{comparison}</span>
            )}
          </div>
        </div>

        <div className="flex gap-4 items-start">
          <div className="relative shrink-0 w-28 h-28">
            {loading ? (
              <Skeleton className="w-28 h-28 rounded-full" />
            ) : (
              <>
                <div
                  className="absolute inset-0 rounded-full"
                  style={{
                    background: hasDonut ? conicGradient : 'var(--muted)',
                    mask: 'radial-gradient(farthest-side, transparent 62%, black 63%)',
                    WebkitMask: 'radial-gradient(farthest-side, transparent 62%, black 63%)',
                  }}
                  aria-hidden
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="font-display text-xl font-bold text-foreground tabular-nums">
                    {totalEvents.toLocaleString()}
                  </span>
                </div>
              </>
            )}
          </div>
          <ul className="space-y-1 text-xs flex-1 min-w-0">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length loading placeholder; the list never reorders.
                  <li key={i} className="flex items-center gap-2">
                    <Skeleton className="w-2 h-2 rounded-sm" />
                    <Skeleton className="h-3 flex-1 max-w-[80px]" />
                    <Skeleton className="h-3 w-6" />
                  </li>
                ))
              : segments.map((s) => (
                  <li key={s.label} className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 shrink-0 rounded-sm"
                      style={{ backgroundColor: s.color }}
                    />
                    <span className="text-muted-foreground truncate">{s.label}</span>
                    <span className="font-medium tabular-nums ml-auto">
                      {s.count.toLocaleString()}
                    </span>
                  </li>
                ))}
          </ul>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-border/40">
          <SummaryBox
            title="This week's approvals"
            line1="Approved 0, Rejected 0"
            skeleton={loading}
          />
          <SummaryBox
            title="This week's reimbursements"
            line1="Reimbursed 0, Pending 0"
            skeleton={loading}
          />
          <SummaryBox
            title="This week's activity"
            line1={`+${eventsToday} today`}
            skeleton={loading}
          />
        </div>
      </div>
    </DashboardCard>
  )
}

function SummaryBox({
  title,
  line1,
  skeleton,
}: {
  title: string
  line1: string
  skeleton?: boolean
}) {
  return (
    <div className="p-3 rounded-none border border-border/40 bg-muted/20">
      <p className="text-xs font-medium text-muted-foreground mb-1">{title}</p>
      {skeleton ? (
        <Skeleton className="h-4 w-24" />
      ) : (
        <p className="text-sm text-foreground">{line1}</p>
      )}
    </div>
  )
}
