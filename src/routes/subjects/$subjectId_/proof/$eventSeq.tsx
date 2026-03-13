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
      if (res.error || !res.data) throw new Error('Failed to load proof')
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
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
          <span className="text-sm text-red-800 dark:text-red-200">{error ? String(error) : 'Proof not found'}</span>
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
          <h2 className="text-sm font-semibold text-foreground mb-2">Proof path</h2>
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
              <code className="break-all text-green-600 dark:text-green-400">{truncate(proof.root_hash, 24)}</code>
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
                <dt className="text-muted-foreground">TSA anchor</dt>
                <dd className="font-mono text-xs">{proof.tsa_anchor_id}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </>
  )
}
