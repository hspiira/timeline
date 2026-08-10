import { useMemo } from 'react'

const CHART_COLORS = [
  'var(--dashboard-accent)',
  'oklch(0.65 0.15 35)',   // orange
  'oklch(0.55 0.12 155)',  // green
  'oklch(0.60 0.10 250)',  // blue
  'oklch(0.55 0.08 280)',  // purple
  'oklch(0.62 0.12 45)',   // amber
]

interface EventsDonutCardProps {
  totalEvents: number
  eventsByType?: Record<string, number>
  eventsToday?: number
}

export function EventsDonutCard({
  totalEvents,
  eventsByType = {},
  eventsToday = 0,
}: EventsDonutCardProps) {
  const { segments, conicGradient } = useMemo(() => {
    const entries = Object.entries(eventsByType).filter(([, n]) => n > 0)
    const total = entries.reduce((s, [, n]) => s + n, 0) || 1
    let acc = 0
    const segs = entries.map(([label, count], i) => {
      const pct = (count / total) * 100
      const start = acc
      acc += pct
      return {
        label,
        count,
        start,
        end: acc,
        color: CHART_COLORS[i % CHART_COLORS.length],
      }
    })
    const gradient =
      segs.length > 0
        ? `conic-gradient(${segs.map((s) => `${s.color} ${s.start}% ${s.end}%`).join(', ')})`
        : 'transparent'
    return { segments: segs, conicGradient: gradient }
  }, [eventsByType])

  const hasDonut = segments.length > 0

  return (
    <div className="rounded-none border border-border/60 bg-card/80 backdrop-blur-sm overflow-hidden">
      <div className="p-4 md:p-5 flex flex-col sm:flex-row gap-4 sm:gap-6 items-start">
        {/* Donut + center total */}
        <div className="relative shrink-0 w-32 h-32 sm:w-36 sm:h-36">
          <div
            className="absolute inset-0 rounded-full border-[10px] border-muted/60"
            style={{
              background: hasDonut ? conicGradient : 'transparent',
              mask: 'radial-gradient(farthest-side, transparent 65%, black 66%)',
              WebkitMask: 'radial-gradient(farthest-side, transparent 65%, black 66%)',
            }}
            aria-hidden
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-display text-2xl sm:text-3xl font-bold text-foreground tabular-nums">
              {totalEvents.toLocaleString()}
            </span>
          </div>
        </div>

        {/* Legend + mini metrics */}
        <div className="flex-1 min-w-0 w-full">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
            Events by type
          </p>
          {segments.length > 0 ? (
            <ul className="space-y-1.5">
              {segments.map((s) => (
                <li key={s.label} className="flex items-center gap-2 text-sm">
                  <span
                    className="w-2.5 h-2.5 shrink-0 rounded-sm"
                    style={{ backgroundColor: s.color }}
                    aria-hidden
                  />
                  <span className="text-muted-foreground truncate">{s.label}</span>
                  <span className="font-medium tabular-nums ml-auto">{s.count.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No events yet</p>
          )}
          {eventsToday > 0 && (
            <p className="text-xs text-muted-foreground mt-3 pt-3 border-t border-border/40">
              +{eventsToday} today
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
