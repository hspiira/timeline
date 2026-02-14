import { useCallback, useEffect, useMemo, useState } from 'react'
import { Calendar, Wifi, WifiOff, BarChart3 } from 'lucide-react'
import { useActivityFeed } from '@/hooks/useActivityFeed'
import { useActivitySubscription, useSimulatedActivityStream } from '@/hooks/useActivitySubscription'
import { useActivityNotifications } from '@/hooks/useActivityNotifications'
import { ActivityRenderer } from './ActivityRenderers'
import { VirtualActivityList } from './VirtualActivityList'
import { ActivitySearchBar } from './ActivitySearchBar'
import { ActivityAnalytics } from './ActivityAnalytics'
import { ActivityProvider, useActivityContext } from '@/context/ActivityContext'
import { Button } from '@/components/ui/button'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import { formatEventDate } from '@/lib/format-date'
import type { ActivityFilter, Activity } from '@/lib/types/activity'

interface ActivityFeedProps {
  filter?: ActivityFilter
  limit?: number
  showAnalytics?: boolean
  enableNotifications?: boolean
}

/**
 * Main Activity Feed Component
 * Wraps the actual feed in provider for context
 */
export function ActivityFeed({
  filter,
  limit = 20,
  ...props
}: ActivityFeedProps & { enableRealTime?: boolean; useSimulation?: boolean }) {
  return (
    <ActivityProvider>
      <ActivityFeedContent filter={filter} limit={limit} {...props} />
    </ActivityProvider>
  )
}

interface ActivityFeedContentProps extends ActivityFeedProps {
  enableRealTime?: boolean
  useSimulation?: boolean
  useVirtualScrolling?: boolean
  showAnalytics?: boolean
  enableNotifications?: boolean
}

/**
 * Activity Feed Content - Inner component with context access
 */
