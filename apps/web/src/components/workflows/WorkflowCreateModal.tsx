import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  arrayMove,
  horizontalListSortingStrategy,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  ArrowDown,
  ArrowRight,
  GitBranch,
  GripVertical,
  Info,
  Plus,
  Trash2,
  Zap,
} from 'lucide-react'
import { useEffect, useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { ErrorAlert } from '@/components/ui/ErrorAlert'
import { Input } from '@/components/ui/input'
import { Modal } from '@/components/ui/Modal'
import { useEventTypes } from '@/hooks/useEventTypes'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import type { components } from '@/lib/timeline-api'
import { toApiActions } from '@/lib/workflow-builder'
import { getActionTypeInfo, WORKFLOW_ACTION_TYPES } from '@/lib/workflow-builder/action-types'

export type FlowDirection = 'lr' | 'tb'

type WorkflowCreate = components['schemas']['WorkflowCreateRequest']

/** Process/Action step (rectangle) – single action in the flow */
interface ActionStep {
  id: string
  kind: 'action'
  type: string
  params: Record<string, unknown>
}

const MAX_DECISION_BRANCHES = 3

/** Decision step (diamond) – up to 3 connectors to action/decision shapes */
interface DecisionStep {
  id: string
  kind: 'decision'
  condition: string
  /** Step IDs this decision connects to (max 3) */
  branches: string[]
}

type Step = ActionStep | DecisionStep

function isActionStep(s: Step): s is ActionStep {
  return s.kind === 'action'
}

function isDecisionStep(s: Step): s is DecisionStep {
  return s.kind === 'decision'
}

const FLOW_LAYOUT = {
  lr: {
    canvas: 'flex flex-row items-center justify-start pl-8 pr-8',
    mainContainer: 'flex flex-row items-center gap-0 flex-nowrap',
    stepWrapper: 'flex flex-row items-center gap-0 shrink-0 flex-wrap',
    branchWrapper: 'flex flex-row items-center gap-0 shrink-0',
  },
  tb: {
    canvas: 'flex flex-col items-center justify-start',
    mainContainer: 'flex flex-col items-center gap-0',
    stepWrapper: 'flex flex-col items-center shrink-0',
    branchWrapper: 'flex flex-col items-center shrink-0',
  },
} as const

function FlowArrow({ direction }: { direction: FlowDirection }) {
  if (direction === 'lr') {
    return (
      <div className="flex items-center flex-shrink-0 px-1" aria-hidden>
        <div className="w-6 h-px bg-muted-foreground/25" />
        <ArrowRight className="w-4 h-4 text-muted-foreground/40 shrink-0" strokeWidth={2} />
        <div className="w-6 h-px bg-muted-foreground/25" />
      </div>
    )
  }
  return (
    <div className="flex flex-col items-center flex-shrink-0" aria-hidden>
      <div className="w-px h-6 bg-muted-foreground/25" />
      <ArrowDown className="w-4 h-4 text-muted-foreground/40" strokeWidth={2} />
      <div className="w-px h-6 bg-muted-foreground/25" />
    </div>
  )
}

const BRANCH_LABELS = ['is true', 'is false', 'else'] as const

/** Curved connector from decision with label on the line (reference style) */
function BranchConnector({
  direction,
  branchIndex,
  label,
}: {
  direction: FlowDirection
  branchIndex: number
  label: string
}) {
  if (direction === 'lr') {
    const offset = branchIndex === 0 ? 8 : branchIndex === 1 ? 0 : -8
    const width = 52
    const height = 28
    const cy = height / 2 + offset
    const pathD = `M 0 ${height / 2} Q ${width / 2} ${cy} ${width} ${height / 2}`
    return (
      <div className="flex items-center flex-shrink-0 relative" style={{ width: width + 8 }}>
        <svg width={width} height={height} className="overflow-visible" aria-hidden="true">
          <path
            d={pathD}
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            className="text-muted-foreground/50"
          />
          <polygon
            points={`${width},${height / 2} ${width - 5},${height / 2 - 3} ${width - 5},${height / 2 + 3}`}
            fill="currentColor"
            className="text-muted-foreground/50"
          />
        </svg>
        <span
          className="absolute text-[10px] font-medium text-muted-foreground bg-background px-1.5 py-0.5 rounded border border-border/70 whitespace-nowrap shadow-sm"
          style={{ left: width / 2 - 24, top: height / 2 - 10 }}
        >
          ● {label}
        </span>
      </div>
    )
  }
  const offset = branchIndex === 0 ? -16 : branchIndex === 1 ? 0 : 16
  const width = 28
  const height = 48
  const cx = width / 2 + offset
  const pathD = `M ${width / 2} 0 Q ${cx} ${height / 2} ${width / 2} ${height}`
  return (
    <div
      className="flex flex-col items-center flex-shrink-0 relative"
      style={{ height: height + 8 }}
    >
      <svg width={width} height={height} className="overflow-visible" aria-hidden="true">
        <path
          d={pathD}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          className="text-muted-foreground/50"
        />
        <polygon
          points={`${width / 2},${height} ${width / 2 - 3},${height - 5} ${width / 2 + 3},${height - 5}`}
          fill="currentColor"
          className="text-muted-foreground/50"
        />
      </svg>
      <span
        className="absolute text-[10px] font-medium text-muted-foreground bg-background px-1.5 py-0.5 rounded border border-border/70 whitespace-nowrap shadow-sm"
        style={{ left: width / 2 - 22, top: height / 2 - 10 }}
      >
        ● {label}
      </span>
    </div>
  )
}

/** Small type label above a shape (e.g. "Launch action", "Check if / else") */
function ShapeTypeLabel({
  icon: Icon,
  label,
  className = '',
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  className?: string
}) {
  return (
    <div
      className={`flex items-center justify-center gap-1.5 text-muted-foreground mb-1.5 ${className}`}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span className="text-[11px] font-medium uppercase tracking-wide">{label}</span>
    </div>
  )
}

const ADD_STEP_BTN_CLASS =
  'flex items-center gap-2 px-4 py-3 rounded-xl border-2 border-dashed border-muted-foreground/30 text-muted-foreground hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-colors shrink-0'

function AddStepButtons({
  onAddAction,
  onAddDecision,
  disabled,
}: {
  onAddAction: () => void
  onAddDecision: () => void
  disabled?: boolean
}) {
  return (
    <div className="flex items-center gap-2 shrink-0 flex-nowrap">
      <button
        type="button"
        onClick={onAddAction}
        disabled={disabled}
        className={ADD_STEP_BTN_CLASS}
      >
        <Plus className="w-4 h-4" />
        <span className="text-sm font-medium">Add step</span>
      </button>
      <button
        type="button"
        onClick={onAddDecision}
        disabled={disabled}
        className={ADD_STEP_BTN_CLASS}
      >
        <GitBranch className="w-4 h-4" />
        <span className="text-sm font-medium">Add condition</span>
      </button>
    </div>
  )
}

/** Start shape (circle) with trigger – type label above like reference */
function StartShape({
  eventType,
  eventTypes,
  loading,
  onChange,
  disabled,
  direction,
}: {
  eventType: string
  eventTypes: string[]
  loading: boolean
  onChange: (value: string) => void
  disabled?: boolean
  direction: FlowDirection
}) {
  const selectEl = (
    <SingleSelectCombobox
      value={eventType}
      onValueChange={onChange}
      options={[
        { value: '', label: 'When event type…' },
        ...eventTypes.map((t) => ({ value: t, label: t })),
      ]}
      placeholder="When event type…"
      disabled={disabled || loading}
      className={
        direction === 'lr'
          ? 'w-44 text-sm rounded-lg border-border [color-scheme:inherit]'
          : 'w-56 text-sm rounded-lg border-border text-center [color-scheme:inherit]'
      }
    />
  )
  const circle = (
    <div className="flex flex-col items-center justify-center w-16 h-16 rounded-full bg-background border border-border shrink-0">
      <span className="text-xs font-semibold uppercase tracking-widest text-foreground">Start</span>
    </div>
  )
  const triggerBlock = (
    <div className="flex flex-col items-center shrink-0">
      <ShapeTypeLabel icon={Zap} label="Trigger" />
      {direction === 'lr' ? (
        <div className="flex flex-row items-center gap-3">
          {circle}
          {selectEl}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          {circle}
          {selectEl}
        </div>
      )}
    </div>
  )
  return triggerBlock
}

/** Action/Process shape (rectangle): definition lives inside the shape */
function ActionShape({
  step,
  isSelected,
  onSelect,
  onRemove,
  onUpdate,
  paramsInput,
  onParamsInputChange,
  disabled,
}: {
  step: ActionStep
  isSelected: boolean
  onSelect: () => void
  onRemove: () => void
  onUpdate: (updates: Partial<Pick<ActionStep, 'type' | 'params'>>) => void
  paramsInput: string
  onParamsInputChange: (value: string) => void
  disabled?: boolean
}) {
  const paramsId = useId()
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: step.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const { label: actionLabel, icon: ActionIcon } = getActionTypeInfo(step.type)

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex flex-col items-center w-[280px] min-w-[280px] shrink-0"
    >
      <ShapeTypeLabel icon={ActionIcon} label={actionLabel} />
      <fieldset
        onFocus={onSelect}
        className={`
          w-full min-w-0 rounded-xl border border-border bg-background overflow-hidden transition-all
          ${isSelected ? 'border-primary/50 ring-2 ring-primary/20' : 'hover:border-muted-foreground/40'}
        `}
      >
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border/60">
          <button
            type="button"
            className="p-1.5 touch-none cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground disabled:pointer-events-none rounded-md hover:bg-muted/60"
            aria-label="Drag to reorder"
            disabled={disabled}
            {...attributes}
            {...listeners}
            onClick={(e) => e.stopPropagation()}
          >
            <GripVertical className="w-4 h-4" />
          </button>
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10">
            <Zap className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <SingleSelectCombobox
              value={step.type}
              onValueChange={(v) => onUpdate({ type: v })}
              options={WORKFLOW_ACTION_TYPES.map((opt) => ({ value: opt.value, label: opt.label }))}
              placeholder="Action type"
              disabled={disabled}
              className="min-w-0 text-sm font-medium border-0 rounded-none bg-transparent py-1 h-auto cursor-pointer [&_[data-slot=input-group]]:border-0 [&_[data-slot=input-group]]:shadow-none"
            />
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onRemove()
              }}
              className="p-1.5 text-muted-foreground hover:text-destructive rounded-md hover:bg-destructive/10 transition-colors"
              aria-label="Remove"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="px-3 py-2 bg-muted/30">
          <label
            htmlFor={paramsId}
            className="block text-xs font-medium text-foreground uppercase tracking-wide mb-1"
          >
            Params
          </label>
          <Input
            id={paramsId}
            type="text"
            placeholder='{"key": "value"}'
            value={paramsInput}
            onChange={(e) => onParamsInputChange(e.target.value)}
            disabled={disabled}
            className="font-mono text-sm h-9 text-foreground placeholder:text-muted-foreground"
          />
          <p className="text-[10px] text-muted-foreground mt-1 leading-tight">
            For create_event: payload should match the target event type’s schema. Other actions:
            action-specific config.
          </p>
        </div>
      </fieldset>
    </div>
  )
}

