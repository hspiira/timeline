import { Activity, Calendar, Users, Wrench } from 'lucide-react'
import { cn } from '@/lib/utils'
import { StatCard } from '../shared/StatCard'

export interface StatsGridProps {
  totalSubjects: number
  totalEvents: number
  eventsToday: number
  activeConnectors: number
  totalConnectors: number
  openRepairs: number
  subjectsByType?: Record<string, number>
  eventsByType?: Record<string, number>
  /** When true, only render the three supporting stats in a vertical column (hero is shown elsewhere) */
  sidebar?: boolean
  /** When false, hide the Active connectors stat (e.g. when user has no connector access) */
  showConnectorStat?: boolean
}

export function StatsGrid({
  totalSubjects,
  totalEvents,
  eventsToday,
  activeConnectors,
  totalConnectors,
  openRepairs,
  sidebar = false,
  showConnectorStat = true,
}: StatsGridProps) {
  if (sidebar) {
    return (
      <div className="space-y-3">
        <StatCard
          label="Subjects"
          value={totalSubjects}
          subtitle="In tenant"
          icon={Users}
          variant="compact"
        />
        {showConnectorStat && (
          <StatCard
            label="Active connectors"
            value={activeConnectors}
            subtitle={`${totalConnectors} total`}
            icon={Activity}
            variant="compact"
          />
        )}
        <StatCard
          label="Open repairs"
          value={openRepairs}
          subtitle={openRepairs > 0 ? 'Pending approval' : 'None'}
          icon={Wrench}
          variant="compact"
        />
      </div>
    )
  }

  const connectorCard = showConnectorStat ? (
    <StatCard
      label="Active connectors"
      value={activeConnectors}
      subtitle={`${activeConnectors} / ${totalConnectors} running`}
      icon={Activity}
    />
  ) : null

  return (
    <div
      className={cn(
        'grid gap-4 md:gap-6',
        showConnectorStat ? 'grid-cols-2 lg:grid-cols-4' : 'grid-cols-2 lg:grid-cols-3',
      )}
    >
      <StatCard
        label="Total events"
        value={totalEvents}
        subtitle={`+${eventsToday} today`}
        icon={Calendar}
      />
      <StatCard label="Total subjects" value={totalSubjects} subtitle="In tenant" icon={Users} />
      {connectorCard}
      <StatCard
        label="Open repairs"
        value={openRepairs}
        subtitle={openRepairs > 0 ? 'Pending approval' : 'None'}
        icon={Wrench}
      />
    </div>
  )
}
