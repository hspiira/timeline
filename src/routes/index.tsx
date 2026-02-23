import { createFileRoute } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { useStore } from '@tanstack/react-store'
import { authStore } from '@/lib/auth-store'
import { LandingPage } from '@/components/landing/LandingPage'
import { WeekDataCard } from '@/components/dashboard/WeekDataCard'
import { TodayTodosCard } from '@/components/dashboard/TodayTodosCard'
import { HelpCenterCard } from '@/components/dashboard/HelpCenterCard'
import { CommonAppsCard } from '@/components/dashboard/CommonAppsCard'
import { EmployeeDataCard } from '@/components/dashboard/EmployeeDataCard'
import { UrgentTasksCard } from '@/components/dashboard/UrgentTasksCard'
import { AnnouncementsCard } from '@/components/dashboard/AnnouncementsCard'
import { TurnoverChartCard } from '@/components/dashboard/TurnoverChartCard'
import { LatestTurnoverCard } from '@/components/dashboard/LatestTurnoverCard'
import { MinimalActivityFeed } from '@/components/dashboard/MinimalActivityFeed'
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorDisplay } from '@/lib/api-utils'
import type { components } from '@/lib/timeline-api'
import type { WorkflowResponse } from '@/lib/types'

type DashboardStatsResponse = components['schemas']['DashboardStatsResponse']

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    requireAuthBeforeLoad('/')
  },
  component: HomePage,
})

interface DashboardData {
  stats: DashboardStatsResponse | null
  workflows: WorkflowResponse[]
}

interface FetchError {
  field: 'analytics' | 'workflows'
  message: string
}

