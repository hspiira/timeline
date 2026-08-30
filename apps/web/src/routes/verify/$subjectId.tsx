import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import {
  AlertCircle,
  AlertTriangle,
  Boxes,
  CheckCircle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  DownloadIcon,
  FileCheck,
  Wrench,
} from 'lucide-react'
import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Button } from '@/components/ui/button'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { Skeleton, SkeletonBreadcrumbs } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ChainVisualization } from '@/components/verify/ChainVisualization'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { formatFullDateTime } from '@/lib/format-date'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import type { components } from '@/lib/timeline-api'

const VERIFY_PAGE_SIZE = 20

type IntegrityEpochItem = components['schemas']['IntegrityEpochItem']

export const Route = createFileRoute('/verify/$subjectId')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: VerifyPage,
})

type IntegrityVerificationDetail = components['schemas']['IntegrityVerificationDetail']
type VerificationEventResult = components['schemas']['VerificationEventResult']

function VerificationTableRow({
  event,
  isExpanded,
  onToggle,
  onInitiateRepair,
  onViewProof,
}: {
  event: VerificationEventResult
  subjectId: string
  isExpanded: boolean
  onToggle: () => void
  onInitiateRepair: () => void
  onViewProof: () => void
}) {
  const hash = event.actual_hash || event.expected_hash || '—'
  const hashShort = hash !== '—' ? `${hash.slice(0, 12)}…` : '—'
  return (
    <>
      <tr className={`border-b border-border/30 ${!event.is_valid ? 'bg-status-warn/10' : ''}`}>
        <td className="py-1.5 pr-2 font-mono text-xs">{event.sequence}</td>
        <td className="py-1.5 pr-2">{event.event_type}</td>
        <td className="py-1.5 pr-2">
          {event.is_valid ? (
            <span className="text-status-ok">✓ Valid</span>
          ) : (
            <span className="text-status-error">✗ BREAK</span>
          )}
        </td>
        <td className="py-1.5 pr-2 font-mono text-xs">{hashShort}</td>
        <td className="py-1.5 pr-2 text-muted-foreground">{event.error_type ?? '—'}</td>
        <td className="py-1.5 pr-2">
          <button
            type="button"
            onClick={onToggle}
            className="p-0.5 rounded hover:bg-muted"
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        </td>
      </tr>
      {isExpanded && (
        <tr className="border-b border-border/30 bg-muted/30">
          <td colSpan={6} className="py-2 px-3 text-xs">
            <div className="grid gap-1 font-mono">
              {event.expected_hash != null && (
                <div>
                  Expected: <span className="font-mono break-all">{event.expected_hash}</span>
                </div>
              )}
              {event.actual_hash != null && (
                <div>
                  Actual: <span className="font-mono break-all">{event.actual_hash}</span>
                </div>
              )}
              <div className="flex flex-wrap gap-2 mt-2">
                <Button variant="outline" size="sm" className="w-fit" onClick={onViewProof}>
                  <FileCheck className="w-3 h-3" />
                  View Proof
                </Button>
                {!event.is_valid && (
                  <Button variant="outline" size="sm" className="w-fit" onClick={onInitiateRepair}>
                    <Wrench className="w-3 h-3" />
                    Initiate Repair
                  </Button>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function VerifyPage() {
  const statusId = useId()
  const authState = useRequireAuth()
  const navigate = useNavigate()
  const { subjectId } = Route.useParams()
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<'' | 'valid' | 'break'>('')
  const [detailPage, setDetailPage] = useState(0)

  const { data: epochs = [] } = useQuery({
    queryKey: ['integrity', 'epochs', subjectId],
    queryFn: async () => {
      const res = await timelineApi.integrity.listEpochs(subjectId)
      if (res.error || !res.data) return []
      return res.data as IntegrityEpochItem[]
    },
    enabled: !!authState.user && !!subjectId,
  })

  const fetchVerification = useCallback(
    () => timelineApi.integrity.verifySubjectDetail(subjectId),
    [subjectId],
  )

  const {
    data: verification,
    error,
    loading,
    refetch,
  } = useFetchWithError<IntegrityVerificationDetail>(fetchVerification, {
    defaultErrorMessage: 'Failed to verify chain',
    enabled: !!authState.user && !!subjectId,
  })

  useEffect(() => {
    if (authState.user && subjectId) refetch()
  }, [authState.user, subjectId, refetch])

  const eventsList = verification?.events ?? []
  const filteredEvents = useMemo(() => {
    if (filterStatus === '') return eventsList
    if (filterStatus === 'valid') return eventsList.filter((e) => e.is_valid)
    return eventsList.filter((e) => !e.is_valid)
  }, [eventsList, filterStatus])

  const paginatedEvents = useMemo(() => {
    const start = detailPage * VERIFY_PAGE_SIZE
    return filteredEvents.slice(start, start + VERIFY_PAGE_SIZE)
  }, [filteredEvents, detailPage])

  // biome-ignore lint/correctness/useExhaustiveDependencies: filterStatus is the trigger; a change to it is what resets the page.
  useEffect(() => {
    setDetailPage(0)
  }, [filterStatus])

  const detailTotalPages = Math.ceil(filteredEvents.length / VERIFY_PAGE_SIZE)
  const detailStart = detailPage * VERIFY_PAGE_SIZE
  const detailEnd = Math.min(detailStart + VERIFY_PAGE_SIZE, filteredEvents.length)

  const handleExportReport = () => {
    if (!verification) return

    const reportContent = {
      subjectId: verification.subject_id,
      tenantId: verification.tenant_id,
      verifiedAt: verification.verified_at,
      integrityStatus: verification.is_chain_valid ? 'Valid' : 'Tampered',
      summary: {
        totalEvents: verification.total_events,
        validEvents: verification.valid_events,
        invalidEvents: verification.invalid_events,
      },
      eventResults: verification.events?.map((e) => ({
        eventId: e.event_id,
        eventType: e.event_type,
        eventTime: e.event_time,
        sequence: e.sequence,
        isValid: e.is_valid,
        errorType: e.error_type || null,
        errorMessage: e.error_message || null,
        expectedHash: e.expected_hash || null,
        actualHash: e.actual_hash || null,
      })),
    }

    const dataStr = JSON.stringify(reportContent, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `chain-verification-${subjectId.slice(0, 8)}-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  if (!authState.user) {
    return null
  }

  if (loading) {
    return (
      <>
        {/* Skeleton Breadcrumbs */}
        <SkeletonBreadcrumbs />

        {/* Skeleton Header */}
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <Skeleton className="h-7 w-1/3" />
            <Skeleton className="h-6 w-24" />
          </div>
          <div className="flex flex-wrap gap-3 mb-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-32" />
          </div>
          <Skeleton className="h-4 w-1/2 mb-2" />
          <Skeleton className="h-4 w-1/3" />
        </div>

        {/* Skeleton Event Chain Timeline */}
        <div className="bg-card/80 rounded-none border border-border/50 p-3 mb-3">
          <Skeleton className="h-5 w-40 mb-2" />
          <div className="space-y-2">
            <div className="p-3 rounded-none border border-border/50 bg-muted/30">
              <Skeleton className="h-5 w-1/2 mb-2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
            <div className="p-3 rounded-none border border-border/50 bg-muted/30">
              <Skeleton className="h-5 w-1/2 mb-2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
            <div className="p-3 rounded-none border border-border/50 bg-muted/30">
              <Skeleton className="h-5 w-1/2 mb-2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
          </div>
        </div>

        {/* Skeleton Export Button */}
        <div className="flex justify-center">
          <Skeleton className="h-8 w-32" />
        </div>
      </>
    )
  }

  return (
    <>
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Subjects', href: '/subjects' },
          { label: `${subjectId.slice(0, 8)}...`, href: `/subjects/${subjectId}` },
          { label: 'Verify' },
        ]}
      />

      {/* Error Alert */}
      {error && (
        <div className="mb-3 p-2.5 bg-destructive/10 border border-destructive/50 rounded-none flex gap-2">
          <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-destructive text-xs">Verification Failed</h3>
            <p className="text-xs text-destructive mt-0.5">{error}</p>
          </div>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={() => refetch()}
            className="shrink-0"
          >
            Retry
          </Button>
        </div>
      )}

      {verification && (
        <>
          {/* Epoch-level integrity dashboard */}
          {epochs.length > 0 && (
            <div className="bg-card/80 rounded-none border border-border/50 p-3 mb-3">
              <h2 className="text-sm font-semibold text-foreground mb-2">Epochs</h2>
              <p className="text-xs text-muted-foreground mb-2">
                Per-epoch status and event counts. Use the detail table below for full chain
                verification.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border/50 text-left text-muted-foreground font-medium">
                      <th className="py-2 pr-2">#</th>
                      <th className="py-2 pr-2">Status</th>
                      <th className="py-2 pr-2">Events</th>
                      <th className="py-2 pr-2">Opened</th>
                      <th className="py-2 pr-2">Sealed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {epochs.map((epoch: IntegrityEpochItem) => (
                      <tr key={epoch.id} className="border-b border-border/30 hover:bg-muted/20">
                        <td className="py-2 pr-2 font-mono">{epoch.epoch_number}</td>
                        <td className="py-2 pr-2">
                          <StatusBadge status={epoch.status} label={epoch.status} />
                        </td>
                        <td className="py-2 pr-2">{epoch.event_count}</td>
                        <td className="py-2 pr-2 text-muted-foreground">
                          {formatFullDateTime(epoch.opened_at)}
                        </td>
                        <td className="py-2 pr-2 text-muted-foreground">
                          {epoch.sealed_at ? formatFullDateTime(epoch.sealed_at) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Link
                to="/subjects/$subjectId/epochs"
                params={{ subjectId }}
                className="inline-block mt-2 text-xs font-medium text-primary hover:underline"
              >
                Open full epochs view →
              </Link>
            </div>
          )}

          {/* Header and Stats Row */}
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <h1 className="text-lg font-bold text-foreground">Chain Verification</h1>
              {verification.is_chain_valid ? (
                <div className="flex items-center gap-1 px-2.5 py-1 bg-status-ok/10 border border-status-ok/50 rounded-none">
                  <CheckCircle className="w-3.5 h-3.5 text-status-ok" />
                  <span className="font-semibold text-status-ok text-xs">Valid Chain</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 px-2.5 py-1 bg-status-error/10 border border-status-error/50 rounded-none">
                  <AlertTriangle className="w-3.5 h-3.5 text-status-error" />
                  <span className="font-semibold text-status-error text-xs">Tampered Chain</span>
                </div>
              )}
              <Button
                variant="outline"
                size="sm"
                className="shrink-0"
                onClick={() =>
                  navigate({ to: '/subjects/$subjectId/epochs', params: { subjectId } })
                }
              >
                <Boxes className="w-3.5 h-3.5" />
                Epochs
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0"
                onClick={() =>
                  navigate({
                    to: '/integrity/repairs/new',
                    search: { subject_id: subjectId, break_seq: undefined },
                  })
                }
              >
                <Wrench className="w-3.5 h-3.5" />
                Initiate Repair
              </Button>
            </div>

            {/* Compact Stats */}
            <div className="flex flex-wrap gap-3 mb-2 text-sm">
              <span className="text-muted-foreground">
                Total Events:{' '}
                <span className="font-bold text-foreground">{verification.total_events}</span>
              </span>
              <span className="text-muted-foreground">
                Valid Events:{' '}
                <span className="font-bold text-status-ok">{verification.valid_events}</span>
              </span>
              <span className="text-muted-foreground">
                Invalid Events:{' '}
                <span className="font-bold text-status-error">{verification.invalid_events}</span>
              </span>
              <span className="text-muted-foreground">
                Integrity:{' '}
                <span
                  className={`font-bold ${verification.is_chain_valid ? 'text-status-ok' : 'text-status-error'}`}
                >
                  {verification.total_events > 0
                    ? Math.round((verification.valid_events / verification.total_events) * 100)
                    : 0}
                  %
                </span>
              </span>
            </div>

            <p className="text-xs text-muted-foreground">Subject ID: {subjectId}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Verified: {formatFullDateTime(verification.verified_at)}
            </p>
          </div>

          {/* First break callout — roadmap: chain break location indicator */}
          {verification.events &&
            verification.events.length > 0 &&
            (() => {
              const firstInvalid = verification.events.find((e) => e.is_valid === false)
              return firstInvalid ? (
                <div className="mb-3 p-3 rounded-none border border-status-error/50 bg-status-error/10 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-status-error shrink-0" />
                  <span className="text-sm text-foreground">
                    First break at event seq{' '}
                    <Link
                      to="/subjects/$subjectId/proof/$eventSeq"
                      params={{ subjectId, eventSeq: String(firstInvalid.sequence) }}
                      className="font-mono font-semibold text-primary hover:underline"
                    >
                      {firstInvalid.sequence}
                    </Link>
                    {firstInvalid.event_id && (
                      <span className="text-muted-foreground">
                        {' '}
                        (event_id: {firstInvalid.event_id})
                      </span>
                    )}
                  </span>
                </div>
              ) : null
            })()}

          {/* Verification table: Seq, Type, Status, Hash, Error (roadmap) */}
          {verification.events && verification.events.length > 0 && (
            <div className="bg-card/80 rounded-none border border-border/50 p-3 mb-3">
              <h2 className="text-sm font-semibold text-foreground mb-2">Verification Detail</h2>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <label
                  htmlFor={statusId}
                  className="text-sm font-medium text-foreground/90 whitespace-nowrap"
                >
                  Status:
                </label>
                <SingleSelectCombobox
                  id={statusId}
                  value={filterStatus}
                  onValueChange={(v) => setFilterStatus(v === 'valid' || v === 'break' ? v : '')}
                  options={[
                    { value: '', label: 'All' },
                    { value: 'valid', label: 'Valid' },
                    { value: 'break', label: 'Break' },
                  ]}
                  placeholder="All"
                  clearable
                  className="min-w-[100px]"
                />
                {filterStatus && (
                  <span className="text-xs text-muted-foreground">
                    Showing {filteredEvents.length} of {eventsList.length} events
                  </span>
                )}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border/50 text-left text-muted-foreground font-medium">
                      <th className="py-2 pr-2">Seq</th>
                      <th className="py-2 pr-2">Type</th>
                      <th className="py-2 pr-2">Status</th>
                      <th className="py-2 pr-2">Hash</th>
                      <th className="py-2 pr-2">Error</th>
                      <th className="w-8" />
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedEvents.map((event) => (
                      <VerificationTableRow
                        key={event.event_id}
                        event={event}
                        subjectId={subjectId}
                        isExpanded={expandedEventId === event.event_id}
                        onToggle={() =>
                          setExpandedEventId((id) =>
                            id === event.event_id ? null : event.event_id,
                          )
                        }
                        onInitiateRepair={() =>
                          navigate({
                            to: '/integrity/repairs/new',
                            search: { subject_id: subjectId, break_seq: String(event.sequence) },
                          })
                        }
                        onViewProof={() =>
                          navigate({
                            to: '/subjects/$subjectId/proof/$eventSeq',
                            params: { subjectId, eventSeq: String(event.sequence) },
                          })
                        }
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredEvents.length > VERIFY_PAGE_SIZE && (
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/30">
                  <div className="text-xs text-muted-foreground">
                    Showing {detailStart + 1}–{detailEnd} of {filteredEvents.length} events
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDetailPage((p) => Math.max(0, p - 1))}
                      disabled={detailPage === 0}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </Button>
                    <span className="text-xs text-muted-foreground px-2">
                      Page {detailPage + 1} of {detailTotalPages}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDetailPage((p) => p + 1)}
                      disabled={detailPage >= detailTotalPages - 1}
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Chain Visualization (existing component) */}
          {verification.events && verification.events.length > 0 && (
            <div className="bg-card/80 rounded-none border border-border/50 p-3 mb-3">
              <h2 className="text-sm font-semibold text-foreground mb-2">Visual Chain Overview</h2>
              <ChainVisualization
                events={verification.events.map((event) => ({
                  id: event.event_id,
                  subject_id: verification.subject_id || subjectId,
                  event_type: event.event_type,
                  schema_version: 1,
                  event_time: event.event_time,
                  payload: {},
                  hash: event.actual_hash || event.expected_hash || '',
                  previous_hash: event.previous_hash ?? null,
                  verified: event.is_valid,
                  expected_hash: event.expected_hash || '',
                  actual_hash: event.actual_hash || '',
                }))}
                tamperedIndices={verification.events
                  .map((event, index) => (!event.is_valid ? index : -1))
                  .filter((i) => i !== -1)}
              />
            </div>
          )}

          {/* Invalid Events Summary */}
          {verification.invalid_events > 0 && (
            <div className="bg-destructive/10 border border-destructive/50 rounded-none p-3 mb-3">
              <h2 className="text-sm font-semibold text-destructive mb-2">
                Chain Integrity Issues ({verification.invalid_events}{' '}
                {verification.invalid_events === 1 ? 'issue' : 'issues'})
              </h2>
              <p className="text-xs text-destructive mb-2">
                {verification.invalid_events} event{verification.invalid_events !== 1 ? 's' : ''}{' '}
                failed verification. See the Visual Chain Overview above for details.
              </p>
            </div>
          )}

          {/* Export Button */}
          <div className="flex justify-center">
            <Button onClick={handleExportReport} variant="primary" size="sm">
              <DownloadIcon />
              Export Report
            </Button>
          </div>
        </>
      )}
    </>
  )
}
