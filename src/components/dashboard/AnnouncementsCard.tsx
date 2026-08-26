import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

const SKELETON_ITEMS = 3

export function AnnouncementsCard() {
  return (
    <DashboardCard
      title="Announcements"
      action={<span className="text-xs text-muted-foreground">View all &gt;</span>}
    >
      <ul className="space-y-3">
        {Array.from({ length: SKELETON_ITEMS }).map((_, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length loading placeholder; the list never reorders.
          <li key={i} className="flex gap-2">
            <Skeleton className="h-4 w-12 shrink-0" />
            <Skeleton className="h-4 flex-1" />
          </li>
        ))}
      </ul>
    </DashboardCard>
  )
}
