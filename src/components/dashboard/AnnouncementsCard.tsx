import { DashboardCard } from './DashboardCard'
import { Skeleton } from '@/components/ui/Skeleton'

const SKELETON_ITEMS = 3

export function AnnouncementsCard() {
  return (
    <DashboardCard
      title="Announcements"
      action={
        <a href="#" className="text-xs text-muted-foreground hover:text-[var(--dashboard-accent)]">
          View all &gt;
        </a>
      }
    >
      <ul className="space-y-3">
        {Array.from({ length: SKELETON_ITEMS }).map((_, i) => (
          <li key={i} className="flex gap-2">
            <Skeleton className="h-4 w-12 shrink-0" />
            <Skeleton className="h-4 flex-1" />
          </li>
        ))}
      </ul>
    </DashboardCard>
  )
}