function ActivityFeedContent({
  filter,
  limit,
  enableRealTime = true,
  useSimulation = false,
  useVirtualScrolling = false,
  showAnalytics = false,
  enableNotifications = true,
}: ActivityFeedContentProps) {
  const { selected, setSelected, expanded, toggleExpanded } = useActivityContext()
  const [searchQuery, setSearchQuery] = useState('')
  const [showAnalyticsPanel, setShowAnalyticsPanel] = useState(showAnalytics)

  // Initialize notifications
  const { notifyNewActivity } = useActivityNotifications({
    enableNotifications,
    showForActions: ['created', 'verified'],
    autoCloseDuration: 5000,
  })

  // Merge search query with provided filter
  const mergedFilter = useMemo<ActivityFilter>(() => ({
    ...filter,
    search: searchQuery || filter?.search,
  }), [filter, searchQuery])

  const { feed, loading, error, fetchMore, addActivity } = useActivityFeed({
    limit,
    filter: mergedFilter,
    autoFetch: true,
  })
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>(
    'disconnected'
  )

  /**
   * Handle new activities from real-time subscription
   */
  const handleNewActivity = useCallback(
    (activity: Activity) => {
      addActivity(activity)
      notifyNewActivity(activity)
    },
    [addActivity, notifyNewActivity]
  )

  /**
   * Set up WebSocket subscription
   */
  const subscription = useActivitySubscription(
    enableRealTime
      ? {
          enabled: !useSimulation,
          onNewActivity: handleNewActivity,
          onError: err => {
            console.error('WebSocket error:', err)
            setWsStatus('disconnected')
          },
        }
      : undefined
  )

  /**
   * Use simulated activity stream for testing
   */
  useSimulatedActivityStream(handleNewActivity, useSimulation)

  // Update WS status when subscription state changes
  useEffect(() => {
    if (enableRealTime && !useSimulation) {
      setWsStatus(
        subscription?.isConnected
          ? 'connected'
          : subscription?.isReconnecting
            ? 'connecting'
            : 'disconnected'
      )
    }
  }, [subscription?.isConnected, subscription?.isReconnecting, enableRealTime, useSimulation])

  const hasActivities = feed.items.length > 0

  if (loading && !hasActivities) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <LoadingIcon size="lg" />
          <span className="text-sm">Loading activities...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
          <ErrorIcon />
          <span className="text-sm">{error}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Connection status indicator */}
      {enableRealTime && !useSimulation && (
        <div className="flex items-center justify-between px-3 py-2 text-xs rounded-none bg-muted/30 border border-border/50">
          <div className="flex items-center gap-2">
            {wsStatus === 'connected' && (
              <>
                <Wifi className="w-3 h-3 text-green-600 dark:text-green-400" />
                <span className="text-muted-foreground">Real-time updates active</span>
              </>
            )}
            {wsStatus === 'connecting' && (
              <>
                <LoadingIcon size="sm" className="text-amber-600 dark:text-amber-400" />
                <span className="text-muted-foreground">Connecting...</span>
              </>
            )}
            {wsStatus === 'disconnected' && (
              <>
                <WifiOff className="w-3 h-3 text-red-600 dark:text-red-400" />
                <span className="text-muted-foreground">Offline - showing cached activities</span>
              </>
            )}
          </div>
          {subscription?.reconnectAttempts > 0 && wsStatus === 'disconnected' && (
            <span className="text-xs text-muted-foreground">
              Retries: {subscription.reconnectAttempts}/5
            </span>
          )}
        </div>
      )}

      {/* Simulation badge */}
      {useSimulation && (
        <div className="flex items-center gap-2 px-3 py-2 text-xs rounded-none bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800">
          <span className="text-blue-700 dark:text-blue-300">
            🧪 Using simulated activities for demo
          </span>
        </div>
      )}

      {/* Search bar and Analytics toggle - Always visible */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <ActivitySearchBar onSearch={setSearchQuery} delay={300} />
        </div>
        {hasActivities && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAnalyticsPanel(!showAnalyticsPanel)}
            className="gap-2 whitespace-nowrap"
          >
            <BarChart3 className="w-4 h-4" />
            {showAnalyticsPanel ? 'Hide' : 'Show'} Analytics
          </Button>
        )}
      </div>

      {/* Analytics panel display */}
      {hasActivities && showAnalyticsPanel && (
        <ActivityAnalytics activities={feed.items} compact={false} />
      )}

      {/* Empty state - shown when no activities to display */}
      {!hasActivities && (
        <div className="bg-card/80 backdrop-blur-sm rounded-none p-12 border border-border/50 text-center">
          <Calendar className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {searchQuery ? 'No activities found' : 'No activities yet'}
          </h3>
          <p className="text-muted-foreground">
            {searchQuery
              ? `No activities match "${searchQuery}". Try adjusting your search.`
              : 'Activities will appear here as events occur in the system'}
          </p>
        </div>
      )}

      {/* Activity items - Virtual or Standard - Only shown when activities exist */}
      {hasActivities && (
        <>
          {useVirtualScrolling ? (
            <VirtualActivityList
              activities={feed.items}
              selectedId={selected}
              expandedIds={expanded}
              onSelect={setSelected}
              onExpand={toggleExpanded}
              height={600}
              itemHeight={100}
            />
          ) : (
            feed.items.map(activity => (
              <ActivityRenderer
                key={activity.id}
                activity={activity}
                isSelected={selected === activity.id}
                onSelect={setSelected}
                onExpand={toggleExpanded}
              />
            ))
          )}
        </>
      )}

      {/* Load more button */}
      {hasActivities && feed.hasMore && (
        <div className="flex justify-center pt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchMore}
            disabled={loading}
            isLoading={loading}
          >
            {loading ? (
              <>
                <LoadingIcon size="sm" />
                Loading more...
              </>
            ) : (
              `Load More (${feed.total - feed.items.length} remaining)`
            )}
          </Button>
        </div>
      )}

      {/* Activity count */}
      {feed.total > 0 && (
        <div className="text-xs text-muted-foreground text-center pt-2">
          Showing {feed.items.length} of {feed.total} activities
        </div>
      )}
    </div>
  )
}

/**
 * Activity Feed by Date Groups
 * Organizes activities into collapsible date groups
 */
