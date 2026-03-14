import { Users, Calendar, Activity, Wrench } from 'lucide-react'
import { StatCard } from '../shared/StatCard'

interface StatsGridProps {
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
}

export function StatsGrid({
  totalSubjects,
  totalEvents,
  eventsToday,
  activeConnectors,
  totalConnectors,
  openRepairs,
  sidebar = false,
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
        <StatCard
          label="Active connectors"
          value={activeConnectors}
          subtitle={`${totalConnectors} total`}
          icon={Activity}
          variant="compact"
        />
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

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
      <StatCard
        label="Total events"
        value={totalEvents}
        subtitle={`+${eventsToday} today`}
        icon={Calendar}
      />
      <StatCard
        label="Total subjects"
        value={totalSubjects}
        subtitle="In tenant"
        icon={Users}
      />
      <StatCard
        label="Active connectors"
        value={activeConnectors}
        subtitle={`${activeConnectors} / ${totalConnectors} running`}
        icon={Activity}
      />
      <StatCard
        label="Open repairs"
        value={openRepairs}
        subtitle={openRepairs > 0 ? 'Pending approval' : 'None'}
        icon={Wrench}
      />
    </div>
  )
}
