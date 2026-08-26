import { useCallback, useRef } from 'react'
import { useToast } from '@/hooks/useToast'
import type { Activity } from '@/lib/types/activity'

interface NotificationPreferences {
  enableNotifications?: boolean
  showForActions?: string[]
  showForResourceTypes?: string[]
  groupByResourceType?: boolean
  autoCloseDuration?: number // milliseconds, 0 = never auto-close
}

/**
 * Hook for managing activity notifications
 *
 * Usage:
 * ```tsx
 * const { notifyNewActivity, notifyActivityUpdate, clearNotifications } = useActivityNotifications({
 *   enableNotifications: true,
 *   showForActions: ['created'],
 *   groupByResourceType: true,
 * })
 *
 * // In real-time handler:
 * notifyNewActivity(activity)
 * ```
 */
export function useActivityNotifications(preferences: NotificationPreferences = {}) {
  const {
    enableNotifications = true,
    showForActions = ['created', 'verified'],
    showForResourceTypes = [],
    groupByResourceType: _groupByResourceType = false,
    autoCloseDuration = 5000,
  } = preferences

  const toast = useToast()
  const notificationCountRef = useRef<number>(0)

  const shouldNotify = useCallback(
    (activity: Activity): boolean => {
      if (!enableNotifications) return false

      // Check action filter
      if (showForActions.length > 0 && !showForActions.includes(activity.action)) {
        return false
      }

      // Check resource type filter
      if (
        showForResourceTypes.length > 0 &&
        !showForResourceTypes.includes(activity.resourceType)
      ) {
        return false
      }

      return true
    },
    [enableNotifications, showForActions, showForResourceTypes],
  )

  const getActionEmoji = useCallback((action: string): string => {
    const emojiMap: Record<string, string> = {
      created: '✨',
      updated: '🔄',
      deleted: '🗑️',
      verified: '✅',
      viewed: '👁️',
      documented: '📝',
      assigned: '👤',
    }
    return emojiMap[action] || '📝'
  }, [])

  const notifyNewActivity = useCallback(
    (activity: Activity) => {
      if (!shouldNotify(activity)) return

      notificationCountRef.current += 1

      const actionEmoji = getActionEmoji(activity.action)
      const title = `${actionEmoji} ${activity.action.charAt(0).toUpperCase() + activity.action.slice(1)}`
      const description = `${activity.resourceType}: ${activity.resourceName.substring(0, 30)}${activity.resourceName.length > 30 ? '...' : ''}`

      toast.info(title, description)
    },
    [shouldNotify, getActionEmoji, toast, autoCloseDuration],
  )

  const notifyActivityUpdate = useCallback(
    (activity: Activity) => {
      if (!enableNotifications) return

      const actionEmoji = getActionEmoji(activity.action)
      const title = `${actionEmoji} Updated`
      const description = `${activity.resourceType}: ${activity.resourceName.substring(0, 30)}${activity.resourceName.length > 30 ? '...' : ''}`

      toast.info(title, description)
    },
    [enableNotifications, getActionEmoji, toast],
  )

  const clearNotifications = useCallback(() => {
    notificationCountRef.current = 0
  }, [])

  const getNotificationCount = useCallback(() => notificationCountRef.current, [])

  return {
    notifyNewActivity,
    notifyActivityUpdate,
    clearNotifications,
    getNotificationCount,
    shouldNotify,
  }
}

export default useActivityNotifications
