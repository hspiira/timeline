import { useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Calendar,
  User,
  FileText,
  Workflow,
  Shield,
  ChevronRight,
  Activity,
  type LucideIcon,
} from 'lucide-react'
import { useActivityFeed } from '@/hooks/useActivityFeed'
import { ActivityProvider } from '@/context/ActivityContext'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'
import { formatShortDate } from '@/lib/format-date'
import type { Activity as ActivityType } from '@/lib/types/activity'
import { ACTIVITY_CONFIG, eventToActivity } from '@/lib/types/activity'

/** Minimal event shape from analytics dashboard recent_events */
export type RecentEventItem = {
  id: string
  subject_id: string
  event_type: string
  event_time: string
  payload?: Record<string, unknown>
}

const RESOURCE_ICONS: Record<ActivityType['resourceType'], LucideIcon> = {
  event: Calendar,
  subject: User,
  document: FileText,
  workflow: Workflow,
  permission: Shield,
  role: Shield,
}

const RESOURCE_COLORS: Record<ActivityType['resourceType'], string> = {
  event: 'text-blue-500',
  subject: 'text-purple-500',
  document: 'text-amber-500',
  workflow: 'text-cyan-500',
  permission: 'text-green-500',
  role: 'text-indigo-500',
}

interface MinimalActivityFeedProps {
  limit?: number
  /** When provided (e.g. from analytics dashboard), show these instead of fetching */
  recentEvents?: RecentEventItem[] | null
}

function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatShortDate(date)
}

function ActivityRow({ activity }: { activity: ActivityType }) {
  const Icon = RESOURCE_ICONS[activity.resourceType]
  const iconColor = RESOURCE_COLORS[activity.resourceType]
  const config = ACTIVITY_CONFIG[activity.action]

  // Build link based on resource type
  const getLink = () => {
    if (activity.resourceType === 'subject') {
      return `/subjects/${activity.resourceId}`
    }
    if (activity.resourceType === 'event' && activity.metadata?.subject_id) {
      return `/subjects/${activity.metadata.subject_id}`
    }
    return null
  }

  const link = getLink()
  const content = (
    <div className="flex items-center gap-3 py-3 px-4 border-b border-border/40 last:border-b-0 hover:bg-[var(--dashboard-accent-muted)]/50 transition-colors group cursor-pointer">
      {/* Accent bar + icon */}
      <div
        className="w-1 h-8 rounded-full shrink-0 bg-[var(--dashboard-accent)] opacity-60 group-hover:opacity-100 transition-opacity"
        aria-hidden
      />
      <div className={`w-9 h-9 rounded-none bg-muted/60 flex items-center justify-center shrink-0 ${iconColor}`}>
        <Icon className="w-4 h-4" strokeWidth={1.75} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-foreground truncate">
            {activity.resourceName}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-none font-medium ${config.color}`}>
            {config.label}
          </span>
        </div>
        {activity.description && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            {activity.description}
          </p>
        )}
      </div>

      {/* Time and arrow */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-muted-foreground tabular-nums">
          {formatRelativeTime(activity.timestamp)}
        </span>
        {link && (
          <ChevronRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-[var(--dashboard-accent)] transition-colors" />
        )}
      </div>
    </div>
  )

  if (link) {
    return <Link to={link}>{content}</Link>
  }

  return content
}

function MinimalActivityFeedContent({
  limit = 10,
  recentEvents: recentEventsProp,
}: MinimalActivityFeedProps) {
  const [showAll, setShowAll] = useState(false)
  const { feed, loading, error, fetchMore } = useActivityFeed({
    limit: showAll ? 50 : limit,
    autoFetch: recentEventsProp == null || recentEventsProp.length === 0,
  })

  const activitiesFromDashboard = useMemo(() => {
    if (!recentEventsProp?.length) return []
    return recentEventsProp.map((e) => eventToActivity(e))
  }, [recentEventsProp])

  const sourceItems = activitiesFromDashboard.length > 0 ? activitiesFromDashboard : feed.items
  const displayedActivities = useMemo(() => {
    return showAll ? sourceItems : sourceItems.slice(0, limit)
  }, [sourceItems, showAll, limit])

  const hasMore =
    activitiesFromDashboard.length > 0
      ? sourceItems.length > limit
      : feed.items.length > limit || feed.hasMore

  if (loading && sourceItems.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <LoadingIcon size="md" />
          <span className="text-xs">Loading activity...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center gap-2 text-red-500">
          <ErrorIcon />
          <span className="text-xs">{error}</span>
        </div>
      </div>
    )
  }

  if (sourceItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="w-12 h-12 rounded-none bg-[var(--dashboard-accent-muted)] flex items-center justify-center mb-3">
          <Activity className="w-6 h-6 text-[var(--dashboard-accent)]" strokeWidth={1.5} />
        </div>
        <p className="text-sm font-medium text-foreground">No recent activity</p>
        <p className="text-xs text-muted-foreground mt-1">Activities will appear here as they occur</p>
      </div>
    )
  }

  return (
    <div className="space-y-0.5">
      {displayedActivities.map((activity) => (
        <ActivityRow key={activity.id} activity={activity} />
      ))}

      {/* Load more / Show less — only when using fetched feed, not dashboard recent_events */}
      {hasMore && activitiesFromDashboard.length === 0 && (
        <div className="pt-2 flex justify-center">
          {showAll ? (
            <div className="flex gap-2">
              {feed.hasMore && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={fetchMore}
                  disabled={loading}
                  className="text-xs"
                >
                  {loading ? <LoadingIcon size="sm" /> : 'Load More'}
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAll(false)}
                className="text-xs"
              >
                Show Less
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAll(true)}
              className="text-xs text-muted-foreground hover:text-foreground hover:bg-[var(--dashboard-accent-muted)]"
            >
              View all activity
            </Button>
          )}
        </div>
      )}
      {hasMore && activitiesFromDashboard.length > 0 && showAll && (
        <div className="pt-2 flex justify-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAll(false)}
            className="text-xs"
          >
            Show Less
          </Button>
        </div>
      )}
    </div>
  )
}

export function MinimalActivityFeed(props: MinimalActivityFeedProps) {
  return (
    <ActivityProvider>
      <MinimalActivityFeedContent {...props} />
    </ActivityProvider>
  )
}
