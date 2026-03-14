import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { getTenantId } from '@/lib/api-client'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/button'
import { Database, Plus } from 'lucide-react'

export const Route = createFileRoute('/projections/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: ProjectionsPage,
})

function ProjectionsPage() {
  useRequireAuth()
  const navigate = useNavigate()
  const tenantId = getTenantId()

  const { data: projections = [], isLoading } = useQuery({
    queryKey: ['projections', tenantId ?? ''],
    queryFn: async () => {
      if (!tenantId) return []
      const res = await timelineApi.projections.list(tenantId)
      if (res.error || !res.data) return []
      return res.data
    },
    enabled: !!tenantId,
  })

  if (!tenantId) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Select a tenant to view projections.
      </div>
    )
  }

  return (
    <>
      <Breadcrumbs items={[{ label: 'Projections' }]} />
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold text-foreground">Projections</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate({ to: '/projections/new' })}
        >
          <Plus className="w-4 h-4" />
          New Projection
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : (
        <div className="bg-card/80 rounded-none border border-border/50 overflow-hidden">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-border/50 bg-muted/30 text-left text-muted-foreground font-medium">
                <th className="py-2 px-3">Name</th>
                <th className="py-2 px-3">Version</th>
                <th className="py-2 px-3">Watermark (seq)</th>
                <th className="py-2 px-3">Lag</th>
                <th className="py-2 px-3">Subject type</th>
                <th className="py-2 px-3">Active</th>
                <th className="py-2 px-3 w-24" />
              </tr>
            </thead>
            <tbody>
              {projections.map((p) => (
                <tr
                  key={`${p.name}-${p.version}`}
                  className="border-b border-border/30 hover:bg-muted/20"
                >
                  <td className="py-2 px-3 font-medium">{p.name}</td>
                  <td className="py-2 px-3">{p.version}</td>
                  <td className="py-2 px-3 font-mono">{p.last_event_seq}</td>
                  <td className="py-2 px-3 text-muted-foreground text-xs">
                    {/* system_latest_seq is optional from the API; not in OpenAPI ProjectionDefinitionResponse yet. Add to backend spec and run generate:api to type it. */}
                    {typeof (p as unknown as { system_latest_seq?: number }).system_latest_seq === 'number'
                      ? (() => {
                          const q = p as unknown as { last_event_seq: number; system_latest_seq: number }
                          const lag = q.system_latest_seq - q.last_event_seq
                          return lag <= 0 ? 'Up to date' : `${lag} events behind`
                        })()
                      : '—'}
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">{p.subject_type ?? '—'}</td>
                  <td className="py-2 px-3">{p.active ? 'Yes' : 'No'}</td>
                  <td className="py-2 px-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        navigate({
                          to: '/projections/$name/$version',
                          params: { name: p.name, version: String(p.version) },
                          search: { subject_id: undefined },
                        })
                      }
                    >
                      <Database className="w-3.5 h-3.5" />
                      View state
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {projections.length === 0 && (
            <div className="py-8 text-center text-muted-foreground text-sm">
              No projections. Create one to get started.
            </div>
          )}
        </div>
      )}
    </>
  )
}
