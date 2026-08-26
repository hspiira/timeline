import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { AlertCircle } from 'lucide-react'
import { useId, useState } from 'react'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { Button } from '@/components/ui/button'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { getTenantId, timelineApi } from '@/lib/api-client'
import { getApiErrorDisplay } from '@/lib/api-utils'
import { requireAuthBeforeLoad } from '@/lib/route-auth'

export const Route = createFileRoute('/projections/new')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: NewProjectionPage,
})

function NewProjectionPage() {
  const nameId = useId()
  const subjectTypeOptionalId = useId()
  const versionId = useId()
  useRequireAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const tenantId = getTenantId()

  const [name, setName] = useState('')
  const [version, setVersion] = useState(1)
  const [subjectType, setSubjectType] = useState('')

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!tenantId) throw new Error('No tenant selected')
      const res = await timelineApi.projections.create(tenantId, {
        name,
        version,
        subject_type: subjectType.trim() || undefined,
      })
      if (res.error || !res.data) throw res.error ?? new Error('Failed to create projection')
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projections'] })
      navigate({ to: '/projections' })
    },
  })

  const errorMessage = createMutation.error
    ? getApiErrorDisplay(
        {
          error: createMutation.error as { detail?: string },
          status: (createMutation.error as { response?: { status?: number } })?.response?.status,
        },
        'Failed to create projection',
      ).message
    : null

  if (!tenantId) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Select a tenant to create a projection.
      </div>
    )
  }

  return (
    <>
      <Breadcrumbs
        items={[{ label: 'Projections', href: '/projections' }, { label: 'New Projection' }]}
      />
      <div className="max-w-lg">
        <h1 className="text-lg font-bold text-foreground mb-4">New Projection</h1>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (name.trim()) createMutation.mutate()
          }}
          className="space-y-4"
        >
          <div>
            <label htmlFor={nameId} className="block text-sm font-medium text-foreground mb-1">
              Name *
            </label>
            <input
              id={nameId}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. user-activity-summary"
              className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
              required
            />
          </div>
          <div>
            <label htmlFor={versionId} className="block text-sm font-medium text-foreground mb-1">
              Version *
            </label>
            <input
              id={versionId}
              type="number"
              min={1}
              value={version}
              onChange={(e) => setVersion(Number(e.target.value) || 1)}
              className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
            />
          </div>
          <div>
            <label
              htmlFor={subjectTypeOptionalId}
              className="block text-sm font-medium text-foreground mb-1"
            >
              Subject type (optional)
            </label>
            <input
              id={subjectTypeOptionalId}
              type="text"
              value={subjectType}
              onChange={(e) => setSubjectType(e.target.value)}
              placeholder="e.g. user"
              className="w-full px-3 py-2 rounded-none border border-border bg-background text-foreground text-sm"
            />
          </div>
          {errorMessage && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex items-center gap-2 text-sm text-red-800 dark:text-red-200">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {errorMessage}
            </div>
          )}
          <div className="flex gap-2">
            <Button type="submit" disabled={createMutation.isPending || !name.trim()}>
              Create
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate({ to: '/projections' })}
            >
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </>
  )
}
