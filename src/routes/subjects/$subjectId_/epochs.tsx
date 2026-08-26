import { useQuery } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { AlertCircle, FileCheck } from 'lucide-react'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Button } from '@/components/ui/button'
import { Skeleton, SkeletonBreadcrumbs } from '@/components/ui/Skeleton'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { formatFullDateTime } from '@/lib/format-date'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import type { components } from '@/lib/timeline-api'

type IntegrityEpochItem = components['schemas']['IntegrityEpochItem']

export const Route = createFileRoute('/subjects/$subjectId_/epochs')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: EpochsPage,
})

function EpochsPage() {
  const authState = useRequireAuth()
  const { subjectId } = Route.useParams()
  const navigate = useNavigate()

  const {
    data: epochs = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['integrity', 'epochs', subjectId],
    queryFn: async () => {
      const res = await timelineApi.integrity.listEpochs(subjectId)
      if (res.error || !res.data) throw new Error('Failed to load epochs')
      return res.data
    },
    enabled: !!authState.user && !!subjectId,
  })

  const statusLabel = (status: string) => {
    switch (status) {
      case 'Open':
        return 'OPEN'
      case 'Sealed':
        return 'SEALED'
      case 'Broken':
        return 'BROKEN'
      case 'Repaired':
        return 'REPAIRED'
      case 'Failed':
        return 'FAILED'
      default:
        return status
    }
  }

  if (!authState.user) return null

  if (isLoading) {
    return (
      <>
        <SkeletonBreadcrumbs />
        <div className="mb-3">
          <Skeleton className="h-7 w-1/3 mb-2" />
          <Skeleton className="h-20 w-full" />
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <Breadcrumbs
          items={[
            { label: 'Subjects', href: '/subjects' },
            { label: `${subjectId.slice(0, 8)}...`, href: `/subjects/${subjectId}` },
            { label: 'Epochs' },
          ]}
        />
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
          <span className="text-sm text-red-800 dark:text-red-200">{String(error)}</span>
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
          { label: 'Epochs' },
        ]}
      />
      <div className="mb-3">
        <h1 className="text-lg font-bold text-foreground">
          Epochs — {subjectId.slice(0, 12)}
          {subjectId.length > 12 ? '…' : ''}
        </h1>
      </div>

      <div className="bg-card/80 rounded-none border border-border/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-border/50 bg-muted/30 text-left text-muted-foreground font-medium">
                <th className="py-2 px-3">#</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Events</th>
                <th className="py-2 px-3">Opened</th>
                <th className="py-2 px-3">Sealed</th>
                <th className="py-2 px-3">Merkle</th>
                <th className="py-2 px-3 w-24" />
              </tr>
            </thead>
            <tbody>
              {epochs.map((epoch: IntegrityEpochItem) => (
                <tr key={epoch.id} className="border-b border-border/30 hover:bg-muted/20">
                  <td className="py-2 px-3 font-mono">{epoch.epoch_number}</td>
                  <td className="py-2 px-3">{statusLabel(epoch.status)}</td>
                  <td className="py-2 px-3">{epoch.event_count}</td>
                  <td className="py-2 px-3 text-muted-foreground">
                    {formatFullDateTime(epoch.opened_at)}
                  </td>
                  <td className="py-2 px-3 text-muted-foreground">
                    {epoch.sealed_at ? formatFullDateTime(epoch.sealed_at) : '—'}
                  </td>
                  <td className="py-2 px-3">
                    {epoch.merkle_root ? (
                      <span className="text-green-600 dark:text-green-400">✓ root</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="py-2 px-3">
                    {(epoch.status === 'Sealed' || epoch.status === 'Repaired') &&
                      epoch.merkle_root && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            navigate({ to: '/verify/$subjectId', params: { subjectId } })
                          }
                        >
                          <FileCheck className="w-3.5 h-3.5" />
                          View Proof
                        </Button>
                      )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {epochs.length === 0 && (
          <div className="py-8 text-center text-muted-foreground text-sm">
            No epochs for this subject.
          </div>
        )}
      </div>
    </>
  )
}
