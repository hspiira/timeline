import { createFileRoute, Link } from '@tanstack/react-router'
import { useState } from 'react'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'
import {
  GitBranch,
  AlertCircle,
  Users,
  Calendar,
  FileCheck,
  ExternalLink,
  Trash2,
  Plus,
} from 'lucide-react'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'
import SubjectSelector from '@/components/subjects/SubjectSelector'
import { FlowWorkflowSteps } from '@/components/flows/FlowWorkflowSteps'
export const Route = createFileRoute('/flows/$flowId')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: FlowDetailPage,
})

function FlowDetailPage() {
  const { flowId } = Route.useParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [addSubjectId, setAddSubjectId] = useState('')
  const [adding, setAdding] = useState(false)
  const [removingId, setRemovingId] = useState<string | null>(null)

  const {
    data: flow,
    isLoading: flowLoading,
    isError: flowError,
    error: flowErr,
  } = useQuery({
    queryKey: ['flow', flowId],
    queryFn: async () => {
      const { data, error } = await timelineApi.flows.get(flowId)
      if (error) throw new Error('Failed to load flow')
      return data
    },
    enabled: !!flowId,
  })

  const { data: workflow } = useQuery({
    queryKey: ['workflow', flow?.workflow_id],
    queryFn: async () => {
      if (!flow?.workflow_id) return null
      const { data } = await timelineApi.workflows.get(flow.workflow_id)
      return data
    },
    enabled: !!flow?.workflow_id,
  })

  const { data: subjects = [], isLoading: subjectsLoading } = useQuery({
    queryKey: ['flow-subjects', flowId],
    queryFn: async () => {
      const { data, error } = await timelineApi.flows.listSubjects(flowId)
      if (error) throw new Error('Failed to load subjects')
      return Array.isArray(data) ? data : []
    },
    enabled: !!flowId,
  })

  const subjectIds = subjects.map((s) => s.subject_id).filter(Boolean)
  const { data: subjectDetailsMap = {} } = useQuery({
    queryKey: ['flow-subject-details', flowId, subjectIds],
    queryFn: async () => {
      const results = await Promise.all(
        subjectIds.map((id) =>
          timelineApi.subjects.get(id).then(({ data }) => ({ id, data }))
        )
      )
      const map: Record<string, { display_name?: string | null; external_ref?: string | null }> = {}
      results.forEach(({ id, data }) => {
        if (data) map[id] = { display_name: data.display_name, external_ref: data.external_ref }
      })
      return map
    },
    enabled: !!flowId && subjectIds.length > 0,
  })

  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ['flow-events', flowId],
    queryFn: async () => {
      const { data, error } = await timelineApi.flows.listEvents(flowId, {
        limit: 100,
      })
      if (error) throw new Error('Failed to load events')
      return Array.isArray(data) ? data : []
    },
    enabled: !!flowId,
  })

  const { data: compliance, isLoading: complianceLoading } = useQuery({
    queryKey: ['flow-compliance', flowId],
    queryFn: async () => {
      const { data, error } = await timelineApi.flows.getDocumentCompliance(
        flowId
      )
      if (error) throw new Error('Failed to load compliance')
      return data
    },
    enabled: !!flowId,
  })

  if (flowLoading || !flow) {
    if (flowError) {
      return (
        <EmptyState
          icon={AlertCircle}
          title="Flow not found"
          description={flowErr?.message ?? 'The flow may have been removed.'}
        />
      )
    }
    return (
      <div className="flex items-center justify-center min-h-[300px] gap-3 text-muted-foreground">
        <LoadingIcon />
        <span>Loading flow...</span>
      </div>
    )
  }

  return (
    <>
      <Breadcrumbs
        items={[
          { href: '/flows', label: 'Flows' },
          { label: flow.name },
        ]}
      />

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-1">{flow.name}</h1>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          {flow.workflow_id && (
            <span className="flex items-center gap-1">
              <GitBranch className="w-4 h-4" />
              <Link
                to="/settings/workflows"
                className="hover:text-foreground underline underline-offset-2"
              >
                {workflow?.name ?? flow.workflow_id}
              </Link>
            </span>
          )}
          {flow.hierarchy_values &&
            Object.keys(flow.hierarchy_values).length > 0 && (
              <span>
                {Object.entries(flow.hierarchy_values)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(', ')}
              </span>
            )}
        </div>
      </div>

      {/* Summary row: Subjects, Events, Document compliance */}
      <div className="flex flex-wrap items-center gap-4 py-3 px-4 rounded-lg bg-muted/30 border border-border/50 mb-4">
        <div className="flex items-center gap-2 text-sm">
          <Users className="w-4 h-4 text-muted-foreground" />
          <span className="text-muted-foreground">Subjects</span>
          <span className="font-medium text-foreground">{subjectsLoading ? '…' : subjects.length}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Calendar className="w-4 h-4 text-muted-foreground" />
          <span className="text-muted-foreground">Events</span>
          <span className="font-medium text-foreground">{eventsLoading ? '…' : events.length}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <FileCheck className="w-4 h-4 text-muted-foreground" />
          <span className="text-muted-foreground">Document compliance</span>
          {complianceLoading ? (
            <span className="text-muted-foreground">…</span>
          ) : compliance?.all_satisfied ? (
            <span className="text-green-600 dark:text-green-400 font-medium">Satisfied</span>
          ) : compliance ? (
            <span className="text-amber-600 dark:text-amber-400 font-medium">Action needed</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </div>
      </div>
      <p className="text-sm text-muted-foreground mb-6 max-w-2xl">
        <strong>Subjects</strong> are saved on the server when you add or remove them; they link who this flow is about.{' '}
        <strong>Events</strong> are recorded by the system (e.g. when automations run); completing a step in the UI only saves progress in this browser and does not create an event yet.{' '}
        <strong>Document compliance</strong> is live and can block completing a step until requirements are met.
      </p>

      <div className="space-y-8">
        {/* Workflow execution: steps */}
        {workflow && (
          <FlowWorkflowSteps
            flowId={flowId}
            workflow={workflow}
            eventCount={events.length}
          />
        )}

        {/* Subjects */}
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2 flex items-center gap-2">
            <Users className="w-5 h-5" />
            Subjects ({subjects.length})
          </h2>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <SubjectSelector
              value={addSubjectId}
              onChange={setAddSubjectId}
              excludeSubjectIds={subjectIds}
            />
            <Button
              size="sm"
              disabled={!addSubjectId || adding}
              onClick={async () => {
                if (!addSubjectId) return
                setAdding(true)
                const { error } = await timelineApi.flows.addSubjects(flowId, {
                  subject_ids: [addSubjectId],
                })
                setAdding(false)
                if (error) {
                  toast.error('Failed to add subject', String((error as { message?: string }).message ?? 'Unknown error'))
                  return
                }
                setAddSubjectId('')
                queryClient.invalidateQueries({ queryKey: ['flow-subjects', flowId] })
                queryClient.invalidateQueries({ queryKey: ['flow-subject-details', flowId] })
                toast.success('Subject added')
              }}
            >
              {adding ? <LoadingIcon /> : <Plus className="w-4 h-4" />}
              Add
            </Button>
          </div>
          {subjectsLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <LoadingIcon />
              Loading subjects...
            </div>
          ) : subjects.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No subjects linked to this flow.
            </p>
          ) : (
            <ul className="list-none divide-y divide-border/50 border border-border/50 rounded-none bg-card/50">
              {subjects.map((s) => {
                const details = subjectDetailsMap[s.subject_id]
                const displayName = details?.display_name ?? null
                const externalRef = details?.external_ref ?? null
                const primaryLabel =
                  displayName || externalRef || s.subject_id
                const secondaryLabel =
                  displayName
                    ? (externalRef ?? s.subject_id)
                    : externalRef
                    ? s.subject_id
                    : null
                return (
                  <li
                    key={s.subject_id}
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <div className="min-w-0">
                      <Link
                        to="/subjects/$subjectId"
                        params={{ subjectId: s.subject_id }}
                        search={{ tab: 'events', event_id: undefined }}
                        className="text-primary hover:underline font-medium block truncate"
                      >
                        {primaryLabel}
                      </Link>
                      {secondaryLabel && (
                        <span className="text-muted-foreground text-xs block truncate">
                          {secondaryLabel}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {s.role && (
                        <span className="text-muted-foreground text-sm">
                          {s.role}
                        </span>
                      )}
                      <Link
                        to="/subjects/$subjectId"
                        params={{ subjectId: s.subject_id }}
                        search={{ tab: 'events', event_id: undefined }}
                        className="text-muted-foreground hover:text-foreground"
                        title="Open subject"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-muted-foreground hover:text-destructive"
                        title="Remove from flow"
                        disabled={removingId === s.subject_id}
                        onClick={async () => {
                          setRemovingId(s.subject_id)
                          const { error } = await timelineApi.flows.removeSubject(
                            flowId,
                            s.subject_id
                          )
                          setRemovingId(null)
                          if (error) {
                            toast.error('Failed to remove subject', String((error as { message?: string }).message ?? 'Unknown error'))
                            return
                          }
                        queryClient.invalidateQueries({ queryKey: ['flow-subjects', flowId] })
                        queryClient.invalidateQueries({ queryKey: ['flow-subject-details', flowId] })
                        toast.success('Subject removed')
                        }}
                      >
                        {removingId === s.subject_id ? (
                          <LoadingIcon />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        {/* Events */}
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2 flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Events ({events.length})
          </h2>
          {eventsLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <LoadingIcon />
              Loading events...
            </div>
          ) : events.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No events recorded for this flow yet.
            </p>
          ) : (
            <ul className="list-none divide-y divide-border/50 border border-border/50 rounded-none bg-card/50">
              {events.slice(0, 20).map((ev) => (
                <li
                  key={ev.id}
                  className="flex items-center justify-between px-4 py-3"
                >
                  <div>
                    <span className="font-medium text-foreground">
                      {ev.event_type}
                    </span>
                    <span className="text-muted-foreground text-sm ml-2">
                      {ev.event_time
                        ? new Date(ev.event_time).toLocaleString()
                        : ''}
                    </span>
                  </div>
                  <Link
                    to="/subjects/$subjectId/events/$eventId"
                    params={{
                      subjectId: ev.subject_id,
                      eventId: ev.id,
                    }}
                    className="text-primary hover:underline text-sm"
                  >
                    View event
                  </Link>
                </li>
              ))}
              {events.length > 20 && (
                <li className="px-4 py-2 text-sm text-muted-foreground">
                  Showing 20 of {events.length} events
                </li>
              )}
            </ul>
          )}
        </section>

        {/* Document compliance */}
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2 flex items-center gap-2">
            <FileCheck className="w-5 h-5" />
            Document compliance
          </h2>
          {complianceLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <LoadingIcon />
              Loading compliance...
            </div>
          ) : !compliance ? (
            <p className="text-sm text-muted-foreground">
              No document requirements for this workflow.
            </p>
          ) : (
            <div className="space-y-3">
              {compliance.all_satisfied ? (
                <p className="text-sm text-green-600 dark:text-green-400">
                  All document requirements are satisfied.
                </p>
              ) : (
                compliance.blocked_reasons &&
                compliance.blocked_reasons.length > 0 && (
                  <ul className="list-disc list-inside text-sm text-amber-600 dark:text-amber-400">
                    {compliance.blocked_reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )
              )}
              {compliance.items && compliance.items.length > 0 && (
                <div className="border border-border/50 rounded-none overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted/30 border-b border-border/50">
                        <th className="text-left px-4 py-2 font-medium">
                          Category
                        </th>
                        <th className="text-left px-4 py-2 font-medium">
                          Required
                        </th>
                        <th className="text-left px-4 py-2 font-medium">
                          Present
                        </th>
                        <th className="text-left px-4 py-2 font-medium">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {compliance.items.map((item) => (
                        <tr
                          key={item.document_category_id}
                          className="border-b border-border/30"
                        >
                          <td className="px-4 py-2">
                            {item.display_name || item.category_name}
                          </td>
                          <td className="px-4 py-2">{item.required_count}</td>
                          <td className="px-4 py-2">{item.present_count}</td>
                          <td className="px-4 py-2">
                            {item.satisfied ? (
                              <span className="text-green-600 dark:text-green-400">
                                OK
                              </span>
                            ) : (
                              <span className="text-amber-600 dark:text-amber-400">
                                {item.blocked_reason ?? 'Missing'}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </>
  )
}
