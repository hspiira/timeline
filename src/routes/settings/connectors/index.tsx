import { createFileRoute } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'

export const Route = createFileRoute('/settings/connectors/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: ConnectorsHealthPage,
})

type ConnectorHealthItem = {
  connector_id?: string
  name?: string
  id?: string
  status?: string
  last_sync?: string
  last_event_at?: string
  error?: string
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

function ConnectorsHealthPage() {
  useRequireAuth()

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['connectors', 'health'],
    queryFn: async () => {
      const res = await timelineApi.connectors.health()
      if (res.error) throw new Error('Failed to load connector health')
      const body = res.data as { connectors?: unknown[]; status?: string } | undefined
      return { connectors: body?.connectors ?? [], status: body?.status ?? 'unknown' }
    },
    refetchInterval: 15_000,
  })

  const items = (data?.connectors ?? []) as ConnectorHealthItem[]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-bold text-foreground">Connector health</h1>
          <p className="text-sm text-muted-foreground">
            Status of registered connectors. Auto-refreshes every 15s.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {isLoading && <Skeleton className="h-24 w-full" />}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex items-center gap-2 text-sm text-red-800 dark:text-red-200">
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
            items.map((item, i) => (
              <div
                key={item.connector_id ?? item.id ?? i}
                className="p-4 rounded-none border border-border/50 bg-card/80 flex flex-wrap items-center gap-4"
              >
                <div className="flex items-center gap-2">
                  <StatusBadge status={item.status ?? 'unknown'} label={item.status ?? '—'} />
                  <span className="font-medium text-foreground">
                    {item.name ?? item.connector_id ?? item.id ?? `Connector ${i + 1}`}
                  </span>
                </div>
                <span className="text-sm text-muted-foreground">
                  Last event: {formatRelativeTime(item.last_event_at ?? item.last_sync)}
                </span>
                {item.error && (
                  <span className="text-xs text-status-error">
                    {String(item.error)}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
