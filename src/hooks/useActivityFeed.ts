import { useCallback, useEffect, useMemo, useState } from 'react'
import { timelineApi } from '@/lib/api-client'
import type { Activity, ActivityFeed, ActivityFilter } from '@/lib/types/activity'
import { eventToActivity } from '@/lib/types/activity'

interface UseActivityFeedOptions {
  limit?: number
  filter?: ActivityFilter
  autoFetch?: boolean
}

const DEFAULT_PAGE_SIZE = 20
const MAX_TOTAL_ITEMS = 1000

export function useActivityFeed({
  limit = DEFAULT_PAGE_SIZE,
  filter,
  autoFetch = true,
}: UseActivityFeedOptions = {}) {
  const pageSize = limit
  const [feed, setFeed] = useState<ActivityFeed>({
    items: [],
    hasMore: false,
    total: 0,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch first page of activities from API (server-side skip/limit).
   */
  const fetchActivities = useCallback(
    async () => {
      setLoading(true)
      setError(null)

      try {
        const { data: events, error: apiError } = await timelineApi.events.listAll({
          skip: 0,
          limit: pageSize,
        })

        if (apiError) {
          setError('Failed to load activities')
          return
        }

        if (!events || !Array.isArray(events)) {
          setFeed({ items: [], hasMore: false, total: 0 })
          return
        }

        const activities = events
          .map(event => eventToActivity(event))
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())

        const hasMore = events.length === pageSize && events.length + 0 < MAX_TOTAL_ITEMS

        setFeed({
          items: activities,
          hasMore,
          total: activities.length,
          lastFetch: new Date(),
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    },
    [pageSize]
  )

  /**
   * Load next page and append (server-side pagination).
   */
  const fetchMore = useCallback(async () => {
    if (!feed.hasMore || loading) return
    const skip = feed.items.length
    if (skip >= MAX_TOTAL_ITEMS) return

    setLoading(true)
    setError(null)

    try {
      const { data: events, error: apiError } = await timelineApi.events.listAll({
        skip,
        limit: pageSize,
      })

      if (apiError || !events || !Array.isArray(events)) {
        setFeed(prev => ({ ...prev, hasMore: false }))
        return
      }

      const newActivities = events
        .map(event => eventToActivity(event))
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())

      const hasMore = events.length === pageSize && skip + events.length < MAX_TOTAL_ITEMS

      setFeed(prev => ({
        ...prev,
        items: [...prev.items, ...newActivities],
        hasMore,
        total: prev.total + newActivities.length,
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [feed.hasMore, feed.items.length, pageSize, loading])

  /**
   * Refresh activities from the beginning
   */
  const refresh = useCallback(async () => {
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

  const displayedFeed = useMemo(() => {
    if (!filter) return feed
    return {
      ...feed,
      items: applyActivityFilters(feed.items, filter),
    }
  }, [feed, filter])

  useEffect(() => {
    if (autoFetch) {
      fetchActivities()
    }
  }, [autoFetch, fetchActivities])

  return {
    feed: displayedFeed,
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
