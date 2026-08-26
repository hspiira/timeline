import { Badge, Calendar, FileText, type LucideIcon, Shield, User, Workflow } from 'lucide-react'
import type { Activity } from '@/lib/types/activity'
import { ACTIVITY_CONFIG, formatActivityTime } from '@/lib/types/activity'

interface ActivityRendererProps {
  activity: Activity
  isSelected?: boolean
  onSelect?: (id: string) => void
  onExpand?: (id: string) => void
}

/**
 * Renderer configuration for each resource type
 * Maps resource type to its icon and color styling
 */
const RENDERER_CONFIG: Record<Activity['resourceType'], { icon: LucideIcon; color: string }> = {
  event: { icon: Calendar, color: 'text-blue-600 dark:text-blue-400' },
  subject: { icon: User, color: 'text-purple-600 dark:text-purple-400' },
  document: { icon: FileText, color: 'text-amber-600 dark:text-amber-400' },
  workflow: { icon: Workflow, color: 'text-cyan-600 dark:text-cyan-400' },
  permission: { icon: Shield, color: 'text-green-600 dark:text-green-400' },
  role: { icon: Badge, color: 'text-blue-600 dark:text-blue-400' },
}

/**
 * Generic Resource Activity Renderer - Renders any resource type activity
 * Replaces all specific renderers (Event, Subject, Document, etc.) with a single reusable component
 */
function ResourceActivityRenderer({
  activity,
  isSelected,
  onSelect,
  onExpand,
}: ActivityRendererProps) {
  const config = ACTIVITY_CONFIG[activity.action]
  const resourceConfig = RENDERER_CONFIG[activity.resourceType]
  const Icon = resourceConfig?.icon

  return (
    <ActivityCardContainer
      activity={activity}
      config={config}
      isSelected={isSelected}
      onSelect={onSelect}
      onExpand={onExpand}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          {Icon && <Icon className={`w-3.5 h-3.5 ${resourceConfig.color}`} />}
          <span className="font-medium text-sm text-foreground">{activity.resourceName}</span>
          <span className="text-xs text-muted-foreground font-mono">
            {activity.resourceId.slice(0, 8)}
          </span>
        </div>
        {activity.description && (
          <p className="text-xs text-muted-foreground">{activity.description}</p>
        )}
      </div>
    </ActivityCardContainer>
  )
}

/**
 * Specific renderer exports for backward compatibility
 * All use the same generic ResourceActivityRenderer internally
 */
export const EventActivityRenderer = ResourceActivityRenderer
export const SubjectActivityRenderer = ResourceActivityRenderer
export const DocumentActivityRenderer = ResourceActivityRenderer
export const WorkflowActivityRenderer = ResourceActivityRenderer
export const PermissionActivityRenderer = ResourceActivityRenderer
export const RoleActivityRenderer = ResourceActivityRenderer

/**
 * Activity Renderers Registry - Strategy pattern
 * All resource types now use the same generic ResourceActivityRenderer
 */
export const ActivityRenderers: Record<
  Activity['resourceType'],
  React.ComponentType<ActivityRendererProps>
> = {
  event: ResourceActivityRenderer,
  subject: ResourceActivityRenderer,
  document: ResourceActivityRenderer,
  workflow: ResourceActivityRenderer,
  permission: ResourceActivityRenderer,
  role: ResourceActivityRenderer,
}

/**
 * Generic Activity Renderer - Dispatches to specific renderer based on resource type
 */
export function ActivityRenderer(props: ActivityRendererProps) {
  const Renderer = ActivityRenderers[props.activity.resourceType]
  if (!Renderer) {
    return <DefaultActivityRenderer {...props} />
  }
  return <Renderer {...props} />
}

/**
 * Default Activity Renderer - Fallback for unknown resource types
 */
function DefaultActivityRenderer({
  activity,
  isSelected,
  onSelect,
  onExpand,
}: ActivityRendererProps) {
  const config = ACTIVITY_CONFIG[activity.action]

  return (
    <ActivityCardContainer
      activity={activity}
      config={config}
      isSelected={isSelected}
      onSelect={onSelect}
      onExpand={onExpand}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-sm text-foreground">{activity.resourceName}</span>
          <span className="text-xs text-muted-foreground font-mono">
            {activity.resourceId.slice(0, 8)}
          </span>
        </div>
        {activity.description && (
          <p className="text-xs text-muted-foreground">{activity.description}</p>
        )}
      </div>
    </ActivityCardContainer>
  )
}

/**
 * Reusable Activity Card Container
 */
function ActivityCardContainer({
  activity,
  config,
  isSelected,
  onSelect,
  children,
}: ActivityRendererProps & {
  config: (typeof ACTIVITY_CONFIG)[keyof typeof ACTIVITY_CONFIG]
  children: React.ReactNode
}) {
  return (
    <div
      onClick={() => onSelect?.(activity.id)}
      className={`p-3 rounded-none border transition-colors cursor-pointer ${
        isSelected
          ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/20'
          : 'border-border hover:border-blue-300 dark:hover:border-blue-700 hover:bg-muted/30'
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Priority indicator */}
        <div
          className={`w-1 h-1 rounded-none mt-2 shrink-0 ${
            activity.priority === 'high'
              ? 'bg-red-500'
              : activity.priority === 'medium'
                ? 'bg-amber-500'
                : 'bg-slate-400'
          }`}
        />

        {/* Main content */}
        <div className="flex-1 min-w-0">{children}</div>

        {/* Action badge and time */}
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-xs px-2 py-1 rounded-none font-medium ${config.color}`}>
            {config.label}
          </span>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {formatActivityTime(activity.timestamp)}
          </span>
        </div>
      </div>

      {/* Metadata */}
      {activity.metadata && Object.keys(activity.metadata).length > 0 && (
        <div className="mt-2 ml-4 text-xs text-muted-foreground space-y-1">
          {Object.entries(activity.metadata)
            .slice(0, 3)
            .map(([key, value]) => (
              <div key={key}>
                <strong>{key}:</strong> {String(value)}
              </div>
            ))}
        </div>
      )}
    </div>
  )
}