/** Renders Action or Decision shape for a step (DRY: single place for step→shape mapping) */
function StepShape({
  step,
  isSelected,
  onSelect,
  onRemove,
  onUpdateAction,
  onUpdateDecision,
  onParamsInputChange,
  paramsInputValue,
  onAddBranch,
  disabled,
}: {
  step: Step
  isSelected: boolean
  onSelect: () => void
  onRemove: () => void
  onUpdateAction: (u: Partial<Pick<ActionStep, 'type' | 'params'>>) => void
  onUpdateDecision: (value: string) => void
  onParamsInputChange: (raw: string) => void
  paramsInputValue: string
  onAddBranch?: () => void
  disabled?: boolean
}) {
  if (isActionStep(step)) {
    return (
      <ActionShape
        step={step}
        isSelected={isSelected}
        onSelect={onSelect}
        onRemove={onRemove}
        onUpdate={onUpdateAction}
        paramsInput={paramsInputValue}
        onParamsInputChange={onParamsInputChange}
        disabled={disabled}
      />
    )
  }
  return (
    <DecisionShape
      step={step}
      isSelected={isSelected}
      onSelect={onSelect}
      onRemove={onRemove}
      onConditionChange={onUpdateDecision}
      onAddBranch={onAddBranch}
      disabled={disabled}
    />
  )
}

