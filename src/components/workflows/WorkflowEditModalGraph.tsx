import { useState, useEffect, useCallback } from 'react'
import { useEventTypes } from '@/hooks/useEventTypes'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import type { components } from '@/lib/timeline-api'
import {
  validateWorkflow,
  workflowGraphToCreateRequest,
  workflowFromResponse,
  updateNode,
  nodeRegistry,
} from '@/lib/workflow-builder'
import type { Workflow } from '@/lib/workflow-builder'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { ErrorAlert } from '@/components/ui/ErrorAlert'
import { WorkflowBuilderCanvas } from '@/components/workflow-builder/WorkflowBuilderCanvas'
import { NodePaletteRow } from '@/components/workflow-builder/NodePaletteRow'
import { NodeConfigPanel } from '@/components/workflow-builder/NodeConfigPanel'

type WorkflowResponse = components['schemas']['WorkflowResponse']
type WorkflowUpdate = components['schemas']['WorkflowUpdate']

export interface WorkflowEditModalGraphProps {
  workflow: WorkflowResponse
  onClose: () => void
  onSave: (id: string, data: WorkflowUpdate) => Promise<boolean>
}

export function WorkflowEditModalGraph({
  workflow: initialWorkflow,
  onClose,
  onSave,
}: WorkflowEditModalGraphProps) {
  const { types: eventTypes, loading: loadingEventTypes } = useEventTypes()
  const [workflow, setWorkflow] = useState<Workflow>(() =>
    workflowFromResponse({
      id: initialWorkflow.id,
      name: initialWorkflow.name,
      trigger_event_type: initialWorkflow.trigger_event_type ?? '',
      actions: initialWorkflow.actions ?? [],
    })
  )
  const [name, setName] = useState(initialWorkflow.name ?? '')
  const [description, setDescription] = useState(initialWorkflow.description ?? '')
  const [executionOrder, setExecutionOrder] = useState(initialWorkflow.execution_order ?? 0)
  const [isActive, setIsActive] = useState(initialWorkflow.is_active ?? true)
  const [triggerEventType, setTriggerEventType] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const { execute, loading, error, setError } = useFormSubmit()

  const triggerNode = workflow.nodes.find((n) => nodeRegistry.getOptional(n.type)?.isTrigger)

  useEffect(() => {
    if (triggerNode) {
      const eventType = (triggerNode.configuration?.eventType as string) ?? ''
      setTriggerEventType(eventType)
    }
  }, [triggerNode?.id])

  const handleTriggerEventTypeChange = useCallback(
    (value: string) => {
      setTriggerEventType(value)
      setFieldErrors((e) => ({ ...e, triggerEventType: '' }))
      if (triggerNode) {
        setWorkflow((prev) =>
          updateNode(prev, triggerNode.id, {
            configuration: { ...triggerNode.configuration, eventType: value },
          })
        )
      }
    },
    [triggerNode]
  )

  const validation = validateWorkflow({ ...workflow, name })
  const graphPayload = workflowGraphToCreateRequest(workflow)
  const triggerEventTypeFinal =
    graphPayload?.trigger_event_type?.trim() ?? triggerEventType.trim()
  const canSubmit =
    name.trim() !== '' &&
    triggerEventTypeFinal !== '' &&
    (graphPayload?.actions?.length ?? 0) > 0 &&
    validation.valid

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) {
      setFieldErrors((prev) => ({ ...prev, name: 'Workflow name is required' }))
      return
    }
    const payloadFromGraph = workflowGraphToCreateRequest(workflow)
    const triggerEventTypeFinal =
      payloadFromGraph?.trigger_event_type?.trim() || triggerEventType.trim()
    if (!triggerEventTypeFinal) {
      setFieldErrors((prev) => ({
        ...prev,
        triggerEventType: 'Set the trigger event type',
      }))
      return
    }
    if (!payloadFromGraph || payloadFromGraph.actions.length === 0) {
      setFieldErrors((prev) => ({
        ...prev,
        steps: 'Workflow must have at least one action or condition after the trigger',
      }))
      return
    }
    if (!validation.valid) {
      setFieldErrors((prev) => ({ ...prev, steps: validation.errors[0] ?? 'Invalid workflow' }))
      return
    }

    const updateData: WorkflowUpdate & { trigger_event_type?: string; actions?: components['schemas']['WorkflowAction'][] } = {
      name: name.trim(),
      description: description.trim() || undefined,
      execution_order: executionOrder,
      is_active: isActive,
      trigger_event_type: triggerEventTypeFinal,
      actions: payloadFromGraph.actions,
    }

    const result = await execute(() => onSave(initialWorkflow.id, updateData as WorkflowUpdate))
    if (result === true) {
      onClose()
    } else if (!result && !error) {
      setError('Failed to update workflow. Please try again.')
    }
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Edit workflow"
      maxWidth="max-w-[96vw]"
      closeButton={!loading}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Workflow name
            </label>
            <Input
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                setFieldErrors((prev) => ({ ...prev, name: '' }))
              }}
              placeholder="e.g. Alert on high priority"
              disabled={loading}
              className={fieldErrors.name ? 'border-destructive' : ''}
            />
            {fieldErrors.name && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.name}</p>
            )}
          </div>
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Description (optional)
            </label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Short description"
              disabled={loading}
            />
          </div>
          <div className="min-w-[200px]">
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              When this workflow runs
            </label>
            <p className="text-[11px] text-muted-foreground/80 mb-1">
              This workflow runs when an event of this type is created.
            </p>
            <SingleSelectCombobox
              value={triggerNode ? (triggerNode.configuration?.eventType as string) ?? '' : triggerEventType}
              onValueChange={handleTriggerEventTypeChange}
              options={[
                { value: '', label: 'When event type…' },
                ...eventTypes.map((t) => ({ value: t, label: t })),
              ]}
              placeholder="When event type…"
              disabled={loading || loadingEventTypes}
              error={fieldErrors.triggerEventType}
              className={fieldErrors.triggerEventType ? 'border-destructive rounded-none border-input/80' : 'rounded-none border-input/80'}
            />
            {fieldErrors.triggerEventType && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.triggerEventType}</p>
            )}
          </div>
          <div className="min-w-[120px]">
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Execution order
            </label>
            <Input
              type="number"
              min={0}
              value={executionOrder}
              onChange={(e) => setExecutionOrder(parseInt(e.target.value, 10) || 0)}
              disabled={loading}
            />
          </div>
        </div>

        <div className="flex gap-4 min-h-0">
          <div className="flex-1 min-w-0">
            <WorkflowBuilderCanvas
              workflow={workflow}
              workflowId={initialWorkflow.id}
              workflowName={name}
              onWorkflowChange={setWorkflow}
              allowCircular={false}
              topPanel={<NodePaletteRow />}
              height="60vh"
              onSelectionChange={setSelectedNodeId}
            />
          </div>
          {selectedNodeId && (() => {
            const node = workflow.nodes.find((n) => n.id === selectedNodeId)
            if (!node) return null
            return (
              <div className="w-64 shrink-0 rounded-lg border border-border bg-background p-3">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Configure step
                </h4>
                <NodeConfigPanel
                  node={node}
                  eventTypes={eventTypes}
                  onUpdate={(updates) =>
                    setWorkflow((prev) =>
                      updateNode(prev, node.id, {
                        configuration: { ...node.configuration, ...updates },
                      })
                    )
                  }
                />
              </div>
            )
          })()}
        </div>

        {!validation.valid && validation.errors.length > 0 && (
          <p className="text-xs text-amber-600 dark:text-amber-400">
            {validation.errors.join(' ')}
          </p>
        )}
        {(fieldErrors.steps ?? fieldErrors.triggerEventType) && (
          <p className="text-xs text-destructive">
            {fieldErrors.steps ?? fieldErrors.triggerEventType}
          </p>
        )}
        {error && <ErrorAlert message={error} />}

        <div className="flex flex-wrap items-center justify-end gap-4 pt-2 border-t border-border">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              disabled={loading}
              className="rounded-none"
            />
            <span className="text-sm text-foreground/90">Active</span>
          </label>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={loading || !canSubmit}>
              {loading ? 'Saving...' : 'Save changes'}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
