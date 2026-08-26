/**
 * Robust sentence-format model for workflows.
 * Supports: status (pending / in progress / completed), conditions, mandatory/optional
 * requirements, and hierarchical sub-steps. Use for agent-style run views and logs.
 */

import {
  getSentenceSegments,
  parseTemplateVariables,
  type SentenceSegment,
  substituteSentence,
} from './sentence-templates'

/** Step status for UI: empty circle (pending), spinner (in progress), checkmark (completed). */
export type StepStatus = 'pending' | 'in_progress' | 'completed'

/** Whether the step is required for the flow or optional. */
export type StepRequirement = 'mandatory' | 'optional'

/** Condition that gates this step (e.g. "When connected to Datadog successfully"). */
export interface StepCondition {
  /** Human-language template, e.g. "When {{connection_status}}" */
  sentenceTemplate: string
  sentenceVariables?: Record<string, string | number | boolean>
  /** Whether the condition is met (e.g. show checkmark when true). */
  met?: boolean
}

/** A single step in the sentence-format workflow: sentence + status + requirement + optional condition + sub-steps. */
export interface WorkflowStepSentence {
  id: string
  /** Human-language template with {{variable}} placeholders. */
  sentenceTemplate: string
  sentenceVariables?: Record<string, string | number | boolean>
  /** Display/execution status. */
  status: StepStatus
  /** Is this step required for the flow to proceed? */
  requirement: StepRequirement
  /** Optional condition that gates this step (shown above/before the step). */
  condition?: StepCondition
  /** Nested sub-steps (hierarchical). */
  subSteps?: WorkflowStepSentence[]
}

/** Root structure: optional title + list of top-level steps. */
export interface WorkflowSentenceFormat {
  /** Optional overall title (e.g. "Analyzing..."). */
  title?: string
  /** Top-level steps (each may have subSteps). */
  steps: WorkflowStepSentence[]
}

// --- Builder API (immutable updates) ---

let idCounter = 0
function nextId(): string {
  idCounter += 1
  return `step-${idCounter}-${Date.now().toString(36)}`
}

/**
 * Create a new step. Use requirement 'mandatory' for required steps, 'optional' for optional.
 */
export function createStep(
  sentenceTemplate: string,
  options: {
    id?: string
    sentenceVariables?: Record<string, string | number | boolean>
    status?: StepStatus
    requirement?: StepRequirement
    condition?: StepCondition
    subSteps?: WorkflowStepSentence[]
  } = {},
): WorkflowStepSentence {
  const {
    id = nextId(),
    sentenceVariables,
    status = 'pending',
    requirement = 'mandatory',
    condition,
    subSteps,
  } = options
  return {
    id,
    sentenceTemplate,
    sentenceVariables,
    status,
    requirement,
    ...(condition != null && { condition }),
    ...(subSteps != null && subSteps.length > 0 && { subSteps }),
  }
}

/**
 * Create a condition object (e.g. "When {{field}} is {{value}}").
 */
export function createCondition(
  sentenceTemplate: string,
  sentenceVariables?: Record<string, string | number | boolean>,
  met?: boolean,
): StepCondition {
  return { sentenceTemplate, sentenceVariables, met }
}

/** Update a step's status. Returns a new step object. */
export function setStepStatus(
  step: WorkflowStepSentence,
  status: StepStatus,
): WorkflowStepSentence {
  return { ...step, status }
}

/** Update a step's condition met flag. Returns a new step object. */
export function setConditionMet(step: WorkflowStepSentence, met: boolean): WorkflowStepSentence {
  if (!step.condition) return step
  return {
    ...step,
    condition: { ...step.condition, met },
  }
}

/** Add or replace sub-steps. Returns a new step object. */
export function setSubSteps(
  step: WorkflowStepSentence,
  subSteps: WorkflowStepSentence[],
): WorkflowStepSentence {
  return { ...step, subSteps: subSteps.length > 0 ? subSteps : undefined }
}

/** Update variables on a step. Returns a new step object. */
export function setStepVariables(
  step: WorkflowStepSentence,
  variables: Record<string, string | number | boolean>,
): WorkflowStepSentence {
  return { ...step, sentenceVariables: { ...step.sentenceVariables, ...variables } }
}

// --- Validation ---

export interface StepValidation {
  valid: boolean
  errors: string[]
}

/** Validate a single step: template non-empty, condition has template if present, sub-steps validated. */
export function validateStep(step: WorkflowStepSentence): StepValidation {
  const errors: string[] = []
  if (!step.sentenceTemplate.trim()) {
    errors.push(`Step ${step.id}: sentenceTemplate is required`)
  }
  if (step.condition != null && !step.condition.sentenceTemplate.trim()) {
    errors.push(`Step ${step.id}: condition must have a sentenceTemplate`)
  }
  if (step.subSteps != null) {
    for (const sub of step.subSteps) {
      const subVal = validateStep(sub)
      if (!subVal.valid) errors.push(...subVal.errors)
    }
  }
  return { valid: errors.length === 0, errors }
}

/** Validate a full workflow sentence format. */
export function validateWorkflowSentenceFormat(root: WorkflowSentenceFormat): StepValidation {
  const errors: string[] = []
  for (const step of root.steps) {
    const v = validateStep(step)
    if (!v.valid) errors.push(...v.errors)
  }
  return { valid: errors.length === 0, errors }
}

// --- Flatten for display / iteration (optional) ---

/** Flatten steps and sub-steps into a list with depth for indentation. */
export function flattenSteps(
  steps: WorkflowStepSentence[],
  depth = 0,
): Array<{ step: WorkflowStepSentence; depth: number }> {
  const out: Array<{ step: WorkflowStepSentence; depth: number }> = []
  for (const step of steps) {
    out.push({ step, depth })
    if (step.subSteps?.length) {
      out.push(...flattenSteps(step.subSteps, depth + 1))
    }
  }
  return out
}

// --- Re-export segment helpers for renderers ---

export { substituteSentence, getSentenceSegments, parseTemplateVariables, type SentenceSegment }
