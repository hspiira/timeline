/**
 * Natural-language workflow requirements: no visual graph.
 * Specify: workflow title/name, steps (name + description), tasks with variables
 * (subjects, payload), and documents attached to tasks.
 */

/** Variable value for a task (e.g. subject id, payload JSON). */
export type TaskVariableValue = string | number | boolean | Record<string, unknown>

/** A task under a step. Has name, optional description, variables (e.g. subjects, payload), and optional document refs. */
export interface WorkflowTaskRequirement {
  id: string
  name: string
  description?: string
  /** Variables such as subjects, payload – key/value. */
  variables?: Record<string, TaskVariableValue>
  /** Document IDs or refs attached to this task. */
  documentIds?: string[]
}

/** A step: name, description slot, optional condition, optional reject routing, and optional tasks. */
export interface WorkflowStepRequirement {
  id: string
  name: string
  description?: string
  /** Optional condition (e.g. "when previous step succeeded", "payload.status === 'active'"). */
  condition?: string
  /** Optional step id to go to on reject (for engine routing). */
  reject_to_step_id?: string
  tasks?: WorkflowTaskRequirement[]
}

/** Full workflow requirements: title, optional description, trigger event type, ordered steps (each with name, description, tasks). */
export interface WorkflowRequirements {
  /** Workflow title/name. */
  name: string
  description?: string
  /** Event type that starts this workflow (required for API create). */
  trigger_event_type?: string
  steps: WorkflowStepRequirement[]
}

// --- Ids ---

let idCounter = 0
function nextId(prefix: string): string {
  idCounter += 1
  return `${prefix}-${idCounter}-${Date.now().toString(36)}`
}

export function createStepRequirement(
  name: string,
  options: {
    id?: string
    description?: string
    condition?: string
    tasks?: WorkflowTaskRequirement[]
  } = {},
): WorkflowStepRequirement {
  const { id = nextId('step'), description, condition, tasks } = options
  return {
    id,
    name,
    ...(description != null && { description }),
    ...(condition != null && condition.trim() !== '' && { condition: condition.trim() }),
    ...(tasks != null && tasks.length > 0 && { tasks }),
  }
}

export function createTaskRequirement(
  name: string,
  options: {
    id?: string
    description?: string
    variables?: Record<string, TaskVariableValue>
    documentIds?: string[]
  } = {},
): WorkflowTaskRequirement {
  const { id = nextId('task'), description, variables, documentIds } = options
  return {
    id,
    name,
    ...(description != null && { description }),
    ...(variables != null && Object.keys(variables).length > 0 && { variables }),
    ...(documentIds != null && documentIds.length > 0 && { documentIds }),
  }
}

export function createEmptyWorkflowRequirements(name: string = ''): WorkflowRequirements {
  return { name, steps: [] }
}

/** Convert requirements to API WorkflowCreateRequest. Steps become actions with params capturing name, description, tasks (variables, documentIds). */
export function requirementsToCreateRequest(
  requirements: WorkflowRequirements,
  options: { defaultTriggerEventType?: string } = {},
): {
  name: string
  description?: string
  trigger_event_type: string
  actions: Array<{ type: string; params?: Record<string, unknown> }>
} {
  const trigger = requirements.trigger_event_type?.trim() || options.defaultTriggerEventType || ''
  const actions = requirements.steps.map((step) => ({
    type: 'create_event' as const,
    params: {
      stepName: step.name,
      stepDescription: step.description,
      condition: step.condition,
      ...(step.reject_to_step_id != null && { reject_to_step_id: step.reject_to_step_id }),
      tasks: (step.tasks ?? []).map((t) => ({
        name: t.name,
        description: t.description,
        variables: t.variables,
        documentIds: t.documentIds,
      })),
    },
  }))
  return {
    name: requirements.name,
    description: requirements.description,
    trigger_event_type: trigger,
    actions,
  }
}

// --- Validation ---

export interface ValidationResult {
  valid: boolean
  errors: string[]
}

export function validateWorkflowRequirements(data: WorkflowRequirements): ValidationResult {
  const errors: string[] = []
  if (!data.name.trim()) errors.push('Workflow name is required')
  if (!data.trigger_event_type?.trim()) errors.push('Trigger event type is required')
  data.steps.forEach((step, i) => {
    if (!step.name.trim()) errors.push(`Step ${i + 1}: name is required`)
    step.tasks?.forEach((task, j) => {
      if (!task.name.trim()) errors.push(`Step ${i + 1}, task ${j + 1}: name is required`)
    })
  })
  return { valid: errors.length === 0, errors }
}
