import { Users, Calendar, Workflow, FileText } from 'lucide-react'
import { StatCard } from '../shared/StatCard'

interface StatsGridProps {
  totalSubjects: number
  totalEvents: number
  totalDocuments: number
  eventsToday: number
  activeWorkflows: number
  subjectsByType?: Record<string, number>
  eventsByType?: Record<string, number>
}

export function StatsGrid({
  totalSubjects,
  totalEvents,
  totalDocuments,
  eventsToday,
  activeWorkflows,
}: StatsGridProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
      {/* Hero stat: Total Events */}
      <div className="lg:col-span-2">
        <StatCard
          label="Total events"
          value={totalEvents}
          subtitle={`+${eventsToday} today`}
          icon={Calendar}
          variant="hero"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4 md:gap-6">
        <StatCard
          label="Subjects"
          value={totalSubjects}
          subtitle="In tenant"
          icon={Users}
        />
        <StatCard
          label="Documents"
          value={totalDocuments}
          subtitle="Total"
          icon={FileText}
        />
        <StatCard
          label="Active workflows"
          value={activeWorkflows}
          subtitle={activeWorkflows > 0 ? 'Running' : 'None active'}
          icon={Workflow}
        />
      </div>
    </div>
  )
}
