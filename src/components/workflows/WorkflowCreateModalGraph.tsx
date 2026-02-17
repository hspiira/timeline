import { useState, useEffect, useCallback } from 'react'
import { useEventTypes } from '@/hooks/useEventTypes'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import type { components } from '@/lib/timeline-api'
import {
  createEmptyWorkflow,
  validateWorkflow,
  workflowGraphToCreateRequest,
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

type WorkflowCreate = components['schemas']['WorkflowCreateRequest']

export interface WorkflowCreateModalProps {
  onClose: () => void
  onSubmit: (data: WorkflowCreate) => Promise<boolean>
  title?: string
}

const WORKFLOW_ID_PLACEHOLDER = 'create-draft'

export function WorkflowCreateModalGraph({
  onClose,
  onSubmit,
  title = 'Create workflow',
}: WorkflowCreateModalProps) {
  const { types: eventTypes, loading: loadingEventTypes } = useEventTypes()
  const [workflow, setWorkflow] = useState<Workflow>(() =>
    createEmptyWorkflow(WORKFLOW_ID_PLACEHOLDER, '')
  )
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [triggerEventType, setTriggerEventType] = useState('')
  const [isActive, setIsActive] = useState(true)
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
  const createPayload = workflowGraphToCreateRequest(workflow)
  const canSubmit =
    name.trim() !== '' &&
    (createPayload?.trigger_event_type?.trim() ?? triggerEventType.trim()) !== '' &&
    (createPayload?.actions?.length ?? 0) > 0 &&
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
        triggerEventType: 'Add a trigger node and set the event type',
      }))
      return
    }
    if (!payloadFromGraph || payloadFromGraph.actions.length === 0) {
      setFieldErrors((prev) => ({
        ...prev,
        steps: 'Add at least one action or condition after the trigger',
      }))
      return
    }
    if (!validation.valid) {
      setFieldErrors((prev) => ({ ...prev, steps: validation.errors[0] }))
      return
    }

    const payload: WorkflowCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      trigger_event_type: triggerEventTypeFinal,
      actions: payloadFromGraph.actions,
      execution_order: 0,
      is_active: isActive,
    }

    const result = await execute(() => onSubmit(payload))
    if (result === true) {
      onClose()
    } else if (!result && !error) {
      setError('Failed to create workflow. Please try again.')
    }
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={title}
      maxWidth="max-w-6xl"
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
              Trigger event type
            </label>
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
        </div>

        <div className="flex gap-4 min-h-0">
          <div className="flex-1 min-w-0">
            <WorkflowBuilderCanvas
              workflow={workflow}
              workflowId={WORKFLOW_ID_PLACEHOLDER}
              workflowName={name}
              onWorkflowChange={setWorkflow}
              allowCircular={false}
              topPanel={<NodePaletteRow />}
              height="420px"
              onSelectionChange={setSelectedNodeId}
            />
          </div>
          {selectedNodeId && (() => {
            const node = workflow.nodes.find((n) => n.id === selectedNodeId)
            if (!node) return null
            return (
              <div className="w-64 shrink-0 rounded-lg border border-border bg-background p-3">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Configure node
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
        {(fieldErrors.steps || fieldErrors.triggerEventType) && (
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
            <span className="text-sm text-foreground/90">Activate after creation</span>
          </label>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={loading || !canSubmit}>
              {loading ? 'Creating...' : 'Create workflow'}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
