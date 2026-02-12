import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { MinimalActivityFeed } from '@/components/dashboard/MinimalActivityFeed'
import { StatsGrid } from '@/components/dashboard/StatsGrid'
import { timelineApi } from '@/lib/api-client'
import { Loader2, AlertCircle } from 'lucide-react'
import type { EventListResponse, SubjectResponse, WorkflowResponse } from '@/lib/types'

export const Route = createFileRoute('/')({
  component: HomePage,
})

interface DashboardData {
  events: EventListResponse[]
  totalEvents: number
  subjects: SubjectResponse[]
  workflows: WorkflowResponse[]
}

interface FetchError {
  field: 'events' | 'subjects' | 'workflows'
  message: string
}

function HomePage() {
  const authState = useRequireAuth()

  const [data, setData] = useState<DashboardData>({
    events: [],
    totalEvents: 0,
    subjects: [],
    workflows: [],
  })
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<FetchError[]>([])

  // Calculate today's events
  const eventsToday = useMemo(() => {
    const today = new Date().toDateString()
    return data.events.filter((event) => new Date(event.event_time).toDateString() === today)
  }, [data.events])

  // Calculate subjects created this week
  const subjectsThisWeek = useMemo(() => {
    const weekAgo = new Date()
    weekAgo.setDate(weekAgo.getDate() - 7)
    // SubjectResponse no longer has created_at, so we can't filter by creation date.
    // Return all subjects as a fallback metric.
    return data.subjects
  }, [data.subjects])

  // Count active workflows
  const activeWorkflowsCount = useMemo(() => {
    return data.workflows.filter((workflow) => (workflow as any).is_active).length
  }, [data.workflows])

  const fetchDashboard = useCallback(async () => {
    setLoading(true)
    setErrors([])
    try {
      const results = await Promise.allSettled([
        timelineApi.events.listAll(),
        timelineApi.events.count(),
        timelineApi.subjects.list(),
        timelineApi.workflows.list(),
      ])

      const newErrors: FetchError[] = []
      const newData: DashboardData = {
        events: [],
        totalEvents: 0,
        subjects: [],
        workflows: [],
      }

      // Process events response
      const eventsResult = results[0]
      if (eventsResult.status === 'fulfilled' && eventsResult.value.data) {
        newData.events = eventsResult.value.data
      } else if (eventsResult.status === 'rejected') {
        newErrors.push({
          field: 'events',
          message: 'Failed to load events',
        })
      }

      // Process events count response
      const eventsCountResult = results[1]
      if (eventsCountResult.status === 'fulfilled' && eventsCountResult.value.data) {
        newData.totalEvents = (eventsCountResult.value.data as { total: number }).total
      }

      // Process subjects response
      const subjectsResult = results[2]
      if (subjectsResult.status === 'fulfilled' && subjectsResult.value.data) {
        newData.subjects = subjectsResult.value.data
      } else if (subjectsResult.status === 'rejected') {
        newErrors.push({
          field: 'subjects',
          message: 'Failed to load subjects',
        })
      }

      // Process workflows response
      const workflowsResult = results[3]
      if (workflowsResult.status === 'fulfilled' && workflowsResult.value.data) {
        newData.workflows = workflowsResult.value.data
      } else if (workflowsResult.status === 'rejected') {
        newErrors.push({
          field: 'workflows',
          message: 'Failed to load workflows',
        })
      }

      setData(newData)
      setErrors(newErrors)
    } catch (err) {
      console.error('Unexpected error fetching dashboard:', err)
      setErrors([
        {
          field: 'events',
          message: 'An unexpected error occurred while loading dashboard',
        },
      ])
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch data on user login and set up smart auto-refresh
  useEffect(() => {
    if (authState.user) {
      fetchDashboard()

      // Smart polling: pause when tab is hidden, resume when visible
      let interval: NodeJS.Timeout | null = null
      const POLL_INTERVAL = 30000 // 30 seconds (not 5)

      const startPolling = () => {
        if (!document.hidden) {
          interval = setInterval(() => {
            if (!document.hidden) {
              fetchDashboard()
            }
          }, POLL_INTERVAL)
        }
      }

      const handleVisibilityChange = () => {
        if (document.hidden) {
          // Tab is hidden - stop polling to save battery/bandwidth
          if (interval) {
            clearInterval(interval)
            interval = null
          }
        } else {
          // Tab is visible - resume polling
          startPolling()
        }
      }

      startPolling()
      document.addEventListener('visibilitychange', handleVisibilityChange)

      return () => {
        if (interval) {
          clearInterval(interval)
        }
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

  return (
    <>

        {/* Error messages */}
        {hasErrors && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xs">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-900 dark:text-red-200 text-sm mb-1">
                  Unable to load some data
                </h3>
                <ul className="space-y-0.5 text-xs text-red-800 dark:text-red-300">
                  {errors.map((error) => (
                    <li key={error.field}>
                      • {error.field.charAt(0).toUpperCase() + error.field.slice(1)}: {error.message}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={fetchDashboard}
                  className="mt-2 text-xs font-medium text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 underline"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <StatsGrid
          totalSubjects={data.subjects.length}
          subjectsThisWeek={subjectsThisWeek.length}
          totalEvents={data.totalEvents}
          eventsToday={eventsToday.length}
          activeWorkflows={activeWorkflowsCount}
        />

        {/* Recent Activity */}
        <div>
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Recent Activity
          </h2>
          <div className="bg-card/80 backdrop-blur-sm rounded-xs border border-border/50">
            <MinimalActivityFeed limit={8} />
          </div>
        </div>
    </>
  )
}
