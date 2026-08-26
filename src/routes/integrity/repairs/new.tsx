import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { AlertCircle, ChevronRight, FileWarning } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Button } from '@/components/ui/button'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorDisplay } from '@/lib/api-utils'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import type { components } from '@/lib/timeline-api'
import { cn } from '@/lib/utils'

type IntegrityVerificationDetail = components['schemas']['IntegrityVerificationDetail']

export const Route = createFileRoute('/integrity/repairs/new')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  validateSearch: (
    search: Record<string, unknown>,
  ): { subject_id: string | undefined; break_seq: string | undefined } => ({
    subject_id: typeof search.subject_id === 'string' ? search.subject_id : undefined,
    break_seq: typeof search.break_seq === 'string' ? search.break_seq : undefined,
  }),
  component: NewRepairPage,
})

function NewRepairPage() {
  useRequireAuth()
  const { subject_id, break_seq } = Route.useSearch()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [step, setStep] = useState<1 | 2>(1)
  const [epochId, setEpochId] = useState('')
  const [breakAtEventSeq, setBreakAtEventSeq] = useState(break_seq ? Number(break_seq) : 0)
  const [breakReason, setBreakReason] = useState(
    break_seq ? `Hash mismatch detected on event seq ${break_seq}` : '',
  )
  const [repairReference, setRepairReference] = useState('')
  const [requiresLegalReference, setRequiresLegalReference] = useState(false)
  const [detectedBreakSeq, setDetectedBreakSeq] = useState<number | null>(null)
  const prefillFromVerifyDone = useRef(false)

  const { data: verification } = useQuery({
    queryKey: ['integrity', 'verify-detail', subject_id ?? ''],
    queryFn: async (): Promise<IntegrityVerificationDetail | null> => {
      if (!subject_id) return null
      const res = await timelineApi.integrity.verifySubjectDetail(subject_id)
      if (res.error || !res.data) return null
      return res.data as IntegrityVerificationDetail
    },
    enabled: !!subject_id && break_seq == null,
  })

  useEffect(() => {
    if (prefillFromVerifyDone.current || break_seq != null || !verification?.events?.length) return
    const firstInvalid = verification.events.find((e) => e.is_valid === false)
    if (firstInvalid != null) {
      setBreakAtEventSeq(firstInvalid.sequence)
      setBreakReason(`Hash mismatch detected on event seq ${firstInvalid.sequence}`)
      setDetectedBreakSeq(firstInvalid.sequence)
      prefillFromVerifyDone.current = true
    }
  }, [verification, break_seq])

  const { data: epochs = [] } = useQuery({
    queryKey: ['integrity', 'epochs', subject_id ?? ''],
    queryFn: async () => {
      if (!subject_id) return []
      const res = await timelineApi.integrity.listEpochs(subject_id)
      if (res.error || !res.data) return []
      return res.data
    },
    enabled: !!subject_id,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await timelineApi.integrity.repair.initiate({
        epoch_id: epochId,
        break_at_event_seq: breakAtEventSeq,
        break_reason: breakReason,
        repair_reference: repairReference || undefined,
      })
      if (res.error || !res.data) throw res.error ?? new Error('Failed to initiate repair')
      return res.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['integrity'] })
      navigate({ to: '/integrity/repairs/$repairId', params: { repairId: data.id } })
    },
  })

  const errorMessage = createMutation.error
    ? getApiErrorDisplay(
        {
          error: createMutation.error as { detail?: string },
          status: (createMutation.error as { response?: { status?: number } })?.response?.status,
        },
        'Failed to initiate repair',
      ).message
    : null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!epochId.trim() || !breakReason.trim()) return
    if (requiresLegalReference && !repairReference.trim()) return
    createMutation.mutate()
  }

  const referenceError = requiresLegalReference && !repairReference.trim()

  const canProceedStep1 = epochId.trim() && breakReason.trim() && breakAtEventSeq >= 0

  return (
    <>
      <Breadcrumbs
        items={[
          { label: 'Chain Repairs', href: '/integrity/repairs' },
          { label: 'Initiate Repair' },
        ]}
      />
      <div className="max-w-lg">
        <h1 className="text-lg font-bold text-foreground mb-2">Initiate Chain Repair</h1>
        <p className="text-sm text-muted-foreground mb-4">
          Repair creates a new integrity epoch and an admin event. A second user must approve before
          the repair is completed.
        </p>

        {/* Stepper */}
        <div className="flex items-center gap-2 mb-6">
          <button
            type="button"
            onClick={() => setStep(1)}
            className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded-none text-sm font-medium transition-colors',
              step === 1
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted',
            )}
          >
            1. Context
          </button>
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
          <button
            type="button"
            onClick={() => canProceedStep1 && setStep(2)}
            className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded-none text-sm font-medium transition-colors',
              step === 2
                ? 'bg-primary text-primary-foreground'
                : canProceedStep1
                  ? 'bg-muted/50 text-muted-foreground hover:bg-muted'
                  : 'bg-muted/30 text-muted-foreground cursor-not-allowed',
            )}
          >
            2. Initiate
          </button>
        </div>

        {subject_id && (
          <div className="p-3 mb-4 rounded-none border border-border/50 bg-muted/20 flex items-start gap-2">
            <FileWarning className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-foreground">Break context</p>
              <p className="text-muted-foreground mt-0.5">
                Subject: {subject_id.slice(0, 12)}…{subject_id.length > 12 ? '' : ''}
                {break_seq != null && ` · Break at seq: ${break_seq}`}
                {detectedBreakSeq != null && break_seq == null && (
                  <> · Detected first break at seq {detectedBreakSeq} (override below if needed)</>
                )}
              </p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {step === 1 && (
            <>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Epoch ID *</label>
                {subject_id && epochs.length > 0 ? (
                  <select
                    value={epochId}
                    onChange={(e) => setEpochId(e.target.value)}
                    className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
                    required
                  >
                    <option value="">Select epoch</option>
                    {epochs.map((ep) => (
                      <option key={ep.id} value={ep.id}>
                        #{ep.epoch_number} — {ep.status} ({ep.event_count} events)
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={epochId}
                    onChange={(e) => setEpochId(e.target.value)}
                    placeholder="epoch-..."
                    className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
                    required
                  />
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Break at event seq *
                </label>
                <input
                  type="number"
                  min={1}
                  value={breakAtEventSeq || ''}
                  onChange={(e) => setBreakAtEventSeq(Number(e.target.value) || 0)}
                  className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Reason *</label>
                <textarea
                  value={breakReason}
                  onChange={(e) => setBreakReason(e.target.value)}
                  placeholder="e.g. Hash mismatch detected on event seq …"
                  rows={3}
                  className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
                  required
                />
              </div>

              <div className="flex gap-2">
                <Button
                  type="button"
                  onClick={() => canProceedStep1 && setStep(2)}
                  disabled={!canProceedStep1}
                >
                  Next: Initiate
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    navigate({
                      to: '/integrity/repairs',
                      search: { subject_id: undefined, break_seq: undefined },
                    })
                  }
                >
                  Cancel
                </Button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div className="p-3 rounded-none border border-border/50 bg-muted/20 text-sm text-muted-foreground">
                Epoch: {epochId.slice(0, 20)}… · Break at seq: {breakAtEventSeq} ·{' '}
                {breakReason.slice(0, 60)}
                {breakReason.length > 60 ? '…' : ''}
              </div>

              <div className="flex items-center gap-2 mb-2">
                <input
                  type="checkbox"
                  id="legal-grade"
                  checked={requiresLegalReference}
                  onChange={(e) => setRequiresLegalReference(e.target.checked)}
                  className="rounded border-border"
                />
                <label htmlFor="legal-grade" className="text-sm font-medium text-foreground">
                  Requires legal reference (LEGAL_GRADE)
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Reference {requiresLegalReference && '*'}
                </label>
                <input
                  type="text"
                  value={repairReference}
                  onChange={(e) => setRepairReference(e.target.value)}
                  placeholder="e.g. INC-2024-001"
                  className={`w-full px-3 py-2 rounded-none border bg-background text-foreground text-sm ${referenceError ? 'border-destructive' : 'border-border'}`}
                />
                {referenceError && (
                  <p className="mt-1 text-xs text-destructive">
                    Reference is required for LEGAL_GRADE repairs.
                  </p>
                )}
              </div>

              {errorMessage && (
                <div className="p-3 bg-destructive/10 border border-destructive/50 rounded-none flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {errorMessage}
                </div>
              )}

              <p className="text-xs text-muted-foreground">
                Approval will be required from a second user.
              </p>

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createMutation.isPending ||
                    !epochId.trim() ||
                    !breakReason.trim() ||
                    referenceError
                  }
                >
                  Initiate Repair
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    navigate({
                      to: '/integrity/repairs',
                      search: { subject_id: undefined, break_seq: undefined },
                    })
                  }
                >
                  Cancel
                </Button>
              </div>
            </>
          )}
        </form>
      </div>
    </>
  )
}