/** Decision shape (diamond) – flowchart symbol, up to 3 connectors to action shapes */
function DecisionShape({
  step,
  isSelected,
  onSelect,
  onRemove,
  onConditionChange,
  onAddBranch,
  disabled,
}: {
  step: DecisionStep
  isSelected: boolean
  onSelect: () => void
  onRemove: () => void
  onConditionChange: (value: string) => void
  onAddBranch?: () => void
  disabled?: boolean
}) {
  const branchCount = step.branches?.length ?? 0
  const canAddBranch = branchCount < MAX_DECISION_BRANCHES && onAddBranch && !disabled
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: step.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  // Diamond: flowchart decision symbol – condition text wraps, no box around component
  const w = 168
  const h = 112
  const points = `${w / 2},4 ${w - 4},${h / 2} ${w / 2},${h - 4} 4,${h / 2}`

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex flex-col items-center justify-center shrink-0"
    >
      <ShapeTypeLabel icon={Info} label="Check if / else" />
      <fieldset
        onFocus={onSelect}
        className="relative min-w-0 transition-colors outline-none border-0 ring-0"
      >
        <svg
          width={w}
          height={h}
          viewBox={`0 0 ${w} ${h}`}
          aria-hidden="true"
          className="overflow-visible"
        >
          <polygon
            points={points}
            fill="var(--card)"
            stroke="currentColor"
            strokeWidth={1.5}
            className={
              isSelected
                ? 'stroke-primary/60 text-primary/60'
                : 'stroke-border text-border hover:stroke-muted-foreground/50'
            }
          />
        </svg>
        <div
          className="absolute inset-0 flex flex-col items-center justify-center p-3 pt-4 pointer-events-none box-border"
          style={{ width: w, height: h }}
        >
          <textarea
            value={step.condition}
            onChange={(e) => onConditionChange(e.target.value)}
            placeholder="e.g. payload.amount > 100"
            disabled={disabled}
            rows={3}
            className="w-full min-w-0 max-w-[136px] min-h-[3.25rem] text-xs text-center font-mono text-foreground placeholder:text-muted-foreground pointer-events-auto bg-transparent border-0 shadow-none resize-none rounded-none py-1 px-2 break-words focus:outline-none focus:ring-0"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
        <div className="absolute top-1 right-1 flex gap-0.5 pointer-events-auto">
          <button
            type="button"
            className="p-1 touch-none cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground hover:bg-muted/50 disabled:pointer-events-none rounded border-0 bg-transparent"
            aria-label="Drag to reorder"
            disabled={disabled}
            {...attributes}
            {...listeners}
            onClick={(e) => e.stopPropagation()}
          >
            <GripVertical className="w-3.5 h-3.5" />
          </button>
          {canAddBranch && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onAddBranch()
              }}
              className="p-1 text-muted-foreground hover:text-primary hover:bg-muted/50 rounded border-0 bg-transparent text-[10px] font-medium"
              aria-label="Add branch"
              title={`Add branch (${branchCount}/${MAX_DECISION_BRANCHES})`}
            >
              <Plus className="w-3 h-3" />
            </button>
          )}
          {!disabled && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onRemove()
              }}
              className="p-1 text-muted-foreground hover:text-destructive hover:bg-muted/50 rounded border-0 bg-transparent"
              aria-label="Remove"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </fieldset>
    </div>
  )
}

