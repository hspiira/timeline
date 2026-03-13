import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { getApiErrorDisplay } from '@/lib/api-utils'

export const Route = createFileRoute('/integrity/repairs/new')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  validateSearch: (search: Record<string, unknown>): { subject_id: string | undefined; break_seq: string | undefined } => ({
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

  const [epochId, setEpochId] = useState('')
  const [breakAtEventSeq, setBreakAtEventSeq] = useState(break_seq ? Number(break_seq) : 0)
  const [breakReason, setBreakReason] = useState(
    break_seq ? `Hash mismatch detected on event seq ${break_seq}` : ''
  )
  const [repairReference, setRepairReference] = useState('')

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
        'Failed to initiate repair'
      ).message
    : null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!epochId.trim() || !breakReason.trim()) return
    createMutation.mutate()
  }

  return (
    <>
      <Breadcrumbs
        items={[
          { label: 'Chain Repairs', href: '/integrity/repairs' },
          { label: 'Initiate Repair' },
        ]}
      />
      <div className="max-w-lg">
        <h1 className="text-lg font-bold text-foreground mb-4">Initiate Chain Repair</h1>

        {subject_id && (
          <p className="text-sm text-muted-foreground mb-4">
            Subject: {subject_id.slice(0, 12)}…{break_seq != null ? ` · Break at seq: ${break_seq}` : ''}
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
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
            <label className="block text-sm font-medium text-foreground mb-1">Break at event seq *</label>
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

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Reference (for LEGAL_GRADE)</label>
            <input
              type="text"
              value={repairReference}
              onChange={(e) => setRepairReference(e.target.value)}
              placeholder="e.g. INC-2024-001"
              className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
            />
          </div>

          {errorMessage && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex items-center gap-2 text-sm text-red-800 dark:text-red-200">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {errorMessage}
            </div>
          )}

          <p className="text-xs text-muted-foreground">Approval will be required from a second user.</p>

          <div className="flex gap-2">
            <Button type="submit" disabled={createMutation.isPending || !epochId.trim() || !breakReason.trim()}>
              Initiate Repair
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate({ to: '/integrity/repairs' })}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </>
  )
}
