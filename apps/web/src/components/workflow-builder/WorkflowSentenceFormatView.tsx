/**
 * Renders a workflow in sentence format: steps with status (checkmark / spinner / pending),
 * conditions, mandatory/optional, and hierarchical sub-steps. Use for agent-style run views.
 */

import { Check, Circle, Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'
import {
  getSentenceSegments,
  type StepRequirement,
  type StepStatus,
  type WorkflowSentenceFormat,
  type WorkflowStepSentence,
} from '@/lib/workflow-builder/workflow-sentence-format'

// --- Status icon ---

function StatusIcon({ status }: { status: StepStatus }) {
  const size = 'w-4 h-4'
  const baseClass = 'shrink-0 text-muted-foreground'
  if (status === 'completed') {
    return (
      <Check
        className={`${size} ${baseClass} text-emerald-600 dark:text-emerald-400`}
        aria-label="Completed"
      />
    )
  }
  if (status === 'in_progress') {
    return (
      <Loader2
        className={`${size} ${baseClass} animate-spin text-primary`}
        aria-label="In progress"
      />
    )
  }
  return (
    <Circle className={`${size} ${baseClass} opacity-60`} strokeWidth={2} aria-label="Pending" />
  )
}

// --- Requirement badge ---

function RequirementBadge({ requirement }: { requirement: StepRequirement }) {
  if (requirement === 'optional') {
    return (
      <span className="shrink-0 rounded border border-amber-200/80 bg-amber-50/80 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-300">
        Optional
      </span>
    )
  }
  return (
    <span className="shrink-0 rounded border border-border bg-muted/50 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
      Required
    </span>
  )
}

// --- Sentence with variable chips (inline) ---

function SentenceWithChips({
  template,
  variables = {},
  className = '',
}: {
  template: string
  variables?: Record<string, string | number | boolean>
  className?: string
}) {
  if (!template.trim()) return null
  const segments = getSentenceSegments(template, variables)
  return (
    <span className={`inline-flex flex-wrap items-baseline gap-x-1 gap-y-0.5 ${className}`}>
      {segments.map((seg, i) =>
        seg.type === 'text' ? (
          // biome-ignore lint/suspicious/noArrayIndexKey: read-only list, replaced wholesale rather than reordered in place.
          <span key={i}>{seg.value}</span>
        ) : (
          <span
            // biome-ignore lint/suspicious/noArrayIndexKey: read-only list, replaced wholesale rather than reordered in place.
            key={i}
            className="inline-flex rounded-md border border-border bg-muted/60 px-1.5 py-0.5 text-[11px] font-medium text-foreground/90"
          >
            {seg.displayValue ?? `{{${seg.value}}}`}
          </span>
        ),
      )}
    </span>
  )
}

// --- Single step row (with optional condition line) ---

function StepRow({
  step,
  depth,
  showRequirement,
}: {
  step: WorkflowStepSentence
  depth: number
  showRequirement?: boolean
}) {
  const indent = depth * 20

  return (
    <div className="flex flex-col gap-0.5">
      {/* Optional condition line (e.g. "When connected to Datadog successfully ✓") */}
      {step.condition?.sentenceTemplate.trim() && (
        <div className="flex items-center gap-2 py-0.5" style={{ paddingLeft: indent + 24 }}>
          {step.condition.met === true ? (
            <Check
              className="h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
              aria-hidden
            />
          ) : (
            <Circle
              className="h-3.5 w-3.5 shrink-0 text-muted-foreground/50"
              strokeWidth={2}
              aria-hidden
            />
          )}
          <SentenceWithChips
            template={step.condition.sentenceTemplate}
            variables={step.condition.sentenceVariables}
            className="text-[11px] text-muted-foreground italic"
          />
        </div>
      )}
      {/* Main step line */}
      <div
        className="flex items-start gap-2 py-1 pr-2"
        style={{ paddingLeft: indent }}
        data-step-id={step.id}
      >
        <span className="flex h-6 items-center shrink-0">
          <StatusIcon status={step.status} />
        </span>
        <div className="min-w-0 flex-1">
          <SentenceWithChips
            template={step.sentenceTemplate}
            variables={step.sentenceVariables}
            className="text-[13px] text-foreground"
          />
          {showRequirement && (
            <span className="ml-2 inline-flex items-center">
              <RequirementBadge requirement={step.requirement} />
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Recursive step list ---

function StepList({
  steps,
  depth,
  showRequirement,
}: {
  steps: WorkflowStepSentence[]
  depth: number
  showRequirement?: boolean
}) {
  return (
    <>
      {steps.map((step) => (
        <div key={step.id}>
          <StepRow step={step} depth={depth} showRequirement={showRequirement} />
          {step.subSteps != null && step.subSteps.length > 0 && (
            <StepList steps={step.subSteps} depth={depth + 1} showRequirement={showRequirement} />
          )}
        </div>
      ))}
    </>
  )
}

// --- Public component ---

export interface WorkflowSentenceFormatViewProps {
  /** The workflow in sentence format (title + steps). */
  data: WorkflowSentenceFormat
  /** Show "Required" / "Optional" badge on each step. */
  showRequirement?: boolean
  /** Optional header content (e.g. "Analyzing..." with spinner and "2 MIN REMAINING"). */
  header?: ReactNode
  className?: string
}

/**
 * Renders a full workflow in sentence format: title, optional header, then steps
 * with status icons (checkmark / spinner / pending), conditions, mandatory/optional,
 * and nested sub-steps with indentation.
 */
export function WorkflowSentenceFormatView({
  data,
  showRequirement = true,
  header,
  className = '',
}: WorkflowSentenceFormatViewProps) {
  const { title, steps } = data

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {title != null && title !== '' && (
        <div className="flex items-center gap-2 pb-1">
          {header}
          <span className="text-sm font-medium text-foreground">{title}</span>
        </div>
      )}
      {header != null && (title == null || title === '') && <div className="pb-1">{header}</div>}
      <div className="flex flex-col">
        <StepList steps={steps} depth={0} showRequirement={showRequirement} />
      </div>
    </div>
  )
}
