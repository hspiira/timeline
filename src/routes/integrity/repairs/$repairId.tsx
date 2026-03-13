import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { SkeletonBreadcrumbs, Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/button'
import { AlertCircle, CheckCircle } from 'lucide-react'
import type { components } from '@/lib/timeline-api'
import { getApiErrorDisplay } from '@/lib/api-utils'

type ChainRepairResponse = components['schemas']['ChainRepairResponse']
type ChainRepairStatus = components['schemas']['ChainRepairStatus']

export const Route = createFileRoute('/integrity/repairs/$repairId')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: RepairDetailPage,
})

const STEPS: { key: ChainRepairStatus | 'initiated'; label: string }[] = [
  { key: 'initiated', label: 'Initiated' },
  { key: 'Pending Approval', label: 'Pending Approval' },
  { key: 'Approved', label: 'Approved' },
  { key: 'Completed', label: 'Completed' },
]

function stepIndex(status: ChainRepairStatus): number {
  switch (status) {
    case 'Pending Approval':
      return 1
    case 'Approved':
      return 2
    case 'Completed':
      return 3
    case 'Failed':
      return 0
    default:
      return 0
  }
}

function RepairDetailPage() {
  const authState = useRequireAuth()
  const { repairId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: repair, isLoading, error } = useQuery({
    queryKey: ['integrity', 'repair', repairId],
    queryFn: async () => {
      const res = await timelineApi.integrity.repair.get(repairId)
      if (res.error || !res.data) throw new Error('Failed to load repair')
      return res.data as ChainRepairResponse
    },
    enabled: !!authState.user && !!repairId,
    refetchInterval: (query) => {
      const data = query.state.data
      return data && data.repair_status !== 'Completed' && data.repair_status !== 'Failed' ? 10_000 : false
    },
  })

  const approveMutation = useMutation({
    mutationFn: () => timelineApi.integrity.repair.approve(repairId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrity', 'repair', repairId] })
    },
  })

  const completeMutation = useMutation({
    mutationFn: () => timelineApi.integrity.repair.complete(repairId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrity', 'repair', repairId] })
    },
  })

  const currentStep = repair ? stepIndex(repair.repair_status) : 0
  const isInitiator = repair && authState.user && repair.repair_initiated_by === authState.user.username
  const canApprove = repair && repair.repair_status === 'Pending Approval' && !isInitiator
  const canComplete = repair && repair.repair_status === 'Approved'

  if (!authState.user) return null

  if (isLoading) {
    return (
      <>
        <SkeletonBreadcrumbs />
        <div className="mb-3">
          <Skeleton className="h-7 w-1/3 mb-2" />
          <Skeleton className="h-24 w-full" />
        </div>
      </>
    )
  }

  if (error || !repair) {
    return (
      <>
        <Breadcrumbs items={[{ label: 'Chain Repairs', href: '/integrity/repairs' }, { label: 'Detail' }]} />
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
          <span className="text-sm text-red-800 dark:text-red-200">{error ? String(error) : 'Repair not found'}</span>
        </div>
      </>
    )
  }

  const approveError = approveMutation.error
    ? getApiErrorDisplay(
        { error: approveMutation.error as { detail?: string }, status: (approveMutation.error as { response?: { status?: number } })?.response?.status },
        'Approve failed'
      ).message
    : null

  return (
    <>
      <Breadcrumbs
        items={[
          { label: 'Chain Repairs', href: '/integrity/repairs' },
          { label: repairId.slice(0, 8) + '…' },
        ]}
      />
      <div className="mb-4">
        <h1 className="text-lg font-bold text-foreground">Chain Repair — {repairId.slice(0, 12)}…</h1>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        {STEPS.map((step, i) => {
          const done = i <= currentStep
          const isCurrent = i === currentStep
          return (
            <div key={step.key} className="flex items-center gap-2">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-none border text-xs font-medium ${
                  done ? 'bg-primary text-primary-foreground border-primary' : 'bg-muted border-border'
                } ${isCurrent ? 'ring-2 ring-primary ring-offset-2' : ''}`}
              >
                {done ? <CheckCircle className="w-4 h-4" /> : i + 1}
              </div>
              <span className={`text-sm ${done ? 'text-foreground' : 'text-muted-foreground'}`}>{step.label}</span>
              {i < STEPS.length - 1 && <span className="text-muted-foreground">→</span>}
            </div>
          )
        })}
      </div>

      {/* Read-only fields */}
      <div className="bg-card/80 rounded-none border border-border/50 p-4 mb-4 space-y-2 text-sm">
        <div className="grid grid-cols-2 gap-2">
          <span className="text-muted-foreground">Epoch</span>
          <span className="font-mono">{repair.epoch_id}</span>
          <span className="text-muted-foreground">Break at seq</span>
          <span>{repair.break_at_event_seq}</span>
          <span className="text-muted-foreground">Reason</span>
          <span>{repair.break_reason}</span>
          <span className="text-muted-foreground">Reference</span>
          <span>{repair.repair_reference ?? '—'}</span>
          <span className="text-muted-foreground">Initiated by</span>
          <span>{repair.repair_initiated_by}</span>
          <span className="text-muted-foreground">Approved by</span>
          <span>{repair.repair_approved_by ?? '—'}</span>
          {repair.repair_completed_at && (
            <>
              <span className="text-muted-foreground">Completed at</span>
              <span>{repair.repair_completed_at}</span>
            </>
          )}
          {repair.new_epoch_id && (
            <>
              <span className="text-muted-foreground">New epoch</span>
              <span className="font-mono">{repair.new_epoch_id}</span>
            </>
          )}
        </div>
      </div>

      {repair.approval_required && repair.repair_status === 'Pending Approval' && isInitiator && (
        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-none text-sm text-amber-800 dark:text-amber-200 mb-4">
          Approval required. You cannot approve your own repair. Logged in as: {authState.user.username}
        </div>
      )}

      {approveError && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none text-sm text-red-800 dark:text-red-200 mb-4">
          {approveError}
        </div>
      )}

      <div className="flex gap-2">
        {canApprove && (
          <Button
            variant="default"
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending}
          >
            Approve Repair
          </Button>
        )}
        {canComplete && (
          <Button
            variant="default"
            onClick={() => completeMutation.mutate()}
            disabled={completeMutation.isPending}
          >
            Complete Repair
          </Button>
        )}
        <Button variant="outline" onClick={() => navigate({ to: '/integrity/repairs', search: { subject_id: undefined, break_seq: undefined } })}>
          Back to list
        </Button>
      </div>
    </>
  )
}
