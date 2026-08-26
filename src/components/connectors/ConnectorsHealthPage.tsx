import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { AlertCircle, ChevronDown, ChevronRight, RefreshCw, ShieldAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from 'recharts'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'

const LAG_HISTORY_MAX = 30

export type ConnectorHealthItem = {
  connector_id?: string
  name?: string
  id?: string
  status?: string
  last_sync?: string
  last_event_at?: string
  error?: string
  /** Numeric consumer lag when API provides it; enables lag-over-time chart */
  lag?: number
  [key: string]: unknown
}

function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function ConnectorsHealthPage() {
  useRequireAuth()
  const [lagHistory, setLagHistory] = useState<Record<string, number[]>>({})
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['connectors', 'health'],
    queryFn: async () => {
      const res = await timelineApi.connectors.health()
      if (res.response?.status === 403) {
        const e = new Error('No permission') as Error & { is403?: boolean }
        e.is403 = true
        throw e
      }
      if (res.error) throw new Error('Failed to load connector health')
      const body = res.data as { connectors?: unknown[]; status?: string } | undefined
      return { connectors: body?.connectors ?? [], status: body?.status ?? 'unknown' }
    },
    refetchInterval: 15_000,
  })

  const items = (data?.connectors ?? []) as ConnectorHealthItem[]

  useEffect(() => {
    if (!items.length) return
    setLagHistory((prev) => {
      const next = { ...prev }
      for (const item of items) {
        const key = item.connector_id ?? item.id ?? ''
        if (!key) continue
        const lag = typeof item.lag === 'number' ? item.lag : null
        const arr = [...(next[key] ?? [])]
        if (lag !== null) {
          arr.push(lag)
          if (arr.length > LAG_HISTORY_MAX) arr.shift()
          next[key] = arr
        }
      }
      return next
    })
  }, [data?.connectors])

  const is403 =
    error &&
    typeof error === 'object' &&
    'is403' in error &&
    (error as Error & { is403?: boolean }).is403

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-bold text-foreground">Connector health</h1>
          <p className="text-sm text-muted-foreground">
            Status of registered connectors. Auto-refreshes every 15s.
          </p>
        </div>
        {!is403 && (
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        )}
      </div>

      {isLoading && <Skeleton className="h-24 w-full" />}
      {is403 && (
        <div className="p-4 rounded-none border border-border bg-card/80 flex flex-col items-center gap-3 text-center">
          <ShieldAlert className="w-10 h-10 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            You don’t have permission to view connector health.
          </p>
          <Link to="/">
            <Button variant="outline" size="sm">
              Back to Dashboard
            </Button>
          </Link>
        </div>
      )}
      {error && !is403 && (
        <div className="p-3 bg-destructive/10 border border-destructive/50 rounded-none flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {String(error)}
        </div>
      )}
      {!isLoading && !error && (
        <div className="grid gap-3">
          {items.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground rounded-none border border-border/50">
              No connector health data returned.
            </div>
          ) : (
            items.map((item, i) => {
              const key = item.connector_id ?? item.id ?? `connector-${i}`
              const connectorLagHistory = lagHistory[key] ?? []
              const isExpanded = expandedId === key
              const displayName = item.name ?? item.connector_id ?? item.id ?? `Connector ${i + 1}`
              return (
                <div
                  key={key}
                  className="rounded-none border border-border/50 bg-card/80 overflow-hidden"
                >
                  <button
                    type="button"
                    className="w-full text-left p-4 flex flex-wrap items-center gap-4 cursor-pointer hover:bg-muted/20 transition-colors"
                    onClick={() => setExpandedId((id) => (id === key ? null : key))}
                    aria-expanded={isExpanded}
                  >
                    <div className="flex items-center gap-1 shrink-0">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={item.status ?? 'unknown'} label={item.status ?? '—'} />
                      <span className="font-medium text-foreground">{displayName}</span>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      Last event: {formatRelativeTime(item.last_event_at ?? item.last_sync)}
                    </span>
                    {typeof item.lag === 'number' && (
                      <span className="text-sm text-muted-foreground">Lag: {item.lag}</span>
                    )}
                    {item.error && (
                      <span className="text-xs text-status-error">{String(item.error)}</span>
                    )}
                    {connectorLagHistory.length > 0 && (
                      <div className="w-24 h-8 shrink-0 ml-auto">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart
                            data={connectorLagHistory.map((lag, idx) => ({ idx, lag }))}
                            margin={{ top: 2, right: 2, bottom: 2, left: 2 }}
                          >
                            <YAxis hide domain={['auto', 'auto']} />
                            <Tooltip
                              content={({ active, payload }) =>
                                active && payload?.[0] ? (
                                  <span className="text-xs bg-popover border border-border px-2 py-1 rounded-none shadow">
                                    Lag: {payload[0].value}
                                  </span>
                                ) : null
                              }
                            />
                            <Line
                              type="monotone"
                              dataKey="lag"
                              stroke="var(--chart-1, hsl(var(--primary)))"
                              strokeWidth={1.5}
                              dot={false}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </button>
                  {isExpanded && (
                    <div className="border-t border-border/50 p-4 bg-muted/10 space-y-3">
                      <h3 className="text-sm font-semibold text-foreground">Connector detail</h3>
                      <dl className="grid grid-cols-2 gap-2 text-sm">
                        <dt className="text-muted-foreground">Name</dt>
                        <dd>{displayName}</dd>
                        <dt className="text-muted-foreground">ID</dt>
                        <dd className="font-mono text-xs">{key}</dd>
                        <dt className="text-muted-foreground">Status</dt>
                        <dd>{item.status ?? '—'}</dd>
                        <dt className="text-muted-foreground">Last sync</dt>
                        <dd>{formatRelativeTime(item.last_sync)}</dd>
                        <dt className="text-muted-foreground">Last event at</dt>
                        <dd>{formatRelativeTime(item.last_event_at)}</dd>
                        {typeof item.lag === 'number' && (
                          <>
                            <dt className="text-muted-foreground">Lag</dt>
                            <dd>{item.lag}</dd>
                          </>
                        )}
                        {item.error && (
                          <>
                            <dt className="text-muted-foreground">Error</dt>
                            <dd className="text-status-error">{String(item.error)}</dd>
                          </>
                        )}
                      </dl>
                      <p className="text-xs text-muted-foreground">
                        Connector mapping UI will be available when the backend exposes connector
                        mappings CRUD (see roadmap).
                      </p>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