function HomePage() {
  const authState = useStore(authStore)

  const [data, setData] = useState<DashboardData>({
    stats: null,
    workflows: [],
  })
  const [_loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<FetchError[]>([])

  const eventsToday = useMemo(() => {
    const recent = data.stats?.recent_events ?? []
    const today = new Date().toDateString()
    return recent.filter((e) => new Date(e.event_time).toDateString() === today).length
  }, [data.stats?.recent_events])

  const activeWorkflowsCount = useMemo(() => {
    return data.workflows.filter((w) => (w as { is_active?: boolean }).is_active).length
  }, [data.workflows])

  const fetchDashboard = useCallback(async () => {
    setLoading(true)
    setErrors([])
    try {
      const [analyticsResult, workflowsResult] = await Promise.allSettled([
        timelineApi.analytics.dashboard(),
        timelineApi.workflows.list({ skip: 0, limit: 100 }),
      ])

      const newErrors: FetchError[] = []
      const newData: DashboardData = {
        stats: null,
        workflows: [],
      }

      if (analyticsResult.status === 'fulfilled' && analyticsResult.value.data) {
        newData.stats = analyticsResult.value.data
      } else if (analyticsResult.status === 'fulfilled' && analyticsResult.value.error) {
        const val = analyticsResult.value as { error: unknown; response?: { status?: number } }
        const status = val.response?.status
        const display = getApiErrorDisplay(
          { error: val.error, status },
          status === 403 ? 'Access denied to dashboard' : 'Failed to load dashboard stats'
        )
        newErrors.push({ field: 'analytics', message: display.message })
      } else if (analyticsResult.status === 'rejected') {
        newErrors.push({ field: 'analytics', message: 'Failed to load dashboard stats' })
      }

      if (workflowsResult.status === 'fulfilled' && workflowsResult.value.data) {
        newData.workflows = workflowsResult.value.data
      } else if (workflowsResult.status === 'rejected') {
        newErrors.push({ field: 'workflows', message: 'Failed to load workflows' })
      }

      setData(newData)
      setErrors(newErrors)
    } catch (err) {
      console.error('Unexpected error fetching dashboard:', err)
      setErrors([{ field: 'analytics', message: 'An unexpected error occurred while loading dashboard' }])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (authState.user) {
      fetchDashboard()
      let interval: NodeJS.Timeout | null = null
      const POLL_INTERVAL = 30000

      const startPolling = () => {
        if (!document.hidden) {
          interval = setInterval(() => {
            if (!document.hidden) fetchDashboard()
          }, POLL_INTERVAL)
        }
      }

      const handleVisibilityChange = () => {
        if (document.hidden && interval) {
          clearInterval(interval)
          interval = null
        } else {
          startPolling()
        }
      }

      startPolling()
      document.addEventListener('visibilitychange', handleVisibilityChange)
      return () => {
        if (interval) clearInterval(interval)
        document.removeEventListener('visibilitychange', handleVisibilityChange)
      }
    }
  }, [authState.user, fetchDashboard])

  if (authState.isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    )
  }

  if (!authState.user) {
    return <LandingPage />
  }

  const hasErrors = errors.length > 0
  const username = authState.user.username ?? 'there'
  const totalEvents = data.stats?.total_events ?? 0

  const greeting = useMemo(() => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 18) return 'Good afternoon'
    return 'Good evening'
  }, [])

  const todayEvents = useMemo(() => {
    const recent = data.stats?.recent_events ?? []
    const today = new Date().toDateString()
    return recent
      .filter((e) => new Date(e.event_time).toDateString() === today)
      .map((e) => ({ id: e.id, event_time: e.event_time, event_type: e.event_type, subject_id: e.subject_id }))
  }, [data.stats?.recent_events])

  const loading = data.stats === null && errors.length === 0

  return (
    <div className="dashboard-page min-h-[calc(100vh-4rem)]">
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.02] dark:opacity-[0.04]"
        style={{
          backgroundImage: `
            linear-gradient(to right, currentColor 1px, transparent 1px),
            linear-gradient(to bottom, currentColor 1px, transparent 1px)
          `,
          backgroundSize: '8px 8px',
        }}
        aria-hidden
      />

      {/* Gaps are layout-only; card content grows inside each card when data is added */}
      <div className="relative flex flex-col gap-4 md:gap-6">
        <header
          className="border-b border-border/60 bg-muted/20 animate-in fade-in slide-in-from-bottom-2 duration-500"
          style={{ borderLeftWidth: '4px', borderLeftColor: 'var(--dashboard-accent)' }}
        >
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 py-5">
            <div>
              <h1 className="font-display text-xl sm:text-2xl font-bold text-foreground tracking-tight">
                {greeting}, {username}
              </h1>
              <p className="mt-0.5 text-sm text-muted-foreground">Here’s your timeline at a glance.</p>
            </div>
            <div className="flex items-baseline gap-2 flex-shrink-0">
              <span className="font-display text-3xl sm:text-4xl font-bold text-foreground tabular-nums">
                {totalEvents.toLocaleString()}
              </span>
              <span className="text-sm text-muted-foreground whitespace-nowrap">events</span>
            </div>
          </div>
        </header>

        {hasErrors && (
          <div
            className="p-4 border rounded-none border-destructive/30 bg-destructive/5 animate-in fade-in slide-in-from-bottom-2 duration-300"
            role="alert"
          >
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-foreground text-sm mb-1">Some data couldn’t be loaded</h3>
                <ul className="space-y-0.5 text-xs text-muted-foreground mb-3">
                  {errors.map((error) => (
                    <li key={error.field}>
                      {error.field.charAt(0).toUpperCase() + error.field.slice(1)}: {error.message}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={fetchDashboard}
                  className="inline-flex items-center gap-2 text-xs font-medium text-foreground hover:text-primary transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Top row: This week's data | Today's to-dos | Help center */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <WeekDataCard
            totalEvents={totalEvents}
            eventsByType={data.stats?.events_by_type}
            eventsToday={eventsToday}
            comparison={null}
            loading={loading}
          />
          <TodayTodosCard todayEvents={todayEvents} loading={loading} />
          <HelpCenterCard />
        </div>

        {/* Middle row: Common apps | Employee (subjects) data | Urgent | Announcements */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 md:gap-5">
          <div className="md:col-span-4 space-y-6">
            <CommonAppsCard />
            <EmployeeDataCard
              totalSubjects={data.stats?.total_subjects ?? 0}
              subjectsByType={data.stats?.subjects_by_type}
              onRefresh={fetchDashboard}
              loading={loading}
            />
          </div>
          <div className="md:col-span-4">
            <UrgentTasksCard count={0} onRefresh={fetchDashboard} loading={loading} />
          </div>
          <div className="md:col-span-4">
            <AnnouncementsCard />
          </div>
        </div>

        {/* Bottom row: Activity trend (large chart) | Latest changes + Recent activity */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-5">
          <div className="lg:col-span-7">
            <TurnoverChartCard
              startCount={0}
              endCount={totalEvents}
              added={eventsToday}
              removed={0}
              loading={loading}
            />
          </div>
          <div className="lg:col-span-5 space-y-6">
            <LatestTurnoverCard />
            <div>
              <h2 className="font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Recent activity
              </h2>
              <div className="rounded-none border border-border/60 bg-card/80 backdrop-blur-sm overflow-hidden">
                <MinimalActivityFeed limit={8} recentEvents={data.stats?.recent_events} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
