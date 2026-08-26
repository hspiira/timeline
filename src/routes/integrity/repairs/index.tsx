import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useEffect, useCallback } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { timelineApi } from '@/lib/api-client'
import { formatDateTimeSafe } from '@/lib/format-date'
import { DataTable } from '@/components/ui/DataTable'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Button } from '@/components/ui/button'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { Wrench, ChevronLeft, ChevronRight, Loader2, AlertCircle } from 'lucide-react'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/integrity/repairs/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  validateSearch: (search: Record<string, unknown>): { subject_id: string | undefined; break_seq: string | undefined } => ({
    subject_id: typeof search.subject_id === 'string' ? search.subject_id : undefined,
    break_seq: typeof search.break_seq === 'string' ? search.break_seq : undefined,
  }),
  component: RepairsPage,
})

type ChainRepair = components['schemas']['ChainRepairResponse']
type ChainRepairStatus = components['schemas']['ChainRepairStatus']

const PAGE_SIZE = 20
const REPAIR_STATUSES: ChainRepairStatus[] = ['Pending Approval', 'Approved', 'Completed', 'Failed']

/** API statuses are display text ("Pending Approval"); toStatusKind wants snake_case. */
function statusToken(status: ChainRepairStatus): string {
  return status.toLowerCase().replace(/\s+/g, '_')
}

function RepairsPage() {
  const authState = useRequireAuth()
  const navigate = useNavigate()
  const { subject_id, break_seq } = Route.useSearch()
  const [skip, setSkip] = useState(0)
  const [status, setStatus] = useState<ChainRepairStatus | ''>('')

  const fetchRepairs = useCallback(async () => {
    const res = await timelineApi.integrity.repair.list({
      skip,
      limit: PAGE_SIZE,
      repair_status: status || undefined,
    })
    if (res.error != null) {
      return { error: res.error, response: res.response }
    }
    return {
      data: {
        items: res.data?.items ?? [],
        total: res.data?.total ?? 0,
      },
    }
  }, [skip, status])

  const {
    data: fetched,
    error,
    loading,
    hasNoAccess,
    refetch,
  } = useFetchWithError<{ items: ChainRepair[]; total: number }>(fetchRepairs, {
    defaultErrorMessage: 'Unable to load chain repairs',
    enabled: !!authState.user,
  })

  useEffect(() => {
    if (authState.user) refetch()
  }, [authState.user, refetch, skip, status])

  const items = fetched?.items ?? []
  const total = fetched?.total ?? 0
  const hasMore = skip + items.length < total

  if (!authState.user) {
    return null
  }

  if (hasNoAccess) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-foreground mb-2">Access denied</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          You do not have permission to view chain repairs. Contact your administrator if you
          need access.
        </p>
      </div>
    )
  }

  const columns: ColumnDef<ChainRepair>[] = [
    {
      accessorKey: 'repair_status',
      header: 'Status',
      cell: ({ row }) => (
        <StatusBadge
          status={statusToken(row.original.repair_status)}
          label={row.original.repair_status}
        />
      ),
    },
    {
      accessorKey: 'break_at_event_seq',
      header: 'Break at',
      cell: ({ row }) => (
        <span className="text-sm font-mono">#{row.original.break_at_event_seq}</span>
      ),
    },
    {
      accessorKey: 'break_reason',
      header: 'Reason',
      cell: ({ row }) => (
        <span className="text-sm truncate max-w-[280px] block" title={row.original.break_reason}>
          {row.original.break_reason}
        </span>
      ),
    },
    {
      accessorKey: 'epoch_id',
      header: 'Epoch',
      cell: ({ row }) => (
        <span className="text-sm font-mono truncate max-w-[120px] block" title={row.original.epoch_id}>
          {row.original.epoch_id}
        </span>
      ),
    },
    {
      accessorKey: 'repair_approved_by',
      header: 'Approved by',
      cell: ({ row }) => (
        <span className="text-sm font-mono">{row.original.repair_approved_by ?? '—'}</span>
      ),
    },
    {
      accessorKey: 'repair_completed_at',
      header: 'Completed',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {row.original.repair_completed_at
            ? formatDateTimeSafe(row.original.repair_completed_at)
            : '—'}
        </span>
      ),
    },
    {
      id: 'open',
      header: '',
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            navigate({
              to: '/integrity/repairs/$repairId',
              params: { repairId: row.original.id },
            })
          }
        >
          Open
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
            <Wrench className="w-5 h-5" />
            Chain repairs
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Repairs awaiting approval, in progress, and completed. Filter by status to find
            what needs your sign-off.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() =>
            navigate({ to: '/integrity/repairs/new', search: { subject_id, break_seq } })
          }
        >
          Initiate repair
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-3 p-4 rounded-lg border border-border bg-muted/30">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">Status</label>
          <SingleSelectCombobox
            value={status || 'all'}
            onValueChange={(v) => {
              setStatus(v === 'all' ? '' : (v as ChainRepairStatus))
              setSkip(0)
            }}
            options={[
              { value: 'all', label: 'All' },
              ...REPAIR_STATUSES.map((s) => ({ value: s, label: s })),
            ]}
            placeholder="Status"
            className="w-[180px]"
          />
        </div>
        {status && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatus('')
              setSkip(0)
            }}
          >
            Clear filter
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="w-8 h-8 animate-spin mr-2" />
          Loading chain repairs…
        </div>
      ) : (
        <>
          <DataTable
            data={items}
            columns={columns}
            isLoading={false}
            isEmpty={items.length === 0}
            emptyState={{
              title: 'No chain repairs',
              description: status
                ? `No repairs with status “${status}”.`
                : 'No repairs have been initiated. Start one from a subject’s Verify page, or use Initiate repair above.',
            }}
            variant="default"
            compact
          />

          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              {total === 0
                ? 'No records'
                : `Showing ${skip + 1}–${skip + items.length} of ${total}`}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSkip((s) => Math.max(0, s - PAGE_SIZE))}
                disabled={skip === 0 || loading}
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSkip((s) => s + PAGE_SIZE)}
                disabled={!hasMore || loading}
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
