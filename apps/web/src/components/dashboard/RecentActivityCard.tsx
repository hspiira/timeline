import { Link } from '@tanstack/react-router'
import { DashboardCard } from './DashboardCard'
import { MinimalActivityFeed } from './MinimalActivityFeed'

type RecentActivityCardProps = React.ComponentProps<typeof MinimalActivityFeed>

export function RecentActivityCard(props: RecentActivityCardProps) {
  return (
    <DashboardCard
      title="Recent activity"
      action={
        <Link
          to="/events"
          className="text-xs text-muted-foreground hover:text-[var(--dashboard-accent)]"
        >
          View all &gt;
        </Link>
      }
    >
      <MinimalActivityFeed {...props} variant="card" />
    </DashboardCard>
  )
}
