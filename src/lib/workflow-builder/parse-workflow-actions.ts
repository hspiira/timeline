/**
 * Parse workflow actions (from API WorkflowResponse) into a list of steps for the flow execution UI.
 * Supports the sentence-like workflow shape: params.stepName, stepDescription, condition, tasks.
 */

export interface ParsedWorkflowTask {
  name: string
  requireDocument: boolean
}

export interface ParsedWorkflowStep {
  index: number
  name: string
  description?: string
  condition?: string
  tasks: ParsedWorkflowTask[]
  /** Optional: step id to go to on reject (from params.reject_to_step_id). */
  rejectToStepId?: string
}

type ActionLike = { type?: string; params?: Record<string, unknown> }

/**
 * Extract steps from workflow actions. Handles create_event-style actions with
 * params.stepName, stepDescription, condition, tasks (from workflow requirements form).
 */
export function getStepsFromWorkflowActions(actions: unknown): ParsedWorkflowStep[] {
  if (!Array.isArray(actions) || actions.length === 0) return []

  const steps: ParsedWorkflowStep[] = []
  actions.forEach((action: unknown, index: number) => {
    const a = action as ActionLike
    const params = a?.params ?? {}
    const stepName = typeof params.stepName === 'string' ? params.stepName : `Step ${index + 1}`
    const tasksRaw = Array.isArray(params.tasks) ? params.tasks : []
    const tasks: ParsedWorkflowTask[] = tasksRaw.map((t: unknown) => {
      const task = t as Record<string, unknown>
      const name = typeof task.name === 'string' ? task.name : 'Task'
      const docIds = task.documentIds
      const requireDocument = Array.isArray(docIds) && docIds.length > 0
      return { name, requireDocument }
    })

    steps.push({
      index,
      name: stepName,
      description: typeof params.stepDescription === 'string' ? params.stepDescription : undefined,
      condition: typeof params.condition === 'string' ? params.condition : undefined,
      tasks,
      rejectToStepId:
        typeof params.reject_to_step_id === 'string' ? params.reject_to_step_id : undefined,
    })
  })

  return steps
}
