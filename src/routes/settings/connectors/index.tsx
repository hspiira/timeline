import { createFileRoute } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Skeleton } from '@/components/ui/Skeleton'
import { AlertCircle, CheckCircle } from 'lucide-react'

export const Route = createFileRoute('/settings/connectors/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: ConnectorsHealthPage,
})

type ConnectorHealthItem = {
  name?: string
  status?: string
  last_sync?: string
  error?: string
  [key: string]: unknown
}

function ConnectorsHealthPage() {
  useRequireAuth()

  const { data: health, isLoading, error } = useQuery({
    queryKey: ['connectors', 'health'],
    queryFn: async () => {
      const res = await timelineApi.connectors.health()
      if (res.error) throw new Error('Failed to load connector health')
      return (res.data ?? []) as ConnectorHealthItem[]
    },
  })

  const items = Array.isArray(health) ? health : health != null ? [health] : []

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-foreground">Connector health</h1>
      <p className="text-sm text-muted-foreground">
        Status of registered connectors. Data is refreshed on load.
      </p>

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
                key={i}
                className="p-4 rounded-none border border-border/50 bg-card/80 flex flex-wrap items-center gap-4"
              >
                <div className="flex items-center gap-2">
                  {item.status === 'ok' || item.status === 'healthy' ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
                  )}
                  <span className="font-medium text-foreground">
                    {item.name ?? item.id ?? `Connector ${i + 1}`}
                  </span>
                </div>
                <span className="text-sm text-muted-foreground">
                  Status: {String(item.status ?? '—')}
                </span>
                {item.last_sync && (
                  <span className="text-xs text-muted-foreground">
                    Last sync: {String(item.last_sync)}
                  </span>
                )}
                {item.error && (
                  <span className="text-xs text-red-600 dark:text-red-400">
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
