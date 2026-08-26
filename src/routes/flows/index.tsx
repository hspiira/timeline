import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { AlertCircle, GitBranch, Plus } from 'lucide-react'
import { useState } from 'react'
import { FlowsTable } from '@/components/flows/FlowsTable'
import { Button } from '@/components/ui/button'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { timelineApi } from '@/lib/api-client'
import { requireAuthBeforeLoad } from '@/lib/route-auth'

export const Route = createFileRoute('/flows/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: FlowsPage,
})

function FlowsPage() {
  const navigate = useNavigate()
  const [workflowFilter, setWorkflowFilter] = useState<string>('')

  const {
    data: flows = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['flows', workflowFilter || null],
    queryFn: async () => {
      const { data, error: apiError } = await timelineApi.flows.list({
        skip: 0,
        limit: 500,
        workflow_id: workflowFilter || null,
      })
      if (apiError) throw new Error('Failed to load flows')
      return Array.isArray(data) ? data : []
    },
  })

  const { data: workflows = [] } = useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const { data, error: apiError } = await timelineApi.workflows.list({
        limit: 500,
      })
      if (apiError) return []
      return Array.isArray(data) ? data : []
    },
  })

  const workflowOptions = [
    { value: '', label: 'All workflows' },
    ...workflows.map((w) => ({ value: w.id, label: w.name || w.id })),
  ]

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-28" />
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-none border border-border/50" />
          ))}
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Unable to load flows"
        description={error?.message ?? 'An unexpected error occurred.'}
      />
    )
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground mb-1">Flows</h1>
          <p className="text-sm text-muted-foreground">
            Workflow instances with subjects and document compliance
          </p>
        </div>
        <Link to="/flows/create">
          <Button>
            <Plus className="w-4 h-4" />
            New flow
          </Button>
        </Link>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <label className="text-sm font-medium text-foreground/90">Workflow:</label>
        <SingleSelectCombobox
          value={workflowFilter}
          onValueChange={setWorkflowFilter}
          options={workflowOptions}
          placeholder="All workflows"
          clearable
          className="w-56"
        />
      </div>

      {flows.length === 0 ? (
        <div className="bg-card/80 backdrop-blur-sm rounded-none border border-border/50">
          <EmptyState
            icon={GitBranch}
            title={workflowFilter ? 'No flows match' : 'No flows yet'}
            description={
              workflowFilter
                ? 'Try a different workflow filter'
                : 'Create a flow to group subjects and track document compliance'
            }
            action={
              !workflowFilter
                ? {
                    label: 'New flow',
                    onClick: () => navigate({ to: '/flows/create' }),
                  }
                : undefined
            }
          />
        </div>
      ) : (
        <FlowsTable flows={flows} workflows={workflows} />
      )}
    </>
  )
}
