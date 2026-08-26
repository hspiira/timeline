import { createFileRoute, Link } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { CheckCircle, FileCheck, Network, Pause, Play, Plus, SquarePen, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { DataTable } from '@/components/ui/DataTable'
import { ErrorModal } from '@/components/ui/ErrorModal'
import { ErrorIcon, LoadingIcon } from '@/components/ui/icons'
import { WorkflowDocumentRequirementsModal } from '@/components/workflows/WorkflowDocumentRequirementsModal'
import { WorkflowEditModal } from '@/components/workflows/WorkflowEditModal'
import { WorkflowRequirementsModal } from '@/components/workflows/WorkflowRequirementsModal'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import type { components } from '@/lib/timeline-api'
export const Route = createFileRoute('/settings/workflows/')({
  component: WorkflowsPage,
})

type Workflow = components['schemas']['WorkflowResponse']
type WorkflowCreate = components['schemas']['WorkflowCreateRequest']
type WorkflowUpdate = components['schemas']['WorkflowUpdate']

function WorkflowsPage() {
  const filterByTriggerId = useId()
  const authState = useRequireAuth()
  const toast = useToast()
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [eventTypes, setEventTypes] = useState<string[]>([])
  const fetchWorkflowsAndTypes = useCallback(async () => {
    const result = await timelineApi.workflows.list()
    if (result.error != null) {
      return { error: result.error, response: result.response }
    }
    if (result.data) {
      const schemaRes = await timelineApi.eventSchemas.list({ limit: 500 })
      const schemaList = Array.isArray(schemaRes.data) ? schemaRes.data : []
      const types: string[] = [
        ...new Set(schemaList.map((s) => s.event_type).filter((x): x is string => Boolean(x))),
      ]
      return { data: { workflows: result.data, eventTypes: types } }
    }
    return {}
  }, [])

  const {
    data: fetchedData,
    error,
    loading,
    hasNoAccess,
    refetch,
    setError,
  } = useFetchWithError<{ workflows: Workflow[]; eventTypes: string[] }>(fetchWorkflowsAndTypes, {
    defaultErrorMessage: 'Failed to load workflows',
    enabled: !!authState.user,
  })

  useEffect(() => {
    if (authState.user) refetch()
  }, [authState.user, refetch])

  useEffect(() => {
    if (fetchedData) {
      setWorkflows(fetchedData.workflows)
      setEventTypes(fetchedData.eventTypes)
    }
  }, [fetchedData])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [toggling, setToggling] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; name: string } | null>(
    null,
  )
  const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null)
  const [documentRequirementsWorkflow, setDocumentRequirementsWorkflow] = useState<Workflow | null>(
    null,
  )
  const [filterEventType, setFilterEventType] = useState<string>('')

  const handleCreateWorkflow = async (workflowData: WorkflowCreate): Promise<boolean> => {
    if (hasNoAccess) {
      setError('You do not have permission to create workflows')
      return false
    }
    try {
      const { data, error: apiError } = await timelineApi.workflows.create(workflowData)
      if (apiError) return false
      if (data) {
        setWorkflows((prev) => [data, ...prev])
        setShowCreateModal(false)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const handleUpdateWorkflow = async (
    workflowId: string,
    data: WorkflowUpdate,
  ): Promise<boolean> => {
    if (hasNoAccess) return false
    try {
      const { error: apiError } = await timelineApi.workflows.update(workflowId, data)
      if (apiError) return false
      setWorkflows((prev) =>
        prev.map((w) =>
          w.id === workflowId
            ? {
                ...w,
                ...data,
                name: data.name ?? w.name,
                description: data.description ?? w.description,
                execution_order: data.execution_order ?? w.execution_order,
                is_active: data.is_active ?? w.is_active,
              }
            : w,
        ),
      )
      setEditingWorkflow(null)
      toast.success('Workflow updated', 'Changes saved successfully')
      return true
    } catch {
      return false
    }
  }

  const handleToggleWorkflow = async (workflowId: string, currentState: boolean) => {
    if (hasNoAccess) {
      toast.error('Permission denied', 'You do not have permission to update workflows')
      return
    }

    setToggling(workflowId)
    try {
      const { error: apiError } = await timelineApi.workflows.update(workflowId, {
        is_active: !currentState,
      })

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'message' in apiError
            ? (apiError as any).message
            : 'Failed to update workflow'
        setError(errorMsg)
        toast.error('Failed to update', errorMsg)
      } else {
        setWorkflows((prev) =>
          prev.map((w) => (w.id === workflowId ? { ...w, is_active: !currentState } : w)),
        )
        toast.success(
          'Workflow updated',
          `Workflow has been ${!currentState ? 'activated' : 'deactivated'}`,
        )
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to update workflow'
      setError(errorMsg)
      toast.error('Error updating', errorMsg)
    } finally {
      setToggling(null)
    }
  }

  const handleDeleteClick = (workflowId: string, workflowName: string) => {
    if (hasNoAccess) {
      toast.error('Permission denied', 'You do not have permission to delete workflows')
      return
    }
    setConfirmingDelete({ id: workflowId, name: workflowName })
  }

  const handleConfirmDelete = async () => {
    if (!confirmingDelete) return

    const { id: workflowId, name: workflowName } = confirmingDelete
    setDeleting(workflowId)

    try {
      const { error: apiError } = await timelineApi.workflows.delete(workflowId)

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'message' in apiError
            ? (apiError as any).message
            : 'Failed to delete workflow'
        setError(errorMsg)
        toast.error('Failed to delete', errorMsg)
        throw new Error(errorMsg)
      }

      setWorkflows((prev) => prev.filter((w) => w.id !== workflowId))
      toast.success('Workflow deleted', `"${workflowName}" has been deleted`)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete workflow'
      setError(errorMsg)
      toast.error('Error deleting', errorMsg)
      throw err
    } finally {
      setDeleting(null)
    }
  }

  if (!authState.user) {
    return null
  }

  // Define columns for DataTable
  const columns: ColumnDef<Workflow>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => <span className="font-medium text-foreground">{row.original.name}</span>,
    },
    {
      id: 'trigger_event',
      header: 'Trigger Event',
      cell: ({ row }) => {
        const triggerEventType = row.original.trigger_event_type || 'N/A'
        return (
          <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-none font-mono">
            {triggerEventType}
          </span>
        )
      },
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) =>
        row.original.is_active ? (
          <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span className="text-xs">Active</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">Inactive</span>
        ),
    },
    {
      id: 'action_count',
      header: 'Actions',
      cell: ({ row }) => {
        const actionsCount = (row.original as any).actions?.length || 0
        return (
          <span className="text-muted-foreground text-sm">
            {actionsCount} action{actionsCount !== 1 ? 's' : ''}
          </span>
        )
      },
    },
    {
      id: 'execution_order',
      header: 'Order',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">{row.original.execution_order}</span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const workflow = row.original
        return (
          <div className="flex items-center justify-end gap-1">
            <button
              type="button"
              onClick={() => setDocumentRequirementsWorkflow(workflow)}
              disabled={hasNoAccess}
              className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={hasNoAccess ? 'No permission' : 'Document requirements'}
            >
              <FileCheck className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setEditingWorkflow(workflow)}
              disabled={hasNoAccess}
              className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={hasNoAccess ? 'No permission to update' : 'Edit name, description, order'}
            >
              <SquarePen className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => handleToggleWorkflow(workflow.id, workflow.is_active)}
              disabled={toggling === workflow.id || hasNoAccess}
              className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={
                hasNoAccess
                  ? 'No permission to update'
                  : workflow.is_active
                    ? 'Deactivate'
                    : 'Activate'
              }
            >
              {toggling === workflow.id ? (
                <LoadingIcon />
              ) : workflow.is_active ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
            </button>
            <button
              type="button"
              onClick={() => handleDeleteClick(workflow.id, workflow.name)}
              disabled={deleting === workflow.id || hasNoAccess}
              className="p-1 text-muted-foreground hover:text-red-600 dark:hover:text-red-400 hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={hasNoAccess ? 'No permission to delete' : 'Delete'}
            >
              {deleting === workflow.id ? <LoadingIcon /> : <Trash2 className="w-4 h-4" />}
            </button>
          </div>
        )
      },
    },
  ]

  const filteredWorkflows = filterEventType
    ? workflows.filter((w: Workflow) => {
        const triggerEventType = w.trigger_event_type || ''
        return triggerEventType === filterEventType
      })
    : workflows

  return (
    <>
      {showCreateModal && !hasNoAccess && (
        <WorkflowRequirementsModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateWorkflow}
          title="Create workflow"
        />
      )}

      {/* Edit Workflow Modal */}
      {editingWorkflow && !hasNoAccess && (
        <WorkflowEditModal
          workflow={editingWorkflow}
          onClose={() => setEditingWorkflow(null)}
          onSave={handleUpdateWorkflow}
        />
      )}

      {/* Document requirements modal */}
      {documentRequirementsWorkflow && (
        <WorkflowDocumentRequirementsModal
          workflowId={documentRequirementsWorkflow.id}
          workflowName={documentRequirementsWorkflow.name}
          isOpen={true}
          onClose={() => setDocumentRequirementsWorkflow(null)}
        />
      )}

      <ErrorModal
        open={!!error}
        onClose={() => setError(null)}
        title="Error"
        message={error ?? ''}
      />

      {/* No Access Notice */}
      {hasNoAccess && (
        <div className="mb-3 p-2.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-none flex gap-2">
          <ErrorIcon className="text-amber-600 dark:text-amber-400 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-amber-900 dark:text-amber-200 text-sm">
              Limited Access
            </h3>
            <p className="text-sm text-amber-800 dark:text-amber-300 mt-0.5">
              You don't have permission to manage workflows. You can view existing workflows but
              cannot create or modify them.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Workflows</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage event-driven automation workflows
          </p>
        </div>
        {!hasNoAccess && (
          <div className="flex items-center gap-2">
            <Link to="/settings/workflows/builder">
              <Button variant="secondary" size="md">
                <Network className="w-4 h-4" />
                Graph builder
              </Button>
            </Link>
            <Button onClick={() => setShowCreateModal(true)} variant="primary" size="md">
              <Plus className="w-4 h-4" />
              Workflow
            </Button>
          </div>
        )}
      </div>

      {/* Filters */}
      {eventTypes.length > 0 && (
        <div className="bg-card/80 backdrop-blur-sm rounded-none p-2.5 border border-border/50 mb-3">
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor={filterByTriggerId} className="text-sm font-medium text-foreground/90">
              Filter by trigger event type:
            </label>
            <select
              id={filterByTriggerId}
              value={filterEventType}
              onChange={(e) => setFilterEventType(e.target.value)}
              className="px-3 py-1.5 bg-background border border-input rounded-none text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">All Workflows</option>
              {eventTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            {filterEventType && (
              <Button onClick={() => setFilterEventType('')} variant="secondary" size="md">
                Clear filter
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Workflows Table */}
      <DataTable
        data={filteredWorkflows}
        columns={columns}
        isLoading={loading}
        isEmpty={filteredWorkflows.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: hasNoAccess ? 'No workflows available' : 'No workflows yet',
          description: hasNoAccess
            ? 'You do not have permission to view or create workflows.'
            : 'Create your first workflow to automate event-driven tasks',
          action: !hasNoAccess ? (
            <Button onClick={() => setShowCreateModal(true)} variant="primary" size="md">
              <Plus className="w-4 h-4" />
              Workflow
            </Button>
          ) : undefined,
        }}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmModal
        isOpen={!!confirmingDelete}
        onClose={() => setConfirmingDelete(null)}
        title="Delete Workflow?"
        message={`Are you sure you want to delete "${confirmingDelete?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={handleConfirmDelete}
      />
    </>
  )
}
