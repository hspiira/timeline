/**
 * Workflow execution view for the flow page: shows steps derived from the workflow's
 * actions and lets users advance (Complete step) or go back (Reject). Progress is
 * persisted in localStorage keyed by flowId.
 */

import { useCallback, useMemo, useState, useEffect } from 'react'
import {
  CheckCircle2,
  ListTodo,
  ChevronRight,
  FileText,
  RotateCcw,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  getStepsFromWorkflowActions,
  type ParsedWorkflowStep,
} from '@/lib/workflow-builder/parse-workflow-actions'

const STORAGE_KEY_PREFIX = 'flow-execution-'

function loadExecutionState(
  flowId: string
): { completedIndices: number[]; currentIndex: number } | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${flowId}`)
    if (!raw) return null
    const data = JSON.parse(raw) as {
      completedIndices?: number[]
      currentIndex?: number
    }
    return {
      completedIndices: Array.isArray(data.completedIndices)
        ? data.completedIndices
        : [],
      currentIndex:
        typeof data.currentIndex === 'number' && data.currentIndex >= 0
          ? data.currentIndex
          : 0,
    }
  } catch {
    return null
  }
}

function saveExecutionState(
  flowId: string,
  completedIndices: number[],
  currentIndex: number
) {
  try {
    localStorage.setItem(
      `${STORAGE_KEY_PREFIX}${flowId}`,
      JSON.stringify({ completedIndices, currentIndex })
    )
  } catch {
    // ignore
  }
}

export interface FlowWorkflowStepsProps {
  flowId: string
  workflow: { actions?: unknown } | null
  onCompleteStep?: (stepIndex: number) => void
  onRejectStep?: (stepIndex: number, targetStepIndex: number) => void
  eventCount?: number
}

export function FlowWorkflowSteps({
  flowId,
  workflow,
  onCompleteStep,
  onRejectStep,
}: FlowWorkflowStepsProps) {
  const steps = useMemo(
    () => getStepsFromWorkflowActions(workflow?.actions),
    [workflow?.actions]
  )

  const [state, setState] = useState<{
    completedIndices: number[]
    currentIndex: number
  }>(() => {
    const saved = loadExecutionState(flowId)
    if (saved) return saved
    return { completedIndices: [], currentIndex: 0 }
  })

  useEffect(() => {
    const saved = loadExecutionState(flowId)
    if (saved && steps.length > 0) {
      const maxCur = Math.min(saved.currentIndex, steps.length - 1)
      setState({
        completedIndices: saved.completedIndices,
        currentIndex: maxCur,
      })
    }
  }, [flowId, steps.length])

  const persist = useCallback(
    (completedIndices: number[], currentIndex: number) => {
      saveExecutionState(flowId, completedIndices, currentIndex)
    },
    [flowId]
  )

  const handleCompleteStep = useCallback(() => {
    const { completedIndices, currentIndex } = state
    if (currentIndex < 0 || currentIndex >= steps.length) return
    const nextCompleted = [...completedIndices, currentIndex]
    const nextCurrent = Math.min(currentIndex + 1, steps.length - 1)
    setState({ completedIndices: nextCompleted, currentIndex: nextCurrent })
    persist(nextCompleted, nextCurrent)
    onCompleteStep?.(currentIndex)
  }, [state, steps.length, persist, onCompleteStep])

  const handleReject = useCallback(
    (targetStepIndex: number) => {
      const { completedIndices } = state
      const nextCompleted = completedIndices.filter((i) => i < targetStepIndex)
      setState({
        completedIndices: nextCompleted,
        currentIndex: targetStepIndex,
      })
      persist(nextCompleted, targetStepIndex)
      onRejectStep?.(state.currentIndex, targetStepIndex)
    },
    [state, persist, onRejectStep]
  )

  const isStepCompleted = useCallback(
    (index: number) => state.completedIndices.includes(index),
    [state.completedIndices]
  )

  const isCurrentStep = useCallback(
    (index: number) => state.currentIndex === index,
    [state.currentIndex]
  )

  if (steps.length === 0) return null

  return (
    <section className="space-y-1">
      <div className="flex items-center justify-between gap-2 mb-4">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <ListTodo className="w-5 h-5 text-primary/80" />
          Workflow steps
        </h2>
        <span className="text-xs text-muted-foreground">
          {state.completedIndices.length} of {steps.length} completed
        </span>
      </div>

      <div className="relative border border-border/60 rounded-xl bg-card/80 overflow-hidden">
        <div className="divide-y divide-border/50">
          {steps.map((step, index) => (
            <StepRow
              key={step.index}
              step={step}
              stepNumber={index + 1}
              isCompleted={isStepCompleted(index)}
              isCurrent={isCurrentStep(index)}
              onComplete={
                isCurrentStep(index) ? handleCompleteStep : undefined
              }
              onReject={
                isCurrentStep(index) && index > 0
                  ? () => handleReject(index - 1)
                  : undefined
              }
              rejectTargetLabel={index > 0 ? `Step ${index}` : undefined}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

interface StepRowProps {
  step: ParsedWorkflowStep
  stepNumber: number
  isCompleted: boolean
  isCurrent: boolean
  onComplete?: () => void
  onReject?: () => void
  rejectTargetLabel?: string
}

function StepRow({
  step,
  stepNumber,
  isCompleted,
  isCurrent,
  onComplete,
  onReject,
  rejectTargetLabel,
}: StepRowProps) {
  return (
    <div
      className={cn(
        'flex gap-4 px-5 py-4 transition-colors',
        isCurrent && 'bg-primary/5 dark:bg-primary/10',
        isCompleted && !isCurrent && 'bg-muted/20'
      )}
    >
      <div className="flex flex-col items-center shrink-0 pt-0.5">
        <div
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors',
            isCompleted &&
              'border-green-500/80 bg-green-500/10 text-green-700 dark:text-green-400',
            isCurrent &&
              !isCompleted &&
              'border-primary bg-primary/10 text-primary',
            !isCurrent &&
              !isCompleted &&
              'border-muted-foreground/30 bg-muted/30 text-muted-foreground'
          )}
        >
          {isCompleted ? (
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
          ) : (
            <span>{stepNumber}</span>
          )}
        </div>
      </div>

      <div className="flex-1 min-w-0 space-y-2">
        <div>
          <h3
            className={cn(
              'font-medium text-foreground',
              isCompleted && 'text-muted-foreground'
            )}
          >
            {step.name}
          </h3>
          {step.description && (
            <p className="text-sm text-muted-foreground mt-0.5">
              {step.description}
            </p>
          )}
          {step.condition && (
            <p className="text-xs text-muted-foreground/90 mt-1 italic">
              {step.condition}
            </p>
          )}
        </div>

        {step.tasks.length > 0 && (
          <ul className="space-y-1">
            {step.tasks.map((task, i) => (
              <li
                key={i}
                className="flex items-center gap-2 text-sm text-muted-foreground"
              >
                <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-60" />
                <span>{task.name}</span>
                {task.requireDocument && (
                  <FileText className="h-3.5 w-3.5 shrink-0 text-amber-600/80 dark:text-amber-400/80" />
                )}
              </li>
            ))}
          </ul>
        )}

        {isCurrent && (onComplete || onReject) && (
          <div className="flex flex-wrap items-center gap-2 pt-2">
            {onComplete && (
              <Button size="sm" onClick={onComplete} variant="primary">
                Complete step
              </Button>
            )}
            {onReject && (
              <Button
                size="sm"
                onClick={onReject}
                variant="outline"
                className="text-muted-foreground"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                {rejectTargetLabel ? `Reject to ${rejectTargetLabel}` : 'Reject'}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
