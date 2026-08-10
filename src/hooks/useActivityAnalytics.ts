import { useMemo } from 'react'
import type { Activity } from '@/lib/types/activity'

interface ActivityStats {
  total: number
  byAction: Record<string, number>
  byResourceType: Record<string, number>
  byPriority: Record<string, number>
  byUser: Record<string, number>
}

interface ActivityTrends {
  mostCommonAction: { action: string; count: number } | null
  mostCommonResourceType: { resourceType: string; count: number } | null
  mostActiveUser: { userId: string; count: number } | null
  averagePerHour: number
}

/**
 * Hook for analyzing activity data and computing trends
 *
 * Usage:
 * ```tsx
 * const { stats, trends } = useActivityAnalytics(feed.items)
 *
 * <div>
 *   <p>Total activities: {stats.total}</p>
 *   <p>Most common action: {trends.mostCommonAction?.action}</p>
 * </div>
 * ```
 */
export function useActivityAnalytics(activities: Activity[]) {
  const stats = useMemo<ActivityStats>(() => {
    const result: ActivityStats = {
      total: activities.length,
      byAction: {},
      byResourceType: {},
      byPriority: {},
      byUser: {},
    }

    activities.forEach(activity => {
      // Count by action
      result.byAction[activity.action] = (result.byAction[activity.action] || 0) + 1

      // Count by resource type
      result.byResourceType[activity.resourceType] =
        (result.byResourceType[activity.resourceType] || 0) + 1

      // Count by priority
      result.byPriority[activity.priority] = (result.byPriority[activity.priority] || 0) + 1

      // Count by user
      result.byUser[activity.userId] = (result.byUser[activity.userId] || 0) + 1
    })

    return result
  }, [activities])

  const trends = useMemo<ActivityTrends>(() => {
    const mostCommonAction = Object.entries(stats.byAction).reduce(
      (prev, [action, count]) => (!prev || count > prev.count ? { action, count } : prev),
      null as { action: string; count: number } | null
    )

    const mostCommonResourceType = Object.entries(stats.byResourceType).reduce(
      (prev, [resourceType, count]) =>
        !prev || count > prev.count ? { resourceType, count } : prev,
      null as { resourceType: string; count: number } | null
    )

    const mostActiveUser = Object.entries(stats.byUser).reduce(
      (prev, [userId, count]) => (!prev || count > prev.count ? { userId, count } : prev),
      null as { userId: string; count: number } | null
    )

    // Calculate average activities per hour
    const now = new Date()
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000)
    const activitiesLastHour = activities.filter(
      a => a.timestamp >= oneHourAgo && a.timestamp <= now
    ).length
    const averagePerHour = activitiesLastHour

    return {
      mostCommonAction,
      mostCommonResourceType,
      mostActiveUser,
      averagePerHour,
    }
  }, [stats, activities])

  return { stats, trends }
}

export default useActivityAnalytics
