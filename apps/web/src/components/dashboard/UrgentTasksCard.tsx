import { Link } from '@tanstack/react-router'
import { Flame, RefreshCw } from 'lucide-react'
import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

interface UrgentTasksCardProps {
  /** Number to show in center (e.g. open urgent count) */
  count?: number
  onRefresh?: () => void
  loading?: boolean
}

const SKELETON_ITEMS = 3

export function UrgentTasksCard({ count = 0, onRefresh, loading = false }: UrgentTasksCardProps) {
  return (
    <DashboardCard
      title="Urgent"
      action={
        <div className="flex items-center gap-1">
          <Flame className="w-4 h-4 text-orange-500" />
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="p-1 text-muted-foreground hover:text-foreground"
              aria-label="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
          <Link
            to="/events"
            className="text-xs text-muted-foreground hover:text-[var(--dashboard-accent)]"
          >
            View details &gt;
          </Link>
        </div>
      }
    >
      <div className="flex gap-4">
        <div className="relative shrink-0 w-24 h-24">
          {loading ? (
            <Skeleton className="w-24 h-24 rounded-full" />
          ) : (
            <>
              <div
                className="absolute inset-0 rounded-full border-4 border-muted"
                style={{
                  background: `conic-gradient(oklch(0.65 0.15 35) 0% ${Math.min(count * 2.5, 100)}%, var(--muted) ${Math.min(count * 2.5, 100)}% 100%)`,
                  mask: 'radial-gradient(farthest-side, transparent 62%, black 63%)',
                  WebkitMask: 'radial-gradient(farthest-side, transparent 62%, black 63%)',
                }}
                aria-hidden
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-display text-2xl font-bold text-foreground tabular-nums">
                  {count}
                </span>
              </div>
            </>
          )}
        </div>
        <ul className="flex-1 space-y-2 min-w-0">
          {loading
            ? Array.from({ length: SKELETON_ITEMS }).map((_, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length loading placeholder; the list never reorders.
                <li key={i}>
                  <Skeleton className="h-4 w-full mb-1" />
                  <Skeleton className="h-3 w-3/4" />
                </li>
              ))
            : [
                <li key="1" className="text-sm text-muted-foreground">
                  Missing required data: 0 items
                </li>,
                <li key="2" className="text-sm text-muted-foreground">
                  Pending approvals: 0
                </li>,
                <li key="3" className="text-sm text-muted-foreground">
                  Overdue: 0
                </li>,
              ]}
        </ul>
      </div>
    </DashboardCard>
  )
}
