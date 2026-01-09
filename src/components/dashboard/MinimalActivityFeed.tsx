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
import type { Activity as ActivityType } from '@/lib/types/activity'
import { ACTIVITY_CONFIG } from '@/lib/types/activity'

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
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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
    <div className="flex items-center gap-3 py-2.5 px-3 rounded-xs hover:bg-muted/40 transition-colors group cursor-pointer">
      {/* Icon */}
      <div className={`w-8 h-8 rounded-full bg-muted/50 flex items-center justify-center shrink-0 ${iconColor}`}>
        <Icon className="w-4 h-4" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground truncate">
            {activity.resourceName}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${config.color}`}>
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
        <span className="text-xs text-muted-foreground">
          {formatRelativeTime(activity.timestamp)}
        </span>
        {link && (
          <ChevronRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-primary transition-colors" />
        )}
      </div>
    </div>
  )

  if (link) {
    return <Link to={link}>{content}</Link>
  }

  return content
}

function MinimalActivityFeedContent({ limit = 10 }: MinimalActivityFeedProps) {
  const [showAll, setShowAll] = useState(false)
  const { feed, loading, error, fetchMore } = useActivityFeed({
    limit: showAll ? 50 : limit,
    autoFetch: true,
  })

  const displayedActivities = useMemo(() => {
    return showAll ? feed.items : feed.items.slice(0, limit)
  }, [feed.items, showAll, limit])

  const hasMore = feed.items.length > limit || feed.hasMore

  if (loading && feed.items.length === 0) {
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

  if (feed.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <Activity className="w-10 h-10 text-muted-foreground/30 mb-2" />
        <p className="text-sm text-muted-foreground">No recent activity</p>
        <p className="text-xs text-muted-foreground/70">Activities will appear here as they occur</p>
      </div>
    )
  }

  return (
    <div className="space-y-0.5">
      {displayedActivities.map((activity) => (
        <ActivityRow key={activity.id} activity={activity} />
      ))}

      {/* Load more / Show less */}
      {hasMore && (
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
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              View all activity
            </Button>
          )}
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