export function ActivityFeedByDate({
  filter,
  limit = 20,
  showAnalytics,
  enableNotifications,
}: ActivityFeedProps) {
  return (
    <ActivityProvider>
      <ActivityFeedByDateContent
        filter={filter}
        limit={limit}
        showAnalytics={showAnalytics}
        enableNotifications={enableNotifications}
      />
    </ActivityProvider>
  )
}

/**
 * Activity Feed by Date Content
 */
function ActivityFeedByDateContent({
  filter,
  limit,
  showAnalytics = false,
}: ActivityFeedProps) {
  const { selected, setSelected, toggleExpanded } = useActivityContext()
  const [searchQuery, setSearchQuery] = useState('')
  const [showAnalyticsPanel, setShowAnalyticsPanel] = useState(showAnalytics)

  // Merge search query with provided filter
  const mergedFilter = useMemo<ActivityFilter>(() => ({
    ...filter,
    search: searchQuery || filter?.search,
  }), [filter, searchQuery])

  const { feed, loading, error } = useActivityFeed({
    limit: limit || 100,
    filter: mergedFilter,
    autoFetch: true,
  })

  const hasActivities = feed.items.length > 0

  // Group activities by date
  const groupedActivities = useMemo(() => {
    const groups: Record<string, typeof feed.items> = {}

    feed.items.forEach(activity => {
      const date = formatEventDate(activity.timestamp)
      if (!groups[date]) {
        groups[date] = []
      }
      groups[date].push(activity)
    })

    return groups
  }, [feed.items])

  const [collapsedDates, setCollapsedDates] = useState<Set<string>>(new Set())

  const toggleDateCollapsed = useCallback((date: string) => {
    setCollapsedDates(prev => {
      const newSet = new Set(prev)
      if (newSet.has(date)) {
        newSet.delete(date)
      } else {
        newSet.add(date)
      }
      return newSet
    })
  }, [])

  if (loading && !hasActivities) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <LoadingIcon size="lg" />
          <span className="text-sm">Loading activities...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
          <ErrorIcon />
          <span className="text-sm">{error}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Search bar and Analytics toggle - Always visible */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <ActivitySearchBar onSearch={setSearchQuery} delay={300} />
        </div>
        {hasActivities && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAnalyticsPanel(!showAnalyticsPanel)}
            className="gap-2 whitespace-nowrap"
          >
            <BarChart3 className="w-4 h-4" />
            {showAnalyticsPanel ? 'Hide' : 'Show'} Analytics
          </Button>
        )}
      </div>

      {/* Analytics panel display */}
      {hasActivities && showAnalyticsPanel && (
        <ActivityAnalytics activities={feed.items} compact={false} />
      )}

      {/* Empty state messages */}
      {!hasActivities && (
        <div className="bg-card/80 backdrop-blur-sm rounded-none p-12 border border-border/50 text-center">
          <Calendar className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {searchQuery ? 'No activities found' : 'No activities yet'}
          </h3>
          <p className="text-muted-foreground">
            {searchQuery
              ? `No activities match "${searchQuery}". Try adjusting your search.`
              : 'Activities will appear here as events occur in the system'}
          </p>
        </div>
      )}

      {/* Grouped activities by date */}
      {hasActivities && Object.entries(groupedActivities).map(([date, activities]) => {
        const isCollapsed = collapsedDates.has(date)

        return (
          <div key={date}>
            {/* Date header with collapse toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => toggleDateCollapsed(date)}
              className="gap-2 mb-3 justify-start"
            >
              <span
                className={`transform transition-transform ${
                  isCollapsed ? '' : 'rotate-90'
                }`}
              >
                ▶
              </span>
              <span className="font-semibold text-foreground">{date}</span>
              <span className="text-xs text-muted-foreground">
                ({activities.length})
              </span>
            </Button>

            {/* Activities list */}
            {!isCollapsed && (
              <div className="ml-4 space-y-2 max-h-96 overflow-y-auto">
                {activities.map(activity => (
                  <ActivityRenderer
                    key={activity.id}
                    activity={activity}
                    isSelected={selected === activity.id}
                    onSelect={setSelected}
                    onExpand={toggleExpanded}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
