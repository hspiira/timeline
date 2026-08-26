import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { Activity, AlertCircle, Circle, Loader2, RefreshCw, Shield } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { RecentActivityCard } from '@/components/dashboard/RecentActivityCard'
import { StatsGrid, type StatsGridProps } from '@/components/dashboard/StatsGrid'
import { LandingPage } from '@/components/landing/LandingPage'
import { useEventStream } from '@/hooks/useActivitySubscription'
import { useHasSystemAccess } from '@/hooks/useHasSystemAccess'
import { getApiBaseUrl, getAuthToken, getTenantId, timelineApi } from '@/lib/api-client'
import { getApiErrorDisplay } from '@/lib/api-utils'
import { authStore } from '@/lib/auth-store'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import type { components } from '@/lib/timeline-api'
import type { WorkflowResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

type DashboardStatsResponse = components['schemas']['DashboardStatsResponse']

type ConnectorHealthItem = {
  connector_id?: string
  status?: string
  last_event_at?: string
  error?: string
  lag?: number
}

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

/** Response shape for GET /api/v1/tenants/integrity/summary (when backend implements it). */
interface IntegritySummaryResponse {
  healthy?: number
  broken?: number
  unverified?: number
  last_verified?: string | null
}

/** Chain integrity breakdown. Wired to GET /api/v1/tenants/integrity/summary; shows "—" when endpoint is absent or errors. */
function ChainIntegrityCard() {
  const authState = useStore(authStore)
  const { data: summary } = useQuery({
    queryKey: ['integrity', 'summary'],
    queryFn: async (): Promise<{
      healthy: number
      broken: number
      unverified: number
      lastVerified: string | null
    } | null> => {
      const baseUrl = getApiBaseUrl()
      const token = getAuthToken()
      const tenantId = getTenantId()
      const res = await fetch(`${baseUrl}/api/v1/tenants/integrity/summary`, {
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
          ...(tenantId && { 'X-Tenant-ID': tenantId }),
        },
      })
      if (!res.ok) return null
      const raw = (await res.json()) as IntegritySummaryResponse
      const healthy = typeof raw.healthy === 'number' ? raw.healthy : 0
      const broken = typeof raw.broken === 'number' ? raw.broken : 0
      const unverified = typeof raw.unverified === 'number' ? raw.unverified : 0
      const lastVerified = typeof raw.last_verified === 'string' ? raw.last_verified : null
      return { healthy, broken, unverified, lastVerified }
    },
    enabled: !!authState.user,
  })

  const healthy = summary?.healthy ?? '—'
  const broken = summary?.broken ?? '—'
  const unverified = summary?.unverified ?? '—'
  const lastVerified = summary?.lastVerified
    ? (() => {
        const d = new Date(summary.lastVerified)
        const diffMs = Date.now() - d.getTime()
        const mins = Math.floor(diffMs / 60000)
        if (mins < 1) return 'Just now'
        if (mins < 60) return `${mins} minutes ago`
        return `${Math.floor(mins / 60)} hours ago`
      })()
    : '—'

  return (
    <div className="rounded-none border border-border bg-card p-4">
      <h2 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
        <Shield className="w-4 h-4 text-muted-foreground" />
        Chain integrity
      </h2>
      <dl className="space-y-1.5 text-sm">
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-status-ok" aria-hidden /> Healthy
          </dt>
          <dd className="font-medium tabular-nums">{healthy}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-status-error" aria-hidden /> Broken
          </dt>
          <dd className="font-medium tabular-nums">
            {typeof broken === 'number' ? (
              <Link to="/subjects" className="text-primary hover:underline">
                {broken} subjects
              </Link>
            ) : (
              broken
            )}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-muted-foreground flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-muted-foreground/50" aria-hidden /> Unverified
          </dt>
          <dd className="font-medium tabular-nums">{unverified}</dd>
        </div>
      </dl>
      <p className="text-xs text-muted-foreground mt-2 pt-2 border-t border-border/50">
        Last verified: {lastVerified}
      </p>
    </div>
  )
}

