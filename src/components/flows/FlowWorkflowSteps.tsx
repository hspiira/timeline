/**
 * Workflow execution view for the flow page: shows steps derived from the workflow's
 * actions and lets users advance (Complete step) or go back (Reject). Progress is
 * persisted in localStorage keyed by flowId.
 */

import { CheckCircle2, ChevronRight, FileText, ListTodo, RotateCcw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import type { FlowDocumentComplianceResponse } from '@/lib/types'
import { cn } from '@/lib/utils'
import {
  getStepsFromWorkflowActions,
  type ParsedWorkflowStep,
} from '@/lib/workflow-builder/parse-workflow-actions'

const STORAGE_KEY_PREFIX = 'flow-execution-'

function loadExecutionState(
  flowId: string,
): { completedIndices: number[]; currentIndex: number } | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${flowId}`)
    if (!raw) return null
    const data = JSON.parse(raw) as {
      completedIndices?: number[]
      currentIndex?: number
    }
    return {
      completedIndices: Array.isArray(data.completedIndices) ? data.completedIndices : [],
      currentIndex:
        typeof data.currentIndex === 'number' && data.currentIndex >= 0 ? data.currentIndex : 0,
    }
  } catch {
    return null
  }
}

function saveExecutionState(flowId: string, completedIndices: number[], currentIndex: number) {
  try {
    localStorage.setItem(
      `${STORAGE_KEY_PREFIX}${flowId}`,
      JSON.stringify({ completedIndices, currentIndex }),
    )
  } catch {
    // ignore
  }
}

export interface FlowWorkflowStepsProps {
  flowId: string
  workflow: { actions?: unknown } | null
  compliance?: FlowDocumentComplianceResponse | null
  complianceLoading?: boolean
  onCompleteStep?: (stepIndex: number) => void
  onRejectStep?: (stepIndex: number, targetStepIndex: number) => void
  eventCount?: number
}

export function FlowWorkflowSteps({
  flowId,
  workflow,
  compliance = null,
  complianceLoading = false,
  onCompleteStep,
  onRejectStep,
}: FlowWorkflowStepsProps) {
  const steps = useMemo(() => getStepsFromWorkflowActions(workflow?.actions), [workflow?.actions])

  const [state, setState] = useState<{
    completedIndices: number[]
    currentIndex: number
  }>(() => {
    const saved = loadExecutionState(flowId)
    if (saved) return saved
    return { completedIndices: [], currentIndex: 0 }
  })

  /** Accordion open value: single step open at a time, default to current step. */
  const [openStepValue, setOpenStepValue] = useState<string>('0')

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

  /** Keep accordion open value in sync with current step when it changes. */
  const currentIndex = state.currentIndex
  useEffect(() => {
    if (steps.length > 0) {
      const valid = Math.min(Math.max(0, currentIndex), steps.length - 1)
      setOpenStepValue(String(valid))
    }
  }, [currentIndex, steps.length])

  const persist = useCallback(
    (completedIndices: number[], currentIndex: number) => {
      saveExecutionState(flowId, completedIndices, currentIndex)
    },
    [flowId],
  )

  const handleCompleteStep = useCallback(() => {
    const { completedIndices, currentIndex } = state
    if (currentIndex < 0 || currentIndex >= steps.length) return
    const nextCompleted = [...completedIndices, currentIndex]
    const nextCurrent = Math.min(currentIndex + 1, steps.length - 1)
    setState({ completedIndices: nextCompleted, currentIndex: nextCurrent })
    persist(nextCompleted, nextCurrent)
    setOpenStepValue(String(nextCurrent))
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
      setOpenStepValue(String(targetStepIndex))
      onRejectStep?.(state.currentIndex, targetStepIndex)
    },
    [state, persist, onRejectStep],
  )

  const isStepCompleted = useCallback(
    (index: number) => state.completedIndices.includes(index),
    [state.completedIndices],
  )

  const isCurrentStep = useCallback(
    (index: number) => state.currentIndex === index,
    [state.currentIndex],
  )

  const currentStep = steps[currentIndex]
  const currentStepHasDocumentRequirement =
    currentStep?.tasks.some((t) => t.requireDocument) ?? false
  const isDocumentBlocked =
    currentStepHasDocumentRequirement && !!compliance && !compliance.all_satisfied

  if (steps.length === 0) return null

  const completedCount = state.completedIndices.length
  const progressPercent = steps.length > 0 ? (completedCount / steps.length) * 100 : 0

  return (
    <section className="space-y-1">
      <div className="flex items-center justify-between gap-2 mb-4">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <ListTodo className="w-5 h-5 text-primary/80" />
          Workflow steps
        </h2>
        <span className="text-xs text-muted-foreground">
          {completedCount} of {steps.length} completed
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div
          className="h-2 w-full rounded-full bg-muted overflow-hidden"
          role="progressbar"
          aria-valuenow={completedCount}
          aria-valuemin={0}
          aria-valuemax={steps.length}
          aria-label={`${completedCount} of ${steps.length} steps completed`}
        >
          <div
            className="h-full bg-primary transition-[width] duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      <div className="relative border border-border/60 rounded-xl bg-card/80 overflow-hidden">
        <Accordion
          type="single"
          collapsible={true}
          value={openStepValue}
          onValueChange={(v) => v !== '' && setOpenStepValue(v)}
          className="w-full"
        >
          <div className="divide-y divide-border/50">
            {steps.map((step, index) => (
              <AccordionItem key={step.index} value={String(index)} className="border-b-0">
                <AccordionTrigger className="flex items-center px-3 py-1 hover:no-underline [&[data-state=open]]:bg-primary/5 [&[data-state=open]]:dark:bg-primary/10">
                  <div className="flex items-center gap-1.5 text-left w-full">
                    <div
                      className={cn(
                        'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-semibold transition-colors leading-none',
                        isStepCompleted(index) &&
                          'border-green-500/80 bg-green-500/10 text-green-700 dark:text-green-400',
                        isCurrentStep(index) &&
                          !isStepCompleted(index) &&
                          'border-primary bg-primary/10 text-primary',
                        !isCurrentStep(index) &&
                          !isStepCompleted(index) &&
                          'border-muted-foreground/30 bg-muted/30 text-muted-foreground',
                      )}
                    >
                      {isStepCompleted(index) ? (
                        <CheckCircle2 className="h-3 w-3 text-green-600 dark:text-green-400" />
                      ) : (
                        <span>{index + 1}</span>
                      )}
                    </div>
                    <span
                      className={cn(
                        'text-sm font-medium',
                        isStepCompleted(index) && 'text-muted-foreground',
                        isCurrentStep(index) && !isStepCompleted(index) && 'text-foreground',
                      )}
                    >
                      {step.name}
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-2 pt-0">
                  <StepRow
                    step={step}
                    stepNumber={index + 1}
                    isCompleted={isStepCompleted(index)}
                    isCurrent={isCurrentStep(index)}
                    onComplete={isCurrentStep(index) ? handleCompleteStep : undefined}
                    onReject={
                      isCurrentStep(index) && index > 0 ? () => handleReject(index - 1) : undefined
                    }
                    rejectTargetLabel={index > 0 ? `Step ${index}` : undefined}
                    documentBlocked={isCurrentStep(index) && isDocumentBlocked}
                    complianceLoading={isCurrentStep(index) && complianceLoading}
                    blockedReasons={compliance?.blocked_reasons?.slice(0, 1) ?? []}
                  />
                </AccordionContent>
              </AccordionItem>
            ))}
          </div>
        </Accordion>
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
  documentBlocked?: boolean
  complianceLoading?: boolean
  blockedReasons?: string[]
}

function StepRow({
  step,
  stepNumber: _stepNumber,
  isCompleted: _isCompleted,
  isCurrent,
  onComplete,
  onReject,
  rejectTargetLabel,
  documentBlocked = false,
  complianceLoading = false,
  blockedReasons = [],
}: StepRowProps) {
  return (
    <div className="space-y-2">
      <div>
        {step.description && (
          <p className="text-sm text-muted-foreground mt-0.5">{step.description}</p>
        )}
        {step.condition && (
          <p className="text-xs text-muted-foreground/90 mt-1 italic">{step.condition}</p>
        )}
      </div>

      {step.tasks.length > 0 && (
        <ul className="space-y-1">
          {step.tasks.map((task, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
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
          {complianceLoading && (
            <p className="text-xs text-muted-foreground">Checking documents…</p>
          )}
          {!complianceLoading && documentBlocked && (
            <p className="text-sm text-amber-600 dark:text-amber-400">
              Document requirements must be satisfied before completing this step.
              {blockedReasons[0] && (
                <span className="block mt-0.5 text-muted-foreground">{blockedReasons[0]}</span>
              )}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            {onComplete && (
              <Button
                size="sm"
                onClick={onComplete}
                variant="primary"
                disabled={complianceLoading || documentBlocked}
              >
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
        </div>
      )}
    </div>
  )
}
