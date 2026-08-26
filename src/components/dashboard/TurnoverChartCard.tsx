import { format, subDays } from 'date-fns'
import { useId, useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

/** Distinct colors: blue for events, amber for subjects (theme-aware for dark mode) */
const chartConfig = {
  date: { label: 'Date' },
  events: {
    label: 'Events',
    theme: {
      light: 'oklch(0.50 0.18 250)',
      dark: 'oklch(0.65 0.16 250)',
    },
  },
  subjects: {
    label: 'Subjects (active)',
    theme: {
      light: 'oklch(0.60 0.18 75)',
      dark: 'oklch(0.75 0.16 75)',
    },
  },
} satisfies ChartConfig

/** Minimal event shape for building daily series */
interface RecentEventForChart {
  event_time: string
  subject_id: string
}

/** Build daily series: events count and unique subjects (active) per day from recent_events */
function buildChartDataFromRecent(
  days: number,
  recentEvents: RecentEventForChart[],
): { date: string; events: number; subjects: number }[] {
  const now = new Date()
  const byDate = new Map<string, { events: number; subjectIds: Set<string> }>()

  for (let i = days - 1; i >= 0; i--) {
    const d = subDays(now, i)
    const dateStr = format(d, 'yyyy-MM-dd')
    byDate.set(dateStr, { events: 0, subjectIds: new Set() })
  }

  for (const e of recentEvents) {
    const dateStr = format(new Date(e.event_time), 'yyyy-MM-dd')
    const entry = byDate.get(dateStr)
    if (entry) {
      entry.events += 1
      entry.subjectIds.add(e.subject_id)
    }
  }

  return Array.from(byDate.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, { events, subjectIds }]) => ({
      date,
      events,
      subjects: subjectIds.size,
    }))
}

interface TurnoverChartCardProps {
  totalSubjects?: number
  totalEvents?: number
  /** Recent events used to build daily events/subjects series */
  recentEvents?: { event_time: string; subject_id: string }[] | null
  loading?: boolean
}

export function TurnoverChartCard({
  totalSubjects = 0,
  totalEvents = 0,
  recentEvents = [],
  loading = false,
}: TurnoverChartCardProps) {
  const gradientPrefix = useId().replace(/:/g, '')
  const fillEventsId = `${gradientPrefix}-events`
  const fillSubjectsId = `${gradientPrefix}-subjects`
  const [timeRange, setTimeRange] = useState('7d')
  const days = timeRange === '30d' ? 30 : timeRange === '14d' ? 14 : 7

  const chartData = useMemo(
    () => buildChartDataFromRecent(days, recentEvents ?? []),
    [days, recentEvents],
  )

  const periodEvents = useMemo(() => chartData.reduce((s, d) => s + d.events, 0), [chartData])
  const periodSubjects = useMemo(() => {
    const ids = new Set<string>()
    for (const e of recentEvents ?? []) {
      ids.add(e.subject_id)
    }
    return ids.size
  }, [recentEvents])

  return (
    <DashboardCard title="Activity trend">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="w-[130px] rounded-none border border-border/60 bg-muted/30 text-xs h-8 px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            aria-label="Time range"
          >
            <option value="7d">Last 7 days</option>
            <option value="14d">Last 14 days</option>
            <option value="30d">Last 30 days</option>
          </select>
          <select
            className="text-xs border border-border/60 bg-muted/30 px-2 py-1.5 text-foreground rounded-none h-8"
            aria-label="Group by"
          >
            <option>By date</option>
          </select>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-3 border border-border/40 rounded-none">
                <Skeleton className="h-3 w-16 mb-2" />
                <Skeleton className="h-7 w-12" />
              </div>
            ))
          ) : (
            <>
              <MetricBox label="Total subjects" value={totalSubjects} />
              <MetricBox label="Total events" value={totalEvents} />
              <MetricBox label="Events in period" value={periodEvents} />
              <MetricBox label="Subjects active" value={periodSubjects} />
            </>
          )}
        </div>
        <div className="h-[220px] w-full border-t border-border/40 pt-4">
          {loading ? (
            <Skeleton className="h-full w-full rounded-none" />
          ) : (
            <ChartContainer config={chartConfig} className="h-full w-full">
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id={fillEventsId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-events)" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="var(--color-events)" stopOpacity={0.1} />
                  </linearGradient>
                  <linearGradient id={fillSubjectsId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-subjects)" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="var(--color-subjects)" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  vertical={false}
                  strokeDasharray="3 3"
                  className="stroke-border/50"
                />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  minTickGap={24}
                  tickFormatter={(value) => format(new Date(value), 'MM/dd')}
                />
                <YAxis hide />
                <ChartTooltip
                  cursor={false}
                  content={
                    <ChartTooltipContent
                      labelFormatter={(value) => format(new Date(value), 'MMM d, yyyy')}
                      indicator="dot"
                    />
                  }
                />
                <Area
                  dataKey="subjects"
                  type="natural"
                  fill={`url(#${fillSubjectsId})`}
                  stroke="var(--color-subjects)"
                  strokeWidth={1.5}
                />
                <Area
                  dataKey="events"
                  type="natural"
                  fill={`url(#${fillEventsId})`}
                  stroke="var(--color-events)"
                  strokeWidth={1.5}
                />
                <ChartLegend content={<ChartLegendContent />} />
              </AreaChart>
            </ChartContainer>
          )}
        </div>
      </div>
    </DashboardCard>
  )
}

function MetricBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-3 border border-border/40 rounded-none">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="font-display text-lg font-bold text-foreground tabular-nums">
        {value.toLocaleString()}
      </p>
    </div>
  )
}