function HomePage() {
  const authState = useStore(authStore)
  const hasSystemAccess = useHasSystemAccess(!!authState.user)

  const [data, setData] = useState<DashboardData>({
    stats: null,
    workflows: [],
  })
  const [, setLoading] = useState(true)
  const [errors, setErrors] = useState<FetchError[]>([])

  const { isConnected } = useEventStream({
    enabled: !!authState.user,
    onNewActivity: () => fetchDashboard(),
  })

  const { data: connectorsData } = useQuery({
    queryKey: ['connectors', 'health'],
    queryFn: async () => {
      const res = await timelineApi.connectors.health()
      if (res.error) return { connectors: [] as ConnectorHealthItem[], status: 'unknown' }
      const body = res.data as { connectors?: unknown[]; status?: string }
      return { connectors: body?.connectors ?? [], status: body?.status ?? 'unknown' }
    },
    enabled: !!authState.user,
    refetchInterval: 15_000,
  })
  const { data: pendingRepairs } = useQuery({
    queryKey: ['integrity', 'repairs', 'pending-approval'],
    queryFn: async () => {
      const res = await timelineApi.integrity.repair.list({
        limit: 1,
        repair_status: 'Pending Approval',
      })
      return res.error ? 0 : (res.data?.total ?? 0)
    },
    enabled: !!authState.user,
    refetchInterval: 60_000,
  })

  const connectorList = (connectorsData?.connectors ?? []) as ConnectorHealthItem[]
  const activeConnectors = connectorList.filter(
    (c) => c.status === 'running' || c.status === 'ok',
  ).length

  const eventsToday = useMemo(() => {
    const recent = data.stats?.recent_events ?? []
    const today = new Date().toDateString()
    return recent.filter((e) => new Date(e.event_time).toDateString() === today).length
  }, [data.stats?.recent_events])

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
          status === 403 ? 'Access denied to dashboard' : 'Failed to load dashboard stats',
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
      setErrors([
        { field: 'analytics', message: 'An unexpected error occurred while loading dashboard' },
      ])
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

  const greeting = useMemo(() => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 18) return 'Good afternoon'
    return 'Good evening'
  }, [])

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

  const loadingStats = data.stats === null && errors.length === 0
  const totalSubjects = data.stats?.total_subjects ?? 0
  const openRepairs = pendingRepairs ?? 0

  return (
    <div className="dashboard-page min-h-[calc(100vh-4rem)] relative">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04] dark:opacity-[0.06]"
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
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 py-5 pl-2 sm:pl-3">
            <div>
              <h1 className="font-display text-xl sm:text-2xl font-bold text-foreground tracking-tight">
                {greeting}, {username}
              </h1>
              <p className="mt-0.5 text-sm text-muted-foreground flex items-center gap-2">
                Event integrity at a glance.
                {isConnected && (
                  <span className="inline-flex items-center gap-1 text-status-ok font-medium">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-ok opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-status-ok" />
                    </span>
                    Live
                  </span>
                )}
              </p>
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

        {/* Stats row */}
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          {loadingStats ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-24 rounded-none border border-border bg-muted/30 animate-pulse"
                />
              ))}
            </div>
          ) : (
            <StatsGrid
              {...({
                totalSubjects,
                totalEvents,
                eventsToday,
                activeConnectors,
                totalConnectors: connectorList.length,
                openRepairs,
                subjectsByType: data.stats?.subjects_by_type,
                eventsByType: data.stats?.events_by_type,
                showConnectorStat: hasSystemAccess !== false,
              } satisfies StatsGridProps)}
            />
          )}
        </div>

        {/* Integrity summary + Connector strip (Connectors card gated by hasSystemAccess) */}
        <div
          className={cn(
            'grid grid-cols-1 gap-4 md:gap-5 animate-in fade-in slide-in-from-bottom-4 duration-500',
            hasSystemAccess !== false ? 'lg:grid-cols-12' : '',
          )}
        >
          <div className={hasSystemAccess !== false ? 'lg:col-span-4' : 'lg:col-span-12'}>
            <ChainIntegrityCard />
          </div>
          {hasSystemAccess !== false && (
            <div className="lg:col-span-8">
              <div className="rounded-none border border-border bg-card p-4">
                <h2 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-muted-foreground" />
                  Connectors
                  <span className="text-xs font-normal text-muted-foreground">
                    {activeConnectors} of {connectorList.length} running
                  </span>
                </h2>
                <div className="flex flex-wrap gap-2">
                  {connectorList.length === 0 ? (
                    <span className="text-sm text-muted-foreground">No connector data</span>
                  ) : (
                    connectorList.map((c, i) => {
                      const status = (c.status ?? 'unknown').toLowerCase()
                      const isOk = status === 'running' || status === 'ok'
                      const isWarn = status === 'degraded'
                      return (
                        <div
                          key={c.connector_id ?? i}
                          className={cn(
                            'inline-flex items-center gap-1.5 px-2 py-1 rounded-none border text-xs',
                            isOk && 'border-status-ok/50 bg-status-ok/10 text-status-ok',
                            isWarn && 'border-status-warn/50 bg-status-warn/10 text-status-warn',
                            !isOk &&
                              !isWarn &&
                              'border-status-error/50 bg-status-error/10 text-status-error',
                          )}
                        >
                          <Circle className="w-2 h-2 fill-current" />
                          <span>{c.connector_id ?? `Connector ${i + 1}`}</span>
                        </div>
                      )
                    })
                  )}
                </div>
                <Link
                  to="/connectors"
                  className="inline-block mt-2 text-xs font-medium text-primary hover:underline"
                >
                  View connector health →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Real-time event feed */}
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <RecentActivityCard limit={8} recentEvents={data.stats?.recent_events} />
        </div>
      </div>
    </div>
  )
}
