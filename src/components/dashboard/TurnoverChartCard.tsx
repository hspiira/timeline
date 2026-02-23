import { DashboardCard } from './DashboardCard'
import { Skeleton } from '@/components/ui/Skeleton'

/** Placeholder metrics; can be wired to real data later */
interface TurnoverChartCardProps {
  startCount?: number
  endCount?: number
  added?: number
  removed?: number
  loading?: boolean
}

export function TurnoverChartCard({
  startCount = 0,
  endCount = 0,
  added = 0,
  removed = 0,
  loading = false,
}: TurnoverChartCardProps) {
  return (
    <DashboardCard title="Activity trend">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <select
            className="text-xs border border-border/60 bg-muted/30 px-2 py-1.5 text-foreground rounded-none"
            aria-label="Scope"
          >
            <option>All</option>
          </select>
          <select
            className="text-xs border border-border/60 bg-muted/30 px-2 py-1.5 text-foreground rounded-none"
            aria-label="Group by"
          >
            <option>By date</option>
          </select>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-3 border border-border/40 rounded-none">
                <Skeleton className="h-3 w-16 mb-2" />
                <Skeleton className="h-7 w-12" />
              </div>
            ))
          ) : (
            <>
              <MetricBox label="Start" value={startCount} />
              <MetricBox label="End" value={endCount} />
              <MetricBox label="Added" value={added} />
              <MetricBox label="Removed" value={removed} />
            </>
          )}
        </div>
        <div className="h-48 flex items-end gap-0.5 pt-4 border-t border-border/40">
          {loading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            Array.from({ length: 14 }).map((_, i) => (
              <div
                key={i}
                className="flex-1 min-w-0 flex flex-col gap-1 justify-end"
                style={{ height: '100%' }}
              >
                <div
                  className="w-full rounded-none bg-[var(--dashboard-accent-muted)]"
                  style={{
                    height: `${30 + (i % 5) * 15}%`,
                    minHeight: 4,
                  }}
                  aria-hidden
                />
                <div
                  className="w-full rounded-none bg-muted"
                  style={{
                    height: `${20 + (i % 4) * 12}%`,
                    minHeight: 4,
                  }}
                  aria-hidden
                />
              </div>
            ))
          )}
        </div>
      </div>
    </DashboardCard>
  )
}

function MetricBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-3 border border-border/40 rounded-none">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="font-display text-lg font-bold text-foreground tabular-nums">{value.toLocaleString()}</p>
    </div>
  )
}
