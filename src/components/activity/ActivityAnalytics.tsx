import { useActivityAnalytics } from '@/hooks/useActivityAnalytics'
import type { Activity } from '@/lib/types/activity'
import { BarChart3, TrendingUp, Users, Zap } from 'lucide-react'
import { StatCard } from '@/components/shared/StatCard'

// User ID prefix length (e.g., "user_" = 5 characters)
const USER_ID_PREFIX_LENGTH = 5

interface ActivityAnalyticsProps {
  activities: Activity[]
  compact?: boolean
}

/**
 * Analytics dashboard for activity feed
 * Displays key statistics and trending insights
 */
export function ActivityAnalytics({ activities, compact = false }: ActivityAnalyticsProps) {
  const { stats, trends } = useActivityAnalytics(activities)

  if (compact) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard
          variant="compact"
          icon={BarChart3}
          label="Total Activities"
          value={stats.total.toString()}
          color="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          variant="compact"
          icon={Zap}
          label="Last Hour"
          value={trends.averagePerHour.toString()}
          color="text-amber-600 dark:text-amber-400"
        />
        <StatCard
          variant="compact"
          icon={TrendingUp}
          label="Most Common"
          value={trends.mostCommonAction?.action || 'N/A'}
          color="text-green-600 dark:text-green-400"
        />
        <StatCard
          variant="compact"
          icon={Users}
          label="Top User"
          value={trends.mostActiveUser?.userId.substring(USER_ID_PREFIX_LENGTH) || 'N/A'}
          color="text-purple-600 dark:text-purple-400"
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard
          variant="compact"
          icon={BarChart3}
          label="Total Activities"
          value={stats.total.toString()}
          color="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          variant="compact"
          icon={Zap}
          label="Activities Last Hour"
          value={trends.averagePerHour.toString()}
          color="text-amber-600 dark:text-amber-400"
        />
        <StatCard
          variant="compact"
          icon={TrendingUp}
          label="Most Common Action"
          value={trends.mostCommonAction?.action || 'N/A'}
          subtext={trends.mostCommonAction ? `${trends.mostCommonAction.count} times` : ''}
          color="text-green-600 dark:text-green-400"
        />
        <StatCard
          variant="compact"
          icon={Users}
          label="Top Active User"
          value={trends.mostActiveUser?.userId.substring(USER_ID_PREFIX_LENGTH) || 'N/A'}
          subtext={trends.mostActiveUser ? `${trends.mostActiveUser.count} activities` : ''}
          color="text-purple-600 dark:text-purple-400"
        />
      </div>

      {/* Action breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-card/50 rounded-none border border-border/50 p-4">
          <h4 className="text-sm font-semibold text-foreground mb-3">Activities by Action</h4>
          <div className="space-y-2">
            {(() => {
              const actionValues = Object.values(stats.byAction)
              const maxActionCount = actionValues.length > 0 ? Math.max(...actionValues) : 1
              return Object.entries(stats.byAction)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 5)
                .map(([action, count]) => (
                  <div key={action} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground capitalize">{action}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-muted rounded-none overflow-hidden">
                        <div
                          className="h-full bg-blue-500"
                          style={{
                            width: `${(count / maxActionCount) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="w-8 text-right font-medium text-foreground">{count}</span>
                    </div>
                  </div>
                ))
            })()}
          </div>
        </div>

        {/* Resource type breakdown */}
        <div className="bg-card/50 rounded-none border border-border/50 p-4">
          <h4 className="text-sm font-semibold text-foreground mb-3">Activities by Resource</h4>
          <div className="space-y-2">
            {(() => {
              const resourceValues = Object.values(stats.byResourceType)
              const maxResourceCount = resourceValues.length > 0 ? Math.max(...resourceValues) : 1
              return Object.entries(stats.byResourceType)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 5)
                .map(([resourceType, count]) => (
                  <div key={resourceType} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground capitalize">{resourceType}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-muted rounded-none overflow-hidden">
                        <div
                          className="h-full bg-purple-500"
                          style={{
                            width: `${(count / maxResourceCount) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="w-8 text-right font-medium text-foreground">{count}</span>
                    </div>
                  </div>
                ))
            })()}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ActivityAnalytics
