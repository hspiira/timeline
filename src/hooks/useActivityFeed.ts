import { useCallback, useEffect, useState } from 'react'
import { timelineApi } from '@/lib/api-client'
import type { Activity, ActivityFeed, ActivityFilter } from '@/lib/types/activity'
import { eventToActivity } from '@/lib/types/activity'

interface UseActivityFeedOptions {
  limit?: number
  filter?: ActivityFilter
  autoFetch?: boolean
}

export function useActivityFeed({
  limit = 20,
  filter,
  autoFetch = true,
}: UseActivityFeedOptions = {}) {
  const [feed, setFeed] = useState<ActivityFeed>({
    items: [],
    hasMore: false,
    total: 0,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [_cursor, setCursor] = useState<string | null>(null)

  /**
   * Fetch activities from API
   * In a real scenario, the backend would handle:
   * - Pagination with cursor
   * - Filtering
   * - Activity generation from events
   */
  const fetchActivities = useCallback(
    async (_nextCursor?: string) => {
      setLoading(true)
      setError(null)

      try {
        // For now, convert events to activities
        // In production, this would call a dedicated activity endpoint
        const { data: events, error: apiError } = await timelineApi.events.listAll()

        if (apiError) {
          setError('Failed to load activities')
          return
        }

        if (!events || !Array.isArray(events)) {
          setFeed({
            items: [],
            hasMore: false,
            total: 0,
          })
          return
        }

        // Convert events to activities
        let activities = events
          .map(event => eventToActivity(event))
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())

        // Apply filters
        if (filter) {
          activities = applyActivityFilters(activities, filter)
        }

        // Simulate pagination
        const start = 0
        const end = start + limit
        const items = activities.slice(start, end)
        const hasMore = activities.length > end

        setFeed({
          items,
          hasMore,
          cursor: hasMore ? end.toString() : undefined,
          total: activities.length,
          lastFetch: new Date(),
        })
        setCursor(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    },
    [limit, filter]
  )

  /**
   * Load more activities with pagination
   */
  const fetchMore = useCallback(async () => {
    if (!feed.hasMore || loading) return

    setLoading(true)
    setError(null)

    try {
      const { data: events } = await timelineApi.events.listAll()

      if (!events || !Array.isArray(events)) {
        return
      }

      let activities = events
        .map(event => eventToActivity(event))
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())

      if (filter) {
        activities = applyActivityFilters(activities, filter)
      }

      const currentCount = feed.items.length
      const start = currentCount
      const end = start + limit
      const newItems = activities.slice(start, end)
      const hasMore = activities.length > end

      setFeed(prev => ({
        ...prev,
        items: [...prev.items, ...newItems],
        hasMore,
        cursor: hasMore ? end.toString() : undefined,
        total: activities.length,
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [feed.hasMore, feed.items.length, limit, filter, loading])

  /**
   * Refresh activities from the beginning
   */
  const refresh = useCallback(async () => {
    setCursor(null)
    await fetchActivities()
  }, [fetchActivities])

  /**
   * Add new activity to the feed
   */
  const addActivity = useCallback((activity: Activity) => {
    setFeed(prev => ({
      ...prev,
      items: [activity, ...prev.items],
      total: prev.total + 1,
    }))
  }, [])

  /**
   * Update an activity
   */
  const updateActivity = useCallback((id: string, updates: Partial<Activity>) => {
    setFeed(prev => ({
      ...prev,
      items: prev.items.map(item =>
        item.id === id ? { ...item, ...updates } : item
      ),
    }))
  }, [])

  /**
   * Remove an activity
   */
  const removeActivity = useCallback((id: string) => {
    setFeed(prev => ({
      ...prev,
      items: prev.items.filter(item => item.id !== id),
      total: prev.total - 1,
    }))
  }, [])

  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      fetchActivities()
    }
  }, [autoFetch, fetchActivities])

  return {
    feed,
    loading,
    error,
    fetchActivities,
    fetchMore,
    refresh,
    addActivity,
    updateActivity,
    removeActivity,
  }
}

/**
 * Apply filters to activities
 */
function applyActivityFilters(
  activities: Activity[],
  filter: ActivityFilter
): Activity[] {
  return activities.filter(activity => {
    // Filter by actions
    if (
      filter.actions &&
      filter.actions.length > 0 &&
      !filter.actions.includes(activity.action)
    ) {
      return false
    }

    // Filter by resource types
    if (
      filter.resourceTypes &&
      filter.resourceTypes.length > 0 &&
      !filter.resourceTypes.includes(activity.resourceType)
    ) {
      return false
    }

    // Filter by date range
    if (filter.dateRange) {
      const { from, to } = filter.dateRange
      if (activity.timestamp < from || activity.timestamp > to) {
        return false
      }
    }

    // Filter by user ID
    if (filter.userId && activity.userId !== filter.userId) {
      return false
    }

    // Filter by priority
    if (
      filter.priority &&
      filter.priority.length > 0 &&
      !filter.priority.includes(activity.priority)
    ) {
      return false
    }

    // Filter by search text
    if (filter.search) {
      const searchLower = filter.search.toLowerCase()
      const matches =
        activity.resourceName.toLowerCase().includes(searchLower) ||
        activity.description?.toLowerCase().includes(searchLower) ||
        activity.resourceId.toLowerCase().includes(searchLower)
      if (!matches) {
        return false
      }
    }

    return true
  })
}
