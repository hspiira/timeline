/**
 * Activity Feed - Expert-level architecture for recent activity
 * Separates concerns: Activity records are independent of Events
 */

import { formatEventDateTime } from '@/lib/format-date'

export type ActivityAction =
  | 'created'
  | 'updated'
  | 'deleted'
  | 'viewed'
  | 'documented'
  | 'verified'
  | 'assigned'

export type ActivityResourceType =
  | 'event'
  | 'subject'
  | 'document'
  | 'workflow'
  | 'permission'
  | 'role'

export type ActivityPriority = 'low' | 'medium' | 'high'

export interface Activity {
  id: string
  userId: string
  action: ActivityAction
  resourceType: ActivityResourceType
  resourceId: string
  resourceName: string
  timestamp: Date
  metadata?: Record<string, unknown>
  icon?: string
  priority: ActivityPriority
  description?: string
}

export interface ActivityFeed {
  items: Activity[]
  hasMore: boolean
  cursor?: string
  total: number
  lastFetch?: Date
}

export interface ActivityFilter {
  actions?: ActivityAction[]
  resourceTypes?: ActivityResourceType[]
  dateRange?: { from: Date; to: Date }
  userId?: string
  priority?: ActivityPriority[]
  search?: string
}

/**
 * Activity Action Metadata - configuration for each action type
 */
export const ACTIVITY_CONFIG: Record<
  ActivityAction,
  {
    label: string
    icon: string
    color: string
    priority: ActivityPriority
  }
> = {
  created: {
    label: 'Created',
    icon: 'Plus',
    color: 'bg-green-100 dark:bg-green-950/30 text-green-700 dark:text-green-300',
    priority: 'medium',
  },
  updated: {
    label: 'Updated',
    icon: 'Edit',
    color: 'bg-blue-100 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300',
    priority: 'low',
  },
  deleted: {
    label: 'Deleted',
    icon: 'Trash2',
    color: 'bg-red-100 dark:bg-red-950/30 text-red-700 dark:text-red-300',
    priority: 'high',
  },
  viewed: {
    label: 'Viewed',
    icon: 'Eye',
    color: 'bg-slate-100 dark:bg-slate-900/30 text-slate-700 dark:text-slate-300',
    priority: 'low',
  },
  documented: {
    label: 'Documented',
    icon: 'FileText',
    color: 'bg-amber-100 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300',
    priority: 'medium',
  },
  verified: {
    label: 'Verified',
    icon: 'CheckCircle',
    color: 'bg-green-100 dark:bg-green-950/30 text-green-700 dark:text-green-300',
    priority: 'high',
  },
  assigned: {
    label: 'Assigned',
    icon: 'User',
    color: 'bg-purple-100 dark:bg-purple-950/30 text-purple-700 dark:text-purple-300',
    priority: 'medium',
  },
}

/**
 * Resource Type Icons - icon mapping for each resource type
 */
export const RESOURCE_ICONS: Record<ActivityResourceType, string> = {
  event: 'Calendar',
  subject: 'User',
  document: 'FileText',
  workflow: 'Workflow',
  permission: 'Shield',
  role: 'Badge',
}

/**
 * Convert Event to Activity (works with EventListResponse or RecentEventItem)
 */
export function eventToActivity(event: {
  id: string
  subject_id: string
  event_type: string
  event_time: string
  payload?: Record<string, unknown>
}): Activity {
  return {
    id: event.id,
    userId: event.subject_id,
    action: 'created',
    resourceType: 'event',
    resourceId: event.id,
    resourceName: event.event_type,
    timestamp: new Date(event.event_time),
    metadata: { ...event.payload, subject_id: event.subject_id },
    priority: 'low',
    description: `${event.event_type} event created for ${event.subject_id.slice(0, 8)}`,
  }
}

/**
 * Format activity timestamp for display
 */
export function formatActivityTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return formatEventDateTime(date)
}
