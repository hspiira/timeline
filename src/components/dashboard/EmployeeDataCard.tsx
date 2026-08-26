import { Link } from '@tanstack/react-router'
import { RefreshCw } from 'lucide-react'
import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

interface EmployeeDataCardProps {
  totalSubjects: number
  subjectsByType?: Record<string, number>
  onRefresh?: () => void
  loading?: boolean
}

const MAX_CATEGORIES = 8

export function EmployeeDataCard({
  totalSubjects,
  subjectsByType = {},
  onRefresh,
  loading = false,
}: EmployeeDataCardProps) {
  const entries = Object.entries(subjectsByType)
    .filter(([, n]) => n > 0)
    .slice(0, MAX_CATEGORIES)

  return (
    <DashboardCard
      title="Subject data"
      action={
        <div className="flex items-center gap-2">
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
            to="/subjects"
            className="text-xs text-muted-foreground hover:text-[var(--dashboard-accent)]"
          >
            View details &gt;
          </Link>
        </div>
      }
    >
      <div className="space-y-4">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Total subjects</p>
          {loading ? (
            <Skeleton className="h-10 w-20" />
          ) : (
            <span className="font-display text-3xl font-bold text-foreground tabular-nums">
              {totalSubjects.toLocaleString()}
            </span>
          )}
        </div>
        <ul className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length loading placeholder; the list never reorders.
                <li key={i} className="flex justify-between gap-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-8" />
                </li>
              ))
            : entries.length > 0
              ? entries.map(([label, count]) => (
                  <li key={label} className="flex justify-between gap-2">
                    <span className="text-muted-foreground truncate">{label}</span>
                    <span className="font-medium tabular-nums shrink-0">
                      {count.toLocaleString()}
                    </span>
                  </li>
                ))
              : [
                  <li key="none" className="col-span-2 text-muted-foreground text-sm">
                    No subject types yet
                  </li>,
                ]}
        </ul>
      </div>
    </DashboardCard>
  )
}
