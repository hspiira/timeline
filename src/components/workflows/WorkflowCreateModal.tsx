import { useState, useMemo, useEffect } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useEventTypes } from '@/hooks/useEventTypes'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import type { components } from '@/lib/timeline-api'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/button'
import { FormField, FormInput, FormTextarea } from '@/components/ui/FormField'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { ErrorAlert } from '@/components/ui/ErrorAlert'
import { ArrowDown, GripVertical, Zap, Trash2 } from 'lucide-react'

type WorkflowCreate = components['schemas']['WorkflowCreateRequest']

interface ActionItem {
  id: string
  type: string
  params: Record<string, unknown>
}

const ACTION_TYPES = [
  { value: 'create_event', label: 'Create Event' },
  { value: 'send_email', label: 'Send Email' },
  { value: 'update_subject', label: 'Update Subject' },
] as const

function FlowArrow() {
  return (
    <div className="flex flex-col items-center py-1" aria-hidden>
      <div className="w-px h-3 bg-border" />
      <ArrowDown className="w-4 h-4 text-muted-foreground" />
      <div className="w-px h-3 bg-border" />
    </div>
  )
}

function TriggerNode({
  eventType,
  eventTypes,
  loading,
  onChange,
  disabled,
}: {
  eventType: string
  eventTypes: string[]
  loading: boolean
  onChange: (value: string) => void
  disabled?: boolean
}) {
  return (
    <div className="flex flex-col items-center">
      <div className="px-4 py-3 bg-primary/10 border border-primary/30 rounded-none min-w-[200px] text-center">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">Trigger</div>
        <Select
          value={eventType}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled || loading}
          className="w-full text-sm font-medium bg-background"
        >
          <option value="">Select event type...</option>
          {eventTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
      </div>
    </div>
  )
}

function ActionNode({
  action,
  index,
  isSelected,
  onSelect,
  onRemove,
  disabled,
}: {
  action: ActionItem
  index: number
  isSelected: boolean
  onSelect: () => void
  onRemove: () => void
  disabled?: boolean
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: action.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const label = ACTION_TYPES.find((a) => a.value === action.type)?.label ?? action.type

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex flex-col items-center"
    >
      <div
        role="button"
        tabIndex={0}
        onClick={onSelect}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect()}
        className={`
          flex items-center gap-2 px-4 py-3 min-w-[220px] rounded-none border cursor-pointer transition-colors
          ${isSelected ? 'bg-primary/15 border-primary/50 ring-1 ring-primary/30' : 'bg-card border-border hover:border-muted-foreground/40'}
        `}
      >
        <button
          type="button"
          className="p-1 touch-none cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground disabled:pointer-events-none"
          aria-label="Drag to reorder"
          disabled={disabled}
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical className="w-4 h-4" />
        </button>
        <Zap className="w-4 h-4 text-primary shrink-0" />
        <div className="flex-1 text-left min-w-0">
          <div className="text-xs text-muted-foreground">Action {index + 1}</div>
          <div className="text-sm font-medium truncate">{label}</div>
        </div>
        {!disabled && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onRemove()
            }}
            className="p-1 text-muted-foreground hover:text-destructive rounded-none transition-colors"
            aria-label="Remove action"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )
}

export interface WorkflowCreateModalProps {
  onClose: () => void
  onSubmit: (data: WorkflowCreate) => Promise<boolean>
  title?: string
}

