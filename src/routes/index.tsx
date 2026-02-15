import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { MinimalActivityFeed } from '@/components/dashboard/MinimalActivityFeed'
import { StatsGrid } from '@/components/dashboard/StatsGrid'
import { timelineApi } from '@/lib/api-client'
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import type { components } from '@/lib/timeline-api'
import type { WorkflowResponse } from '@/lib/types'

type DashboardStatsResponse = components['schemas']['DashboardStatsResponse']

export const Route = createFileRoute('/')({
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
  const authState = useRequireAuth()

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
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    )
  }

  if (!authState.user) {
    return null
  }

  const hasErrors = errors.length > 0
  const username = authState.user.username ?? 'there'

  return (
    <div className="dashboard-page">
      {/* Subtle grid background */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.02] dark:opacity-[0.04]"
        style={{
          backgroundImage: `
            linear-gradient(to right, currentColor 1px, transparent 1px),
            linear-gradient(to bottom, currentColor 1px, transparent 1px)
          `,
          backgroundSize: '64px 64px',
        }}
        aria-hidden
      />

      <div className="relative">
        {/* Welcome strip */}
        <header className="mb-8 md:mb-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <h1 className="font-display text-2xl md:text-3xl font-bold text-foreground tracking-tight">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Welcome back, {username}. Here’s your timeline at a glance.
          </p>
        </header>

        {/* Error messages */}
        {hasErrors && (
          <div
            className="mb-6 p-4 border rounded-none border-destructive/30 bg-destructive/5 animate-in fade-in slide-in-from-bottom-2 duration-300"
            role="alert"
          >
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-foreground text-sm mb-1">
                  Some data couldn’t be loaded
                </h3>
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

        {/* Stats — staggered */}
        <section
          className="mb-8 md:mb-10 animate-in fade-in slide-in-from-bottom-4 duration-500"
          style={{ animationDelay: '80ms' }}
        >
          <StatsGrid
            totalSubjects={data.stats?.total_subjects ?? 0}
            totalEvents={data.stats?.total_events ?? 0}
            totalDocuments={data.stats?.total_documents ?? 0}
            eventsToday={eventsToday}
            activeWorkflows={activeWorkflowsCount}
            subjectsByType={data.stats?.subjects_by_type}
            eventsByType={data.stats?.events_by_type}
          />
        </section>

        {/* Recent Activity — from analytics dashboard */}
        <section
          className="animate-in fade-in slide-in-from-bottom-4 duration-500"
          style={{ animationDelay: '160ms' }}
        >
          <div className="flex items-baseline justify-between gap-4 mb-3">
            <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-foreground">
              Recent activity
            </h2>
          </div>
          <div className="rounded-none border border-border/60 bg-card/80 backdrop-blur-sm overflow-hidden">
            <MinimalActivityFeed limit={8} recentEvents={data.stats?.recent_events} />
          </div>
        </section>
      </div>
    </div>
  )
}
