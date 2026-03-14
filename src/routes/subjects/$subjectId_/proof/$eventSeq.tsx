import { createFileRoute } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { SkeletonBreadcrumbs, Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/button'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { AlertCircle, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import type { components } from '@/lib/timeline-api'
import { MerkleProofTree } from '@/components/verify/MerkleProofTree'

type MerkleProofResponse = components['schemas']['MerkleProofResponse']

export const Route = createFileRoute('/subjects/$subjectId_/proof/$eventSeq')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: ProofPage,
})

function ProofPage() {
  const authState = useRequireAuth()
  const { subjectId, eventSeq } = Route.useParams()
  const eventSeqNum = Number(eventSeq)
  const [copied, setCopied] = useState(false)

  const { data: proof, isLoading, error } = useQuery({
    queryKey: ['integrity', 'proof', eventSeqNum],
    queryFn: async () => {
      const res = await timelineApi.integrity.getProof(eventSeqNum)
      if (res.error || !res.data) {
        const status = (res as { response?: { status?: number } }).response?.status
        if (status === 400) {
          throw new Error('Proof not available: event is not in a sealed LEGAL_GRADE epoch.')
        }
        throw new Error('Failed to load proof')
      }
      return res.data as MerkleProofResponse
    },
    enabled: !!authState.user && !Number.isNaN(eventSeqNum),
  })

  const copyProofJson = () => {
    if (!proof) return
    navigator.clipboard.writeText(JSON.stringify(proof, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const truncate = (s: string, n = 16) => (s.length <= n ? s : `${s.slice(0, n)}…`)

  if (!authState.user) return null

  if (isLoading) {
    return (
      <>
        <SkeletonBreadcrumbs />
        <div className="mb-3">
          <Skeleton className="h-7 w-1/3 mb-2" />
          <Skeleton className="h-40 w-full" />
        </div>
      </>
    )
  }

  if (error || !proof) {
    return (
      <>
        <Breadcrumbs
          items={[
            { label: 'Subjects', href: '/subjects' },
            { label: `${subjectId.slice(0, 8)}...`, href: `/subjects/${subjectId}` },
            { label: 'Proof' },
          ]}
        />
        <div className="p-3 bg-destructive/10 border border-destructive/50 rounded-none flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error ? String(error) : 'Proof not found'}
        </div>
      </>
    )
  }

  return (
    <>
      <Breadcrumbs
        items={[
          { label: 'Subjects', href: '/subjects' },
          { label: `${subjectId.slice(0, 8)}...`, href: `/subjects/${subjectId}` },
          { label: `Proof seq:${proof.event_seq}` },
        ]}
      />
      <div className="mb-3 flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-lg font-bold text-foreground">
          Merkle Proof — seq:{proof.event_seq}
        </h1>
        <Button variant="outline" size="sm" onClick={copyProofJson}>
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          Copy Proof JSON
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="bg-card/80 rounded-none border border-border/50 p-3">
          <MerkleProofTree proof={proof} className="mb-4" />
          <h2 className="text-sm font-semibold text-foreground mb-2">Proof path (steps)</h2>
          <div className="space-y-1 font-mono text-xs">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground shrink-0">Leaf:</span>
              <code className="break-all">{truncate(proof.leaf_hash, 24)}</code>
            </div>
            {proof.steps.map((step, i) => (
              <div key={i} className="flex items-center gap-2 pl-4">
                <span className="text-muted-foreground shrink-0">
                  Step {i + 1} — {step.is_left_sibling ? 'left' : 'right'} sibling:
                </span>
                <code className="break-all">{truncate(step.sibling_hash, 24)}</code>
              </div>
            ))}
            <div className="flex items-center gap-2 pt-2 border-t border-border/30">
              <span className="text-muted-foreground shrink-0">Root:</span>
              <code className="break-all text-status-ok">{truncate(proof.root_hash, 24)}</code>
            </div>
          </div>
        </div>

        <div className="bg-card/80 rounded-none border border-border/50 p-3">
          <h2 className="text-sm font-semibold text-foreground mb-2">Details</h2>
          <dl className="space-y-1 text-sm">
            <div>
              <dt className="text-muted-foreground">Epoch ID</dt>
              <dd className="font-mono text-xs">{proof.epoch_id}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Event seq</dt>
              <dd>{proof.event_seq}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Subject ID</dt>
              <dd className="font-mono text-xs break-all">{proof.subject_id}</dd>
            </div>
            {proof.tsa_anchor_id && (
              <div>
                <dt className="text-muted-foreground mb-1">TSA anchor</dt>
                <dd className="flex items-center gap-2">
                  <code className="font-mono text-xs break-all bg-muted/50 px-2 py-1 rounded-none border border-border/50">
                    {proof.tsa_anchor_id}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 shrink-0"
                    onClick={() => {
                      navigator.clipboard.writeText(proof.tsa_anchor_id ?? '')
                      setCopied(true)
                      setTimeout(() => setCopied(false), 2000)
                    }}
                    title="Copy TSA anchor"
                  >
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </Button>
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </>
  )
}
