import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { EmptyState } from '@/components/ui/EmptyState'
import { Wrench } from 'lucide-react'

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

function RepairsPage() {
  useRequireAuth()
  const navigate = useNavigate()
  const { subject_id, break_seq } = Route.useSearch()

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-foreground">Chain Repairs</h1>
      <EmptyState
        icon={Wrench}
        title="Repair list"
        description="Initiate and manage chain repairs. Use the button below to start a new repair, or go to a subject's Verify page and use Initiate Repair from there."
        action={{
          label: 'Initiate repair',
          onClick: () => navigate({ to: '/integrity/repairs/new', search: { subject_id, break_seq } }),
        }}
      />
    </div>
  )
}
