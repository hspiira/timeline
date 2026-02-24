/**
 * Edit workflow modal. Only name, description, execution_order, and is_active are editable;
 * trigger and steps are read-only (set at creation).
 */

import { useState, useMemo } from 'react'
import { ChevronRight, FileText, ListTodo, Pencil } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import { ErrorAlert } from '@/components/ui/ErrorAlert'
import { FormField, FormTextarea } from '@/components/ui/FormField'
import { getStepsFromWorkflowActions } from '@/lib/workflow-builder/parse-workflow-actions'
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
  const [editingDetails, setEditingDetails] = useState(false)
  const { execute, loading, error, setError } = useFormSubmit()

  const steps = useMemo(
    () => getStepsFromWorkflowActions(workflow.actions),
    [workflow.actions]
  )
  const triggerLabel = workflow.trigger_event_type || '—'
  const stepCount = steps.length

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const success = await execute(() =>
      onSave(workflow.id, {
        name: name.trim() || undefined,
        description: description.trim() || undefined,
        execution_order: executionOrder,
        is_active: isActive,
      })
    )

    if (success) {
      onClose()
      setEditingDetails(false)
    } else {
      setError('Failed to update workflow')
    }
  }

  const cancelEditDetails = () => {
    setName(workflow.name)
    setDescription(workflow.description ?? '')
    setEditingDetails(false)
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Workflow settings"
      subtitle={name}
      maxWidth="max-w-5xl"
      closeButton={!loading}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="flex flex-wrap items-center gap-8">
            <label className="flex items-center gap-2.5 cursor-pointer select-none">
              <Checkbox
                checked={isActive}
                onCheckedChange={(v) => setIsActive(v === true)}
                disabled={loading}
              />
              <span className="text-sm font-medium text-foreground">Active</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Run order</span>
              <Input
                type="number"
                min={0}
                value={executionOrder}
                onChange={(e) => setExecutionOrder(parseInt(e.target.value, 10) || 0)}
                disabled={loading}
                className="h-8 w-14 text-center text-sm tabular-nums"
                title="When multiple workflows share a trigger, lower runs first"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" form="workflow-edit-form" variant="primary" disabled={loading}>
              {loading ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </div>
      }
    >
      <form id="workflow-edit-form" onSubmit={handleSubmit} className="flex flex-col">
        <section className="flex flex-col gap-4">
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Overview
          </h3>
          <div className="rounded-lg border border-border bg-muted/5 overflow-hidden">
            {editingDetails ? (
              <div className="p-5 space-y-4">
                <FormField label="Name">
                  <Input
                    id="workflow-edit-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Workflow name"
                    disabled={loading}
                    className="text-sm"
                  />
                </FormField>
                <FormField label="Description">
                  <FormTextarea
                    id="workflow-edit-desc"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What this workflow does"
                    rows={2}
                    disabled={loading}
                    className="text-sm resize-none"
                  />
                </FormField>
                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={cancelEditDetails}
                    disabled={loading}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => setEditingDetails(false)}
                    disabled={loading}
                  >
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-4 p-5">
                <div className="min-w-0 flex-1">
                  <p className="text-base font-semibold text-foreground">{name || 'Untitled workflow'}</p>
                  <p className="mt-1 text-sm text-muted-foreground whitespace-pre-wrap">
                    {description || '—'}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditingDetails(true)}
                  disabled={loading}
                  className="shrink-0 text-muted-foreground hover:text-foreground"
                  aria-label="Edit name and description"
                >
                  <Pencil className="w-4 h-4 mr-1.5" />
                  Edit
                </Button>
              </div>
            )}
          </div>
        </section>

        <section className="flex flex-col gap-4 mt-8">
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Configuration
          </h3>
          <div className="rounded-lg border border-border bg-muted/5 px-4 py-3 text-sm">
            <span className="text-muted-foreground">Trigger</span>
            <span className="mx-2 text-muted-foreground/60">·</span>
            <span className="font-medium text-foreground">{triggerLabel}</span>
            {stepCount > 0 && (
              <>
                <span className="mx-2 text-muted-foreground/60">·</span>
                <span className="text-muted-foreground">{stepCount} steps</span>
              </>
            )}
          </div>

          {stepCount > 0 ? (
            <div className="rounded-lg border border-border overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border bg-muted/10">
                <ListTodo className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Steps</span>
              </div>
              <ul className="divide-y divide-border">
                {steps.map((step, index) => (
                  <li key={step.index} className="px-4 py-3 hover:bg-muted/5 transition-colors">
                    <div className="flex items-start gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-[11px] font-semibold text-muted-foreground tabular-nums">
                        {index + 1}
                      </span>
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="text-sm font-medium text-foreground">{step.name}</p>
                        {step.description && (
                          <p className="text-xs text-muted-foreground">{step.description}</p>
                        )}
                        {step.condition && (
                          <p className="text-xs text-muted-foreground/80 italic">{step.condition}</p>
                        )}
                        {step.tasks.length > 0 && (
                          <ul className="mt-2 space-y-1">
                            {step.tasks.map((task, ti) => (
                              <li
                                key={ti}
                                className="flex items-center gap-2 text-xs text-muted-foreground"
                              >
                                <ChevronRight className="h-3 w-3 shrink-0 opacity-50" />
                                <span>{task.name}</span>
                                {task.requireDocument && (
                                  <FileText className="h-3 w-3 shrink-0 text-amber-600/80 dark:text-amber-400/80" />
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-3">
              No steps. Steps are defined when the workflow is created.
            </p>
          )}
        </section>

        {error && (
          <div className="mt-6">
            <ErrorAlert message={error} />
          </div>
        )}
      </form>
    </Modal>
  )
}
