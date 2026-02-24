/**
 * Modal to create a workflow by specifying requirements in natural language:
 * workflow name, trigger event type, steps (name + description + condition), tasks and documents.
 * No visual graph – form only. Converts to API WorkflowCreateRequest on submit.
 * Matches WorkflowCreateModal layout: wide modal, footer with "Activate after creation" and actions.
 */

import { useState, useCallback } from 'react'
import { useWorkflowEngineContext } from '@/hooks/useWorkflowEngineContext'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import type { components } from '@/lib/timeline-api'
import {
  createEmptyWorkflowRequirements,
  requirementsToCreateRequest,
  validateWorkflowRequirements,
  type WorkflowRequirements,
} from '@/lib/workflow-builder/workflow-requirements'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/button'
import { WorkflowRequirementsForm } from '@/components/workflows/WorkflowRequirementsForm'
import { ErrorAlert } from '@/components/ui/ErrorAlert'

type WorkflowCreate = components['schemas']['WorkflowCreateRequest']

export interface WorkflowRequirementsModalProps {
  onClose: () => void
  onSubmit: (data: WorkflowCreate) => Promise<boolean>
  title?: string
}

export function WorkflowRequirementsModal({
  onClose,
  onSubmit,
  title = 'Create workflow',
}: WorkflowRequirementsModalProps) {
  const { eventTypes } = useWorkflowEngineContext()
  const [requirements, setRequirements] = useState<WorkflowRequirements>(() => createEmptyWorkflowRequirements(''))
  const [isActive, setIsActive] = useState(true)
  const { execute, loading, error, setError } = useFormSubmit()

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const validation = validateWorkflowRequirements(requirements)
    if (!validation.valid) return
    const payload = requirementsToCreateRequest(requirements)
    if (!payload.trigger_event_type) {
      setError('Trigger event type is required')
      return
    }
    const createPayload: WorkflowCreate = {
      name: payload.name,
      description: payload.description ?? undefined,
      trigger_event_type: payload.trigger_event_type,
      actions: payload.actions,
      execution_order: 0,
      is_active: isActive,
    }
    const success = await execute(() => onSubmit(createPayload))
    if (success) onClose()
  }, [requirements, isActive, onSubmit, onClose, execute, setError])

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={title}
      subtitle={requirements.name.trim() || undefined}
      maxWidth="max-w-5xl"
      closeButton={!loading}
      footer={
        <div className="flex flex-wrap items-center justify-end gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              disabled={loading}
              className="rounded border-input"
            />
            <span className="text-sm text-foreground/90">Activate after creation</span>
          </label>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" form="workflow-requirements-form" variant="primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create workflow'}
            </Button>
          </div>
        </div>
      }
    >
      <form id="workflow-requirements-form" onSubmit={handleSubmit} className="flex flex-col gap-6">
        <p className="text-sm text-muted-foreground">
          Define steps and tasks in plain language. No diagram required.
        </p>
        <WorkflowRequirementsForm
          value={requirements}
          onChange={setRequirements}
          eventTypeOptions={eventTypes}
        />
        {error && <ErrorAlert message={error} />}
      </form>
    </Modal>
  )
}