export function WorkflowCreateModal({ onClose, onSubmit, title = 'Create workflow' }: WorkflowCreateModalProps) {
  const { types: eventTypes, loading: loadingEventTypes } = useEventTypes()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [triggerEventType, setTriggerEventType] = useState('')
  const [actions, setActions] = useState<ActionItem[]>([])
  const [selectedActionId, setSelectedActionId] = useState<string | null>(null)
  const [isActive, setIsActive] = useState(true)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [paramsInput, setParamsInput] = useState('')

  const { execute, loading, error, setError } = useFormSubmit()

  const selectedAction = useMemo(
    () => actions.find((a) => a.id === selectedActionId) ?? null,
    [actions, selectedActionId]
  )

  useEffect(() => {
    const action = actions.find((a) => a.id === selectedActionId)
    if (action) {
      setParamsInput(
        Object.keys(action.params).length === 0
          ? ''
          : JSON.stringify(action.params, null, 0)
      )
    } else {
      setParamsInput('')
    }
  }, [selectedActionId, actions])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      setActions((prev) => {
        const ids = prev.map((a) => a.id)
        const oldIndex = ids.indexOf(active.id as string)
        const newIndex = ids.indexOf(over.id as string)
        if (oldIndex === -1 || newIndex === -1) return prev
        return arrayMove(prev, oldIndex, newIndex)
      })
    }
  }

  const addAction = () => {
    const newAction: ActionItem = {
      id: `action-${Date.now()}`,
      type: 'create_event',
      params: {},
    }
    setActions((prev) => [...prev, newAction])
    setSelectedActionId(newAction.id)
    setFieldErrors((e) => ({ ...e, actions: '' }))
  }

  const removeAction = (id: string) => {
    setActions((prev) => prev.filter((a) => a.id !== id))
    if (selectedActionId === id) setSelectedActionId(null)
  }

  const updateAction = (id: string, updates: Partial<Pick<ActionItem, 'type' | 'params'>>) => {
    setActions((prev) =>
      prev.map((a) => (a.id === id ? { ...a, ...updates } : a))
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const errors: Record<string, string> = {}
    if (!name.trim()) errors.name = 'Workflow name is required'
    if (!triggerEventType.trim()) errors.triggerEventType = 'Trigger event type is required'
    if (actions.length === 0) errors.actions = 'At least one action is required'

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    const payload: WorkflowCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      trigger_event_type: triggerEventType,
      actions: actions.map((a) => ({ type: a.type, params: a.params || null })),
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

  const actionIds = actions.map((a) => a.id)

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={title}
      maxWidth="max-w-6xl"
      closeButton={!loading}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground -mt-2">
          Define trigger and actions; reorder by dragging.
        </p>

        <div className="flex flex-col lg:flex-row gap-6 max-h-[70vh] overflow-auto">
          {/* Flowchart */}
          <div className="flex-1 min-w-0">
            <div className="bg-card/50 border border-border rounded-none p-6 min-h-[280px]">
              <h3 className="text-sm font-semibold text-foreground/90 mb-4">Flow</h3>
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <div className="flex flex-col items-center">
                  <TriggerNode
                    eventType={triggerEventType}
                    eventTypes={eventTypes}
                    loading={loadingEventTypes}
                    onChange={(v) => {
                      setTriggerEventType(v)
                      setFieldErrors((e) => ({ ...e, triggerEventType: '' }))
                    }}
                    disabled={loading}
                  />

                  {actions.length > 0 && (
                    <>
                      <FlowArrow />
                      <SortableContext items={actionIds} strategy={verticalListSortingStrategy}>
                        {actions.map((action, index) => (
                          <div key={action.id} className="flex flex-col items-center">
                            <ActionNode
                              action={action}
                              index={index}
                              isSelected={selectedActionId === action.id}
                              onSelect={() => setSelectedActionId(action.id)}
                              onRemove={() => removeAction(action.id)}
                              disabled={loading}
                            />
                            {index < actions.length - 1 && <FlowArrow />}
                          </div>
                        ))}
                      </SortableContext>
                    </>
                  )}

                  {actions.length === 0 && (
                    <div className="mt-4 py-6 px-6 border border-dashed border-border rounded-none text-center text-sm text-muted-foreground">
                      No actions yet. Add one in the settings panel →
                    </div>
                  )}
                </div>
              </DndContext>
            </div>
          </div>

          {/* Settings sidebar */}
          <div className="w-full lg:w-80 shrink-0 space-y-4">
            <div className="bg-card/50 border border-border rounded-none p-4 space-y-4">
              <h3 className="text-sm font-semibold text-foreground/90">Settings</h3>

              {error && <ErrorAlert message={error} />}

              <FormField label="Workflow name" required error={fieldErrors.name}>
                <FormInput
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value)
                    setFieldErrors((e) => ({ ...e, name: '' }))
                  }}
                  placeholder="e.g. Alert on high priority events"
                  disabled={loading}
                  error={fieldErrors.name}
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

              <FormField
                label="Trigger event type"
                required
                error={fieldErrors.triggerEventType}
                hint="Event type that starts this workflow"
              >
                <Select
                  value={triggerEventType}
                  onChange={(e) => {
                    setTriggerEventType(e.target.value)
                    setFieldErrors((e) => ({ ...e, triggerEventType: '' }))
                  }}
                  disabled={loading || loadingEventTypes}
                  error={fieldErrors.triggerEventType}
                  className="w-full"
                >
                  <option value="">Select event type...</option>
                  {eventTypes.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </FormField>

              <div className="border-t border-border pt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-foreground/90">Actions</span>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={addAction}
                    disabled={loading}
                  >
                    Add action
                  </Button>
                </div>
                {fieldErrors.actions && (
                  <p className="text-xs text-destructive mb-2">{fieldErrors.actions}</p>
                )}
              </div>

              {selectedAction && (
                <div className="border-t border-border pt-4 space-y-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Edit action {actions.findIndex((a) => a.id === selectedAction.id) + 1}
                  </h4>
                  <FormField label="Action type">
                    <Select
                      value={selectedAction.type}
                      onChange={(e) =>
                        updateAction(selectedAction.id, { type: e.target.value })
                      }
                      disabled={loading}
                      className="w-full"
                    >
                      {ACTION_TYPES.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </Select>
                  </FormField>
                  <FormField label="Parameters (JSON)">
                    <Input
                      type="text"
                      placeholder='e.g. {"key": "value"}'
                      value={paramsInput}
                      onChange={(e) => {
                        const raw = e.target.value
                        setParamsInput(raw)
                        const trimmed = raw.trim()
                        if (!trimmed) {
                          updateAction(selectedAction.id, { params: {} })
                          return
                        }
                        try {
                          const parsed = JSON.parse(trimmed) as Record<string, unknown>
                          updateAction(selectedAction.id, { params: parsed })
                        } catch {
                          // allow typing invalid JSON meanwhile
                        }
                      }}
                      disabled={loading}
                      className="font-mono text-xs"
                    />
                  </FormField>
                </div>
              )}

              <div className="border-t border-border pt-4 flex items-center gap-3">
                <input
                  type="checkbox"
                  id="workflow-create-active"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  disabled={loading}
                  className="rounded-none"
                />
                <label htmlFor="workflow-create-active" className="text-sm font-medium text-foreground/90">
                  Activate workflow after creation
                </label>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-border">
          <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? 'Creating...' : 'Create workflow'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
