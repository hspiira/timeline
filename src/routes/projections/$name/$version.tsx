import { createFileRoute, Link } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { getTenantId } from '@/lib/api-client'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { AlertCircle, History, Wrench } from 'lucide-react'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/projections/$name/$version')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  validateSearch: (search: Record<string, unknown>): { subject_id: string | undefined } => ({
    subject_id: typeof search.subject_id === 'string' ? search.subject_id : undefined,
  }),
  component: ProjectionStatePage,
})

type ProjectionDefinitionResponse = components['schemas']['ProjectionDefinitionResponse']

function ProjectionStatePage() {
  useRequireAuth()
  const queryClient = useQueryClient()
  const { name, version } = Route.useParams()
  const { subject_id } = Route.useSearch()
  const [subjectId, setSubjectId] = useState(subject_id ?? '')
  const [viewMode, setViewMode] = useState<'json' | 'table'>('json')
  const [asOf, setAsOf] = useState('')
  const [replayAsOf, setReplayAsOf] = useState<string | null>(null)
  const [rebuildMessage, setRebuildMessage] = useState<string | null>(null)
  const [rebuildLoading, setRebuildLoading] = useState(false)
  const tenantId = getTenantId()

  const versionNum = Number(version)
  const effectiveSubjectId = subject_id || subjectId
  const asOfParam = replayAsOf || undefined

  const { data: projections = [], isLoading: projectionsLoading } = useQuery({
    queryKey: ['projections', tenantId ?? ''],
    queryFn: async () => {
      if (!tenantId) return []
      const res = await timelineApi.projections.list(tenantId)
      if (res.error || !res.data) return []
      return res.data
    },
    enabled: !!tenantId && !Number.isNaN(versionNum),
  })

  // system_latest_seq is optional from the API; not in OpenAPI ProjectionDefinitionResponse yet.
  const projection = projections.find(
    (p) => p.name === name && p.version === versionNum
  ) as (ProjectionDefinitionResponse & { system_latest_seq?: number }) | undefined

  // Normalize as-of to ISO (same as subject State tab) so API gets a well-defined value
  const asOfDisplay =
    replayAsOf != null && replayAsOf !== ''
      ? (() => {
          const d = new Date(replayAsOf)
          const y = d.getFullYear()
          const m = String(d.getMonth() + 1).padStart(2, '0')
          const day = String(d.getDate()).padStart(2, '0')
          const h = String(d.getHours()).padStart(2, '0')
          const min = String(d.getMinutes()).padStart(2, '0')
          return `${y}-${m}-${day}T${h}:${min}`
        })()
      : asOf

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

  const handleRebuild = async () => {
    if (!tenantId || Number.isNaN(versionNum)) return
    setRebuildLoading(true)
    setRebuildMessage(null)
    try {
      const res = await timelineApi.projections.rebuild(tenantId, name, versionNum)
      const status = res.response?.status
      if (status === 202) {
        setRebuildMessage('Rebuild started. Watermark will reset and catch up; refresh or revisit to see progress.')
        await queryClient.invalidateQueries({ queryKey: ['projections', tenantId ?? ''] })
      } else {
        setRebuildMessage(res.error ? String(res.error) : 'Rebuild request failed.')
      }
    } catch (err) {
      setRebuildMessage(err instanceof Error ? err.message : 'Rebuild failed.')
    } finally {
      setRebuildLoading(false)
    }
  }

  const lagText =
    projection && typeof projection.system_latest_seq === 'number'
      ? (() => {
          const lag = projection.system_latest_seq - projection.last_event_seq
          return lag <= 0 ? 'Up to date' : `${lag} events behind`
        })()
      : null

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

      {projectionsLoading && (
        <div className="mb-4">
          <Skeleton className="h-6 w-48" />
        </div>
      )}
      {!projectionsLoading && projection && (
        <div className="mb-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <span>
            Watermark (seq): <span className="font-mono text-foreground">{projection.last_event_seq}</span>
          </span>
          <span>
            Lag: {lagText ?? '—'}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRebuild}
            disabled={rebuildLoading}
          >
            <Wrench className="w-3.5 h-3.5" />
            Rebuild from genesis
          </Button>
          {rebuildMessage && (
            <span className="text-xs text-foreground/80">{rebuildMessage}</span>
          )}
        </div>
      )}
      {!projectionsLoading && projections.length > 0 && !projection && (
        <p className="mb-4 text-sm text-muted-foreground">
          Projection not found.{' '}
          <Link to="/projections" className="text-primary hover:underline">
            Back to Projections
          </Link>
        </p>
      )}

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
                value={asOfDisplay}
                onChange={(e) => setAsOf(e.target.value)}
                className="px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setReplayAsOf(asOf ? new Date(asOf).toISOString() : null)}
              >
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
            <div className="p-3 bg-destructive/10 border border-destructive/50 rounded-none flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {String(error)}
            </div>
          )}
          {stateData && stateObj && (
            <div className="bg-card/80 rounded-none border border-border/50 p-4">
              {replayAsOf && (
                <p className="text-xs text-muted-foreground mb-2">
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
