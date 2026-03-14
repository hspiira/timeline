import { createFileRoute } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { getTenantId } from '@/lib/api-client'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { AlertCircle, History } from 'lucide-react'

export const Route = createFileRoute('/projections/$name/$version')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  validateSearch: (search: Record<string, unknown>): { subject_id: string | undefined } => ({
    subject_id: typeof search.subject_id === 'string' ? search.subject_id : undefined,
  }),
  component: ProjectionStatePage,
})

function ProjectionStatePage() {
  useRequireAuth()
  const { name, version } = Route.useParams()
  const { subject_id } = Route.useSearch()
  const [subjectId, setSubjectId] = useState(subject_id ?? '')
  const [viewMode, setViewMode] = useState<'json' | 'table'>('json')
  const [asOf, setAsOf] = useState('')
  const [replayAsOf, setReplayAsOf] = useState<string | null>(null)
  const tenantId = getTenantId()

  const versionNum = Number(version)
  const effectiveSubjectId = subject_id || subjectId
  const asOfParam = replayAsOf || undefined

  const { data: stateData, isLoading, error } = useQuery({
    queryKey: ['projection-state', tenantId ?? '', name, versionNum, effectiveSubjectId, asOfParam],
    queryFn: async () => {
      if (!tenantId || !effectiveSubjectId) throw new Error('Missing tenant or subject')
      const res = await timelineApi.projections.getState(
        tenantId,
        name,
        versionNum,
        effectiveSubjectId,
        asOfParam ? { as_of: asOfParam } : undefined
      )
      if (res.error || !res.data) throw new Error('Failed to load state')
      return res.data
    },
    enabled: !!tenantId && !!effectiveSubjectId && !Number.isNaN(versionNum),
  })

  const stateObj = stateData?.state as Record<string, unknown> | undefined

  if (!tenantId) {
    return (
      <div className="p-4 text-sm text-muted-foreground">Select a tenant.</div>
    )
  }

  return (
    <>
      <Breadcrumbs
        items={[
          { label: 'Projections', href: '/projections' },
          { label: `${name} v${version}` },
        ]}
      />
      <div className="mb-4">
        <h1 className="text-lg font-bold text-foreground">
          {name} <span className="text-muted-foreground font-normal">v{version}</span>
        </h1>
      </div>

      {!subject_id && (
        <div className="mb-4 flex gap-2 items-center">
          <label className="text-sm text-muted-foreground">Subject ID</label>
          <input
            type="text"
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            placeholder="Enter subject ID"
            className="px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm w-64"
          />
        </div>
      )}

      {effectiveSubjectId && (
        <>
          <div className="mb-4 p-3 bg-muted/30 rounded-none border border-border/50">
            <h2 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
              <History className="w-4 h-4" />
              As-of (time-travel) — read-only
            </h2>
            <p className="text-xs text-muted-foreground mb-2">
              View state as of a specific time. Enter an ISO-8601 datetime. This does not modify live state.
            </p>
            <div className="flex gap-2 items-center">
              <input
                type="datetime-local"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                className="px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
              />
              <Button variant="outline" size="sm" onClick={() => setReplayAsOf(asOf || null)}>
                Replay
              </Button>
              {replayAsOf && (
                <Button variant="ghost" size="sm" onClick={() => { setReplayAsOf(null); setAsOf('') }}>
                  Clear
                </Button>
              )}
            </div>
          </div>
          <div className="flex gap-2 mb-2">
            <Button
              variant={viewMode === 'json' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('json')}
            >
              JSON
            </Button>
            <Button
              variant={viewMode === 'table' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('table')}
            >
              Table
            </Button>
          </div>

          {isLoading && <Skeleton className="h-40 w-full" />}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex items-center gap-2 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {String(error)}
            </div>
          )}
          {stateData && stateObj && (
            <div className="bg-card/80 rounded-none border border-border/50 p-4">
              {replayAsOf && (
                <p className="text-xs text-amber-600 dark:text-amber-400 mb-2">
                  Showing state as of {replayAsOf} (read-only replay)
                </p>
              )}
              {viewMode === 'json' && (
                <pre className="text-xs font-mono overflow-auto max-h-96">
                  {JSON.stringify(stateObj, null, 2)}
                </pre>
              )}
              {viewMode === 'table' && (
                <table className="w-full text-sm border-collapse">
                  <tbody>
                    {Object.entries(stateObj).map(([k, v]) => (
                      <tr key={k} className="border-b border-border/30">
                        <td className="py-1.5 pr-4 font-medium text-muted-foreground">{k}</td>
                        <td className="py-1.5 font-mono text-xs">
                          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}
    </>
  )
}
