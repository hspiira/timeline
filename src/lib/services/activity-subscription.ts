import type { Activity, ActivityFilter } from '@/lib/types/activity'

/**
 * Activity Subscription Service
 *
 * Centralized service for managing real-time activity subscriptions
 * with support for multiple subscribers and filtering.
 */

interface Subscriber {
  id: string
  callback: (activity: Activity) => void
  filter?: ActivityFilter
}

class ActivitySubscriptionService {
  private subscribers: Map<string, Subscriber> = new Map()
  private subscriptionId = 0

  /**
   * Subscribe to activity updates
   */
  subscribe(
    callback: (activity: Activity) => void,
    filter?: ActivityFilter
  ): () => void {
    const id = `subscriber_${++this.subscriptionId}`
    this.subscribers.set(id, { id, callback, filter })

    // Return unsubscribe function
    return () => {
      this.subscribers.delete(id)
    }
  }

  /**
   * Notify all subscribers about a new activity
   */
  notifyNewActivity(activity: Activity) {
    this.notifySubscribers(activity, 'new')
  }

  /**
   * Notify subscribers about updated activity
   */
  notifyActivityUpdate(activity: Activity) {
    this.notifySubscribers(activity, 'update')
  }

  /**
   * Notify subscribers about deleted activity
   */
  notifyActivityRemoval(activityId: string) {
    this.subscribers.forEach(subscriber => {
      // Can't filter on removal, just notify
      subscriber.callback({
        id: activityId,
      } as Activity)
    })
  }

  /**
   * Internal: notify matching subscribers
   */
  private notifySubscribers(activity: Activity, _type: 'new' | 'update') {
    this.subscribers.forEach(subscriber => {
      // Check if activity matches subscriber's filter
      if (subscriber.filter && !this.matchesFilter(activity, subscriber.filter)) {
        return
      }

      try {
        subscriber.callback(activity)
      } catch (err) {
        console.error('Error in subscriber callback:', err)
      }
    })
  }

  /**
   * Check if activity matches filter
   */
  private matchesFilter(activity: Activity, filter: ActivityFilter): boolean {
    if (filter.actions?.length && !filter.actions.includes(activity.action)) {
      return false
    }

    if (
      filter.resourceTypes?.length &&
      !filter.resourceTypes.includes(activity.resourceType)
    ) {
      return false
    }

    if (filter.priority?.length && !filter.priority.includes(activity.priority)) {
      return false
    }

    if (filter.userId && activity.userId !== filter.userId) {
      return false
    }

    if (filter.dateRange) {
      if (
        activity.timestamp < filter.dateRange.from ||
        activity.timestamp > filter.dateRange.to
      ) {
        return false
      }
    }

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
  }

  /**
   * Get subscriber count
   */
  getSubscriberCount(): number {
    return this.subscribers.size
  }

  /**
   * Clear all subscribers
   */
  clear() {
    this.subscribers.clear()
  }
}

/**
 * Singleton instance
 */
export const activitySubscriptionService = new ActivitySubscriptionService()

/**
 * React hook for activity subscriptions
 */
export function useActivitySubscriptions(
  callback: (activity: Activity) => void,
  filter?: ActivityFilter
) {
  // Subscribe on mount
  const unsubscribe = activitySubscriptionService.subscribe(callback, filter)

  // Unsubscribe on unmount
  return unsubscribe
}
