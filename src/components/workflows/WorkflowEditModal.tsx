import { useState } from 'react'
import { Modal } from '../ui/Modal'
import { Input } from '../ui/input'
import { Button } from '../ui/button'
import { LoadingIcon } from '../ui/icons'
import { ErrorAlert } from '../ui/ErrorAlert'
import { FormField, FormTextarea } from '../ui/FormField'
import type { components } from '@/lib/timeline-api'

type Workflow = components['schemas']['WorkflowResponse']
type WorkflowUpdate = components['schemas']['WorkflowUpdate']

interface WorkflowEditModalProps {
  workflow: Workflow
  onClose: () => void
  onSave: (id: string, data: WorkflowUpdate) => Promise<boolean>
}

export function WorkflowEditModal({ workflow, onClose, onSave }: WorkflowEditModalProps) {
  const [name, setName] = useState(workflow.name)
  const [description, setDescription] = useState(workflow.description ?? '')
  const [executionOrder, setExecutionOrder] = useState(workflow.execution_order ?? 0)
  const [isActive, setIsActive] = useState(workflow.is_active)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const success = await onSave(workflow.id, {
        name: name.trim() || undefined,
        description: description.trim() || undefined,
        execution_order: executionOrder,
        is_active: isActive,
      })
      if (success) onClose()
      else setError('Failed to update workflow')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update workflow')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={true} onClose={onClose} title="Edit workflow" maxWidth="max-w-md" closeButton={!loading}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorAlert message={error} />}
        <FormField label="Name">
          <Input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Workflow name"
            disabled={loading}
          />
        </FormField>
        <FormField label="Description">
          <FormTextarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            rows={2}
            disabled={loading}
          />
        </FormField>
        <FormField label="Execution order">
          <Input
            type="number"
            min={0}
            value={executionOrder}
            onChange={(e) => setExecutionOrder(parseInt(e.target.value, 10) || 0)}
            disabled={loading}
          />
        </FormField>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="edit-active"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            disabled={loading}
            className="rounded border-input"
          />
          <label htmlFor="edit-active" className="text-sm font-medium text-foreground/90">
            Active
          </label>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? <LoadingIcon /> : 'Save'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
