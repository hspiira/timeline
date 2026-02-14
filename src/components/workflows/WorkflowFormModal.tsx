import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { components } from '@/lib/timeline-api'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import { Modal } from '../ui/Modal'
import { FormField, FormInput, FormTextarea } from '../ui/FormField'
import { Input } from '../ui/input'
import { Select } from '../ui/select'
import { Button } from '../ui/button'
import { FormModalActions } from '../ui/FormModalActions'
import { ErrorAlert } from '../ui/ErrorAlert'
import { useEventTypes } from '@/hooks/useEventTypes'

type WorkflowCreate = components['schemas']['WorkflowCreateRequest']

interface WorkflowFormModalProps {
  onClose: () => void
  onSubmit: (data: WorkflowCreate) => Promise<boolean>
  title: string
}

interface FormState {
  name: string
  description: string
  triggerEventType: string
  actions: Array<{
    id: string
    action_type: string
    parameters: Record<string, any>
  }>
  isActive: boolean
  fieldErrors: Record<string, string>
}

export function WorkflowFormModal({ onClose, onSubmit, title }: WorkflowFormModalProps) {
  const [state, setState] = useState<FormState>({
    name: '',
    description: '',
    triggerEventType: '',
    actions: [],
    isActive: true,
    fieldErrors: {},
  })
  const { execute, loading, error, setError } = useFormSubmit()
  const { types: eventTypes, loading: loadingEventTypes } = useEventTypes()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    const errors: Record<string, string> = {}

    if (!state.name.trim()) {
      errors.name = 'Workflow name is required'
    }

    if (!state.triggerEventType.trim()) {
      errors.triggerEventType = 'Trigger event type is required'
    }

    if (state.actions.length === 0) {
      errors.actions = 'At least one action is required'
    }

    if (Object.keys(errors).length > 0) {
      setState((prev) => ({ ...prev, fieldErrors: errors }))
      return
    }

    const workflowData: WorkflowCreate = {
      name: state.name,
      description: state.description || undefined,
      trigger_event_type: state.triggerEventType,
      actions: state.actions as any,
      execution_order: 0,
      is_active: state.isActive,
    }

    const success = await execute(() => onSubmit(workflowData))
    if (success) {
      onClose()
    } else {
      setError('Failed to create workflow. Please try again.')
    }
  }

  const addAction = () => {
    const newAction = {
      id: Date.now().toString(),
      action_type: 'create_event',
      parameters: {},
    }
    setState((prev) => ({
      ...prev,
      actions: [...prev.actions, newAction],
    }))
  }

  const removeAction = (id: string) => {
    setState((prev) => ({
      ...prev,
      actions: prev.actions.filter((a) => a.id !== id),
    }))
  }

  const updateAction = (id: string, updates: Partial<(typeof state.actions)[0]>) => {
    setState((prev) => ({
      ...prev,
      actions: prev.actions.map((a) => (a.id === id ? { ...a, ...updates } : a)),
    }))
  }

  return (
    <Modal isOpen={true} onClose={onClose} title={title} maxWidth="max-w-2xl" closeButton={!loading}>
      <form onSubmit={handleSubmit} className="space-y-5">
          {error && <ErrorAlert message={error} />}

          {/* Workflow Name */}
          <FormField
            label="Workflow Name"
            required
            error={state.fieldErrors.name}
          >
            <FormInput
              type="text"
              value={state.name}
              onChange={(e) =>
                setState((prev) => ({
                  ...prev,
                  name: e.target.value,
                  fieldErrors: { ...prev.fieldErrors, name: '' },
                }))
              }
              placeholder="e.g., Alert on high priority events"
              disabled={loading}
              error={state.fieldErrors.name}
            />
          </FormField>

          <FormField label="Description">
            <FormTextarea
              value={state.description}
              onChange={(e) =>
                setState((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              placeholder="Optional description of what this workflow does"
              rows={3}
              disabled={loading}
            />
          </FormField>

          {/* Trigger Configuration */}
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-semibold text-foreground/90 mb-3">Trigger</h3>
            <FormField
              label="Event Type"
              required
              error={state.fieldErrors.triggerEventType}
              hint="This workflow will be triggered when an event of this type is created"
            >
              <Select
                value={state.triggerEventType}
                onChange={(e) =>
                  setState((prev) => ({
                    ...prev,
                    triggerEventType: e.target.value,
                    fieldErrors: { ...prev.fieldErrors, triggerEventType: '' },
                  }))
                }
                disabled={loading || loadingEventTypes}
                error={state.fieldErrors.triggerEventType}
                className="w-full"
              >
                <option value="">Select event type...</option>
                {eventTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>

          {/* Actions Configuration */}
          <div className="border-t border-border pt-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-foreground/90">Actions</h3>
              <Button
                type="button"
                onClick={addAction}
                disabled={loading}
                size="sm"
                variant="primary"
              >
                <Plus className="w-3 h-3" />
                Add Action
              </Button>
            </div>

            {state.fieldErrors.actions && (
              <p className="text-xs text-destructive mb-2">{state.fieldErrors.actions}</p>
            )}

            {state.actions.length === 0 ? (
              <div className="p-3 bg-background/50 border border-dashed border-border rounded-none text-center text-sm text-muted-foreground">
                No actions yet. Click "Add Action" to create one.
              </div>
            ) : (
              <div className="space-y-3">
                {state.actions.map((action, index) => (
                  <div
                    key={action.id}
                    className="p-3 bg-background/50 border border-border rounded-none space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">Action {index + 1}</span>
                      <button
                        type="button"
                        onClick={() => removeAction(action.id)}
                        disabled={loading}
                        className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-none transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </button>
                    </div>

                    <Select
                      value={action.action_type}
                      onChange={(e) =>
                        updateAction(action.id, { action_type: e.target.value })
                      }
                      disabled={loading}
                      className="text-sm"
                    >
                      <option value="create_event">Create Event</option>
                      <option value="send_email">Send Email</option>
                      <option value="update_subject">Update Subject</option>
                    </Select>

                    <Input
                      type="text"
                      placeholder="Action parameters (JSON format)"
                      disabled={loading}
                      className="text-xs"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Active Toggle */}
          <div className="border-t border-border pt-4 flex items-center gap-3">
            <input
              type="checkbox"
              id="isActive"
              checked={state.isActive}
              onChange={(e) =>
                setState((prev) => ({
                  ...prev,
                  isActive: e.target.checked,
                }))
              }
              disabled={loading}
              className="rounded-none"
            />
            <label htmlFor="isActive" className="text-sm font-medium text-foreground/90">
              Activate workflow immediately after creation
            </label>
          </div>

        <FormModalActions
          submitLabel="Create Workflow"
          loadingLabel="Creating..."
          onCancel={onClose}
          loading={loading}
        />
      </form>
    </Modal>
  )
}