export interface WorkflowCreateModalProps {
  onClose: () => void
  onSubmit: (data: WorkflowCreate) => Promise<boolean>
  title?: string
}

export function WorkflowCreateModal({
  onClose,
  onSubmit,
  title = 'Create workflow',
}: WorkflowCreateModalProps) {
  const descriptionOptionalId = useId()
  const flowDirectionId = useId()
  const workflowNameId = useId()
  const { types: eventTypes, loading: loadingEventTypes } = useEventTypes()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [flowDirection, setFlowDirection] = useState<FlowDirection>('lr')
  const [triggerEventType, setTriggerEventType] = useState('')
  const [steps, setSteps] = useState<Step[]>([])
  /** Ordered IDs for the main flow (branch steps are only in decision.branches) */
  const [mainFlowStepIds, setMainFlowStepIds] = useState<string[]>([])
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null)
  const [isActive, setIsActive] = useState(true)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [paramsInput, setParamsInput] = useState('')

  const { execute, loading, error, setError } = useFormSubmit()

  useEffect(() => {
    const step = steps.find((s) => s.id === selectedStepId)
    if (step && isActionStep(step)) {
      setParamsInput(
        Object.keys(step.params).length === 0 ? '' : JSON.stringify(step.params, null, 0),
      )
    } else {
      setParamsInput('')
    }
  }, [selectedStepId, steps])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      setMainFlowStepIds((prev) => {
        const oldIndex = prev.indexOf(active.id as string)
        const newIndex = prev.indexOf(over.id as string)
        if (oldIndex === -1 || newIndex === -1) return prev
        return arrayMove(prev, oldIndex, newIndex)
      })
    }
  }

  const getStep = (id: string): Step | undefined => steps.find((s) => s.id === id)

  const getParamsInputForStep = (step: ActionStep): string =>
    selectedStepId === step.id
      ? paramsInput
      : Object.keys(step.params).length === 0
        ? ''
        : JSON.stringify(step.params, null, 0)

  const stepToPayloadEntries = (
    step: Step,
    get: (id: string) => Step | undefined,
  ): { type: string; params: Record<string, unknown> | null }[] => {
    if (isActionStep(step)) {
      return [{ type: step.type, params: step.params || null }]
    }
    const entries: { type: string; params: Record<string, unknown> | null }[] = [
      { type: 'condition', params: { expression: step.condition } },
    ]
    for (const branchId of step.branches ?? []) {
      const b = get(branchId)
      if (!b) continue
      if (isActionStep(b)) {
        entries.push({ type: b.type, params: b.params || null })
      } else {
        entries.push({ type: 'condition', params: { expression: b.condition } })
      }
    }
    return entries
  }

  const addAction = () => {
    const newStep: ActionStep = {
      id: `action-${Date.now()}`,
      kind: 'action',
      type: 'create_event',
      params: {},
    }
    setSteps((prev) => [...prev, newStep])
    setMainFlowStepIds((prev) => [...prev, newStep.id])
    setSelectedStepId(newStep.id)
    setFieldErrors((e) => ({ ...e, steps: '' }))
  }

  const addDecision = () => {
    const newStep: DecisionStep = {
      id: `decision-${Date.now()}`,
      kind: 'decision',
      condition: '',
      branches: [],
    }
    setSteps((prev) => [...prev, newStep])
    setMainFlowStepIds((prev) => [...prev, newStep.id])
    setSelectedStepId(newStep.id)
    setFieldErrors((e) => ({ ...e, steps: '' }))
  }

  const removeStep = (id: string) => {
    setMainFlowStepIds((prev) => prev.filter((sid) => sid !== id))
    setSteps((prev) =>
      prev
        .filter((s) => s.id !== id)
        .map((s) =>
          isDecisionStep(s) ? { ...s, branches: s.branches.filter((b) => b !== id) } : s,
        ),
    )
    if (selectedStepId === id) setSelectedStepId(null)
  }

  const addBranchToDecision = (decisionId: string) => {
    const candidate = steps.find((s) => s.id === decisionId && isDecisionStep(s))
    const decision = candidate && isDecisionStep(candidate) ? candidate : null
    if (!decision || decision.branches.length >= MAX_DECISION_BRANCHES) return
    const newStep: ActionStep = {
      id: `action-${Date.now()}`,
      kind: 'action',
      type: 'create_event',
      params: {},
    }
    setSteps((prev) => {
      const updated = prev.map((s) =>
        s.id === decisionId && isDecisionStep(s)
          ? { ...s, branches: [...s.branches, newStep.id] }
          : s,
      )
      return [...updated, newStep]
    })
    setSelectedStepId(newStep.id)
  }

  const updateActionStep = (id: string, updates: Partial<Pick<ActionStep, 'type' | 'params'>>) => {
    setSteps((prev) => prev.map((s) => (s.id === id && isActionStep(s) ? { ...s, ...updates } : s)))
  }

  const updateDecisionStep = (id: string, condition: string) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === id && isDecisionStep(s) ? { ...s, condition } : s)),
    )
  }

  const handleParamsInput = (id: string, raw: string) => {
    setParamsInput(raw)
    const trimmed = raw.trim()
    if (!trimmed) {
      updateActionStep(id, { params: {} })
      return
    }
    try {
      const parsed = JSON.parse(trimmed) as Record<string, unknown>
      updateActionStep(id, { params: parsed })
    } catch {
      // allow typing invalid JSON
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const errors: Record<string, string> = {}
    if (!name.trim()) errors.name = 'Workflow name is required'
    if (!triggerEventType.trim()) errors.triggerEventType = 'Trigger (event type) is required'
    if (mainFlowStepIds.length === 0) errors.steps = 'Add at least one step (action or condition)'

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    const actionsPayload = mainFlowStepIds.flatMap((id) => {
      const step = getStep(id)
      return step ? stepToPayloadEntries(step, getStep) : []
    })

    const { actions, errors: actionErrors } = toApiActions(actionsPayload)
    if (actionErrors.length > 0) {
      setFieldErrors({ steps: actionErrors[0] })
      return
    }

    const payload: WorkflowCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      trigger_event_type: triggerEventType,
      actions,
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

  const sortStrategy =
    flowDirection === 'lr' ? horizontalListSortingStrategy : verticalListSortingStrategy

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={title}
      maxWidth="max-w-6xl"
      closeButton={!loading}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Workflow name + description: compact bar above canvas */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[200px]">
            <label
              htmlFor={workflowNameId}
              className="block text-xs font-medium text-muted-foreground mb-1"
            >
              Workflow name
            </label>
            <Input
              id={workflowNameId}
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                setFieldErrors((e) => ({ ...e, name: '' }))
              }}
              placeholder="e.g. Alert on high priority"
              disabled={loading}
              className={fieldErrors.name ? 'border-destructive' : ''}
            />
            {fieldErrors.name && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.name}</p>
            )}
          </div>
          <div className="flex-1 min-w-[200px]">
            <label
              htmlFor={descriptionOptionalId}
              className="block text-xs font-medium text-muted-foreground mb-1"
            >
              Description (optional)
            </label>
            <Input
              id={descriptionOptionalId}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Short description"
              disabled={loading}
            />
          </div>
          <div className="shrink-0">
            <label
              htmlFor={flowDirectionId}
              className="block text-xs font-medium text-muted-foreground mb-1"
            >
              Flow direction
            </label>
            <SingleSelectCombobox
              id={flowDirectionId}
              value={flowDirection}
              onValueChange={(v) => setFlowDirection((v || 'lr') as FlowDirection)}
              options={[
                { value: 'lr', label: 'Left to right' },
                { value: 'tb', label: 'Top to bottom' },
              ]}
              placeholder="Flow direction"
              disabled={loading}
              className="w-[180px]"
            />
          </div>
        </div>

        {/* ERD-style canvas: shapes drawn from start */}
        <div
          className="relative min-h-[360px] rounded-xl border border-border/60 overflow-hidden bg-muted/40 text-muted-foreground/[0.2]"
          style={{
            backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)',
            backgroundSize: '16px 16px',
          }}
        >
          <div
            className={`absolute inset-0 overflow-auto pt-8 pb-8 ${FLOW_LAYOUT[flowDirection].canvas}`}
          >
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <div className={FLOW_LAYOUT[flowDirection].mainContainer}>
                <div className="shrink-0">
                  <StartShape
                    eventType={triggerEventType}
                    eventTypes={eventTypes}
                    loading={loadingEventTypes}
                    onChange={(v) => {
                      setTriggerEventType(v)
                      setFieldErrors((e) => ({ ...e, triggerEventType: '' }))
                    }}
                    disabled={loading}
                    direction={flowDirection}
                  />
                </div>

                {mainFlowStepIds.length > 0 && (
                  <>
                    <FlowArrow direction={flowDirection} />
                    <SortableContext items={mainFlowStepIds} strategy={sortStrategy}>
                      {mainFlowStepIds.map((stepId) => {
                        const step = getStep(stepId)
                        if (!step) return null
                        const isDecisionWithBranches =
                          isDecisionStep(step) && (step.branches?.length ?? 0) > 0
                        const layout = FLOW_LAYOUT[flowDirection]
                        return (
                          <div key={step.id} className={layout.stepWrapper}>
                            <StepShape
                              step={step}
                              isSelected={selectedStepId === step.id}
                              onSelect={() => setSelectedStepId(step.id)}
                              onRemove={() => removeStep(step.id)}
                              onUpdateAction={(u) => updateActionStep(step.id, u)}
                              onUpdateDecision={(value) => updateDecisionStep(step.id, value)}
                              onParamsInputChange={(raw) => handleParamsInput(step.id, raw)}
                              paramsInputValue={
                                isActionStep(step) ? getParamsInputForStep(step) : ''
                              }
                              onAddBranch={
                                isDecisionStep(step)
                                  ? () => addBranchToDecision(step.id)
                                  : undefined
                              }
                              disabled={loading}
                            />
                            {isDecisionWithBranches && isDecisionStep(step)
                              ? (step.branches ?? []).map((branchId, branchIdx) => {
                                  const branchStep = getStep(branchId)
                                  if (!branchStep) return null
                                  const branchLabel =
                                    BRANCH_LABELS[branchIdx] ?? `Branch ${branchIdx + 1}`
                                  return (
                                    <div key={branchId} className={layout.branchWrapper}>
                                      <BranchConnector
                                        direction={flowDirection}
                                        branchIndex={branchIdx}
                                        label={branchLabel}
                                      />
                                      <FlowArrow direction={flowDirection} />
                                      <StepShape
                                        step={branchStep}
                                        isSelected={selectedStepId === branchStep.id}
                                        onSelect={() => setSelectedStepId(branchStep.id)}
                                        onRemove={() => removeStep(branchStep.id)}
                                        onUpdateAction={(u) => updateActionStep(branchStep.id, u)}
                                        onUpdateDecision={(value) =>
                                          updateDecisionStep(branchStep.id, value)
                                        }
                                        onParamsInputChange={(raw) =>
                                          handleParamsInput(branchStep.id, raw)
                                        }
                                        paramsInputValue={
                                          isActionStep(branchStep)
                                            ? getParamsInputForStep(branchStep)
                                            : ''
                                        }
                                        disabled={loading}
                                      />
                                    </div>
                                  )
                                })
                              : null}
                            <FlowArrow direction={flowDirection} />
                          </div>
                        )
                      })}
                    </SortableContext>
                    <FlowArrow direction={flowDirection} />
                    <AddStepButtons
                      onAddAction={addAction}
                      onAddDecision={addDecision}
                      disabled={loading}
                    />
                  </>
                )}

                {mainFlowStepIds.length === 0 && (
                  <>
                    <FlowArrow direction={flowDirection} />
                    <AddStepButtons
                      onAddAction={addAction}
                      onAddDecision={addDecision}
                      disabled={loading}
                    />
                  </>
                )}
              </div>
            </DndContext>
          </div>
        </div>

        {(fieldErrors.triggerEventType || fieldErrors.steps) && (
          <p className="text-xs text-destructive">
            {fieldErrors.triggerEventType || fieldErrors.steps}
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
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create workflow'}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  )
}
