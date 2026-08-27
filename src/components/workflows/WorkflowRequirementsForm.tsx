/**
 * Form-based workflow builder: compact, accordion steps, tasks as simple list.
 * No task descriptions; each task has name + "Require document" checkbox.
 */

import { Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useId, useState } from 'react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { optionsFromStrings, SingleSelectCombobox } from '@/components/ui/combobox'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import {
  createEmptyWorkflowRequirements,
  createStepRequirement,
  createTaskRequirement,
  validateWorkflowRequirements,
  type WorkflowRequirements,
  type WorkflowStepRequirement,
  type WorkflowTaskRequirement,
} from '@/lib/workflow-builder/workflow-requirements'

export interface WorkflowRequirementsFormProps {
  value: WorkflowRequirements
  onChange: (value: WorkflowRequirements) => void
  eventTypeOptions?: string[]
  errors?: string[]
  compact?: boolean
}

export function WorkflowRequirementsForm({
  value,
  onChange,
  eventTypeOptions = [],
  errors = [],
  compact: _compact = false,
}: WorkflowRequirementsFormProps) {
  const oncheckedchangeRequireDocumentId = useId()
  const validation = validateWorkflowRequirements(value)
  const showErrors = errors.length > 0 ? errors : validation.errors

  const [openStepId, setOpenStepId] = useState<string | null>(value.steps[0]?.id ?? null)

  useEffect(() => {
    const ids = new Set(value.steps.map((s) => s.id))
    if (openStepId && !ids.has(openStepId) && value.steps.length > 0) {
      setOpenStepId(value.steps[0].id)
    } else if (value.steps.length === 0) {
      setOpenStepId(null)
    }
  }, [value.steps, openStepId])

  const update = useCallback(
    (patch: Partial<WorkflowRequirements>) => {
      onChange({ ...value, ...patch })
    },
    [value, onChange],
  )

  const addStep = useCallback(() => {
    const step = createStepRequirement('', { tasks: [] })
    onChange({ ...value, steps: [...value.steps, step] })
    setOpenStepId(step.id)
  }, [value, onChange])

  const updateStep = useCallback(
    (index: number, patch: Partial<WorkflowStepRequirement>) => {
      const next = [...value.steps]
      next[index] = { ...next[index], ...patch }
      onChange({ ...value, steps: next })
    },
    [value, onChange],
  )

  const removeStep = useCallback(
    (index: number) => {
      const next = value.steps.filter((_, i) => i !== index)
      const wasOpen = value.steps[index]?.id === openStepId
      onChange({ ...value, steps: next })
      if (wasOpen && next.length > 0) setOpenStepId(next[0].id)
      else if (next.length === 0) setOpenStepId(null)
    },
    [value, onChange, openStepId],
  )

  const addTask = useCallback(
    (stepIndex: number) => {
      const step = value.steps[stepIndex]
      const tasks = [...(step.tasks ?? []), createTaskRequirement('')]
      updateStep(stepIndex, { tasks })
    },
    [value, updateStep],
  )

  const updateTask = useCallback(
    (stepIndex: number, taskIndex: number, patch: Partial<WorkflowTaskRequirement>) => {
      const step = value.steps[stepIndex]
      const tasks = [...(step.tasks ?? [])]
      tasks[taskIndex] = { ...tasks[taskIndex], ...patch }
      updateStep(stepIndex, { tasks })
    },
    [value, updateStep],
  )

  const removeTask = useCallback(
    (stepIndex: number, taskIndex: number) => {
      const step = value.steps[stepIndex]
      const tasks = (step.tasks ?? []).filter((_, i) => i !== taskIndex)
      updateStep(stepIndex, { tasks: tasks.length > 0 ? tasks : undefined })
    },
    [value, updateStep],
  )

  const setRequireDocument = useCallback(
    (stepIndex: number, taskIndex: number, checked: boolean) => {
      updateTask(stepIndex, taskIndex, {
        documentIds: checked ? [''] : undefined,
      })
    },
    [updateTask],
  )

  const accordionValue = openStepId ?? ''
  const setAccordionValue = useCallback((v: string) => {
    setOpenStepId(v || null)
  }, [])

  return (
    <div className="space-y-5">
      {/* Workflow header: compact */}
      <div className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr]">
          <FormField label="Workflow name *">
            <Input
              value={value.name}
              onChange={(e) => update({ name: e.target.value })}
              placeholder="e.g. Onboard new customer"
              className="text-sm"
            />
          </FormField>
          {eventTypeOptions.length > 0 ? (
            <FormField label="Trigger event type *">
              <SingleSelectCombobox
                value={value.trigger_event_type ?? ''}
                onValueChange={(v) => update({ trigger_event_type: v || undefined })}
                options={optionsFromStrings(eventTypeOptions, {
                  value: '',
                  label: 'Select event type…',
                })}
                placeholder="Select event type…"
                className="text-sm"
              />
            </FormField>
          ) : (
            <FormField label="Trigger event type *">
              <Input
                value={value.trigger_event_type ?? ''}
                onChange={(e) => update({ trigger_event_type: e.target.value || undefined })}
                placeholder="e.g. order.created"
                className="text-sm"
              />
            </FormField>
          )}
        </div>
        <FormField label="Description (optional)">
          <Textarea
            value={value.description ?? ''}
            onChange={(e) => update({ description: e.target.value || undefined })}
            placeholder="What this workflow does"
            rows={1}
            className="text-sm resize-none"
          />
        </FormField>
      </div>

      {showErrors.length > 0 && (
        <ul className="text-sm text-destructive list-disc list-inside">
          {showErrors.map((err) => (
            <li key={err}>{err}</li>
          ))}
        </ul>
      )}

      {/* Steps: accordion */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <h3 className="text-sm font-semibold text-foreground">Steps</h3>
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" onClick={addStep}>
              <Plus className="w-3.5 h-3.5" />
              Add step
            </Button>
          </div>
        </div>

        {value.steps.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 border border-dashed border-border rounded-md text-center">
            No steps yet. Add a step to define the workflow.
          </p>
        ) : (
          <Accordion
            type="single"
            collapsible
            value={accordionValue}
            onValueChange={setAccordionValue}
            className="border border-border rounded-md divide-y divide-border"
          >
            {value.steps.map((step, stepIndex) => (
              <AccordionItem key={step.id} value={step.id} className="border-0">
                <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-muted/30">
                  <div className="flex items-center gap-2 w-full text-left">
                    <Input
                      value={step.name}
                      onChange={(e) => updateStep(stepIndex, { name: e.target.value })}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="Step name"
                      className="flex-1 min-w-0 h-8 text-sm font-medium border-0 shadow-none bg-transparent focus-visible:ring-2"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="shrink-0 text-muted-foreground hover:text-destructive h-8 w-8 p-0"
                      onClick={(e) => {
                        e.stopPropagation()
                        removeStep(stepIndex)
                      }}
                      title="Remove step"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 pt-0">
                  {/* Step description (optional) */}
                  <div className="mb-2">
                    <input
                      value={step.description ?? ''}
                      onChange={(e) =>
                        updateStep(stepIndex, {
                          description: e.target.value || undefined,
                        })
                      }
                      placeholder="(Description)"
                      className="w-full text-sm text-muted-foreground bg-muted/30 border border-border rounded px-2.5 py-1.5 placeholder:italic focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  {/* Step condition (optional) */}
                  <div className="mb-3">
                    <input
                      value={step.condition ?? ''}
                      onChange={(e) =>
                        updateStep(stepIndex, {
                          condition: e.target.value || undefined,
                        })
                      }
                      placeholder="Condition (e.g. when previous step succeeded)"
                      className="w-full text-sm text-muted-foreground bg-muted/30 border border-border rounded px-2.5 py-1.5 placeholder:italic focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>

                  {/* Tasks: compact list */}
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-xs text-muted-foreground">Tasks</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => addTask(stepIndex)}
                    >
                      <Plus className="w-3 h-3" />
                      Add task
                    </Button>
                  </div>
                  {(step.tasks ?? []).length === 0 ? (
                    <p className="text-xs text-muted-foreground py-2">No tasks. Add one below.</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {(step.tasks ?? []).map((task, taskIndex) => (
                        <li
                          key={task.id}
                          className={cn(
                            'flex items-center gap-2 py-1.5 pl-2 rounded border border-transparent hover:border-border/50',
                            'group',
                          )}
                        >
                          <span className="text-muted-foreground shrink-0">–</span>
                          <Input
                            value={task.name}
                            onChange={(e) =>
                              updateTask(stepIndex, taskIndex, {
                                name: e.target.value,
                              })
                            }
                            placeholder="Task name"
                            className="flex-1 min-w-0 h-8 text-sm border-0 bg-muted/20 focus-visible:ring-2 rounded"
                          />
                          <label
                            htmlFor={oncheckedchangeRequireDocumentId}
                            className="flex items-center gap-1.5 shrink-0 text-xs text-muted-foreground cursor-pointer whitespace-nowrap"
                          >
                            <Checkbox
                              checked={(task.documentIds?.length ?? 0) > 0}
                              onCheckedChange={(checked) =>
                                setRequireDocument(stepIndex, taskIndex, !!checked)
                              }
                            />
                            Require document
                          </label>
                          <Button
                            id={oncheckedchangeRequireDocumentId}
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="opacity-0 group-hover:opacity-100 h-7 w-7 p-0 text-muted-foreground hover:text-destructive shrink-0"
                            onClick={() => removeTask(stepIndex, taskIndex)}
                            title="Remove task"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </div>
    </div>
  )
}

export function getEmptyWorkflowRequirements(): WorkflowRequirements {
  return createEmptyWorkflowRequirements('')
}
