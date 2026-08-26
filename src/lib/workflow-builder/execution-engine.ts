/**
 * Execution Engine Layer – traverse graph from trigger, evaluate conditions,
 * execute actions sequentially, stop at terminal.
 * Modular: action execution is injected via executor.
 */

import { nodeRegistry } from './node-registry'
import type { Workflow, WorkflowEdge, WorkflowNode } from './types'

export interface ExecutionContext {
  /** Accumulated payload or state passed between steps */
  payload: Record<string, unknown>
  /** Current step index in execution order */
  stepIndex: number
}

export type ActionExecutor = (
  node: WorkflowNode,
  context: ExecutionContext,
) => Promise<Record<string, unknown> | undefined>

/** Condition evaluator: expression + context -> boolean */
export type ConditionEvaluator = (expression: string, context: ExecutionContext) => boolean

/** Get next node id(s) from this node. For conditions, returns one id based on evaluation. */
function getNextNodeIds(
  workflow: Workflow,
  nodeId: string,
  node: WorkflowNode,
  context: ExecutionContext,
  conditionEvaluator: ConditionEvaluator,
): string[] {
  const desc = nodeRegistry.getOptional(node.type)
  if (desc?.isCondition) {
    const edges = workflow.edges.filter((e) => e.from === nodeId) as WorkflowEdge[]
    const trueEdge = edges.find((e) => e.label === 'true')
    const falseEdge = edges.find((e) => e.label === 'false')
    const expression = (node.configuration?.expression as string) ?? ''
    const result = conditionEvaluator(expression, context)
    const nextId = result ? trueEdge?.to : falseEdge?.to
    return nextId ? [nextId] : []
  }
  const fromEdges = workflow.edges.filter((e) => e.from === nodeId).map((e) => e.to)
  const fromConnections = node.outgoingConnections ?? []
  return [...new Set([...fromEdges, ...fromConnections])]
}

export interface ExecutionResult {
  success: boolean
  context: ExecutionContext
  executedNodeIds: string[]
  error?: string
}

/**
 * Execute workflow: start from trigger, evaluate conditions, run actions, stop at terminal.
 * Injected: actionExecutor, conditionEvaluator.
 */
export async function executeWorkflow(
  workflow: Workflow,
  actionExecutor: ActionExecutor,
  conditionEvaluator: ConditionEvaluator,
  initialPayload: Record<string, unknown> = {},
): Promise<ExecutionResult> {
  const triggers = workflow.nodes.filter((n) => nodeRegistry.getOptional(n.type)?.isTrigger)
  if (triggers.length === 0) {
    return {
      success: false,
      context: { payload: initialPayload, stepIndex: 0 },
      executedNodeIds: [],
      error: 'No trigger node',
    }
  }
  const trigger = triggers[0]!
  const context: ExecutionContext = { payload: { ...initialPayload }, stepIndex: 0 }
  const executedNodeIds: string[] = []
  let stepIndex = 0
  const queue: string[] = [trigger.id]

  while (queue.length > 0) {
    const id = queue.shift()!
    const node = workflow.nodes.find((n) => n.id === id)
    if (!node) continue

    context.stepIndex = stepIndex++
    const desc = nodeRegistry.getOptional(node.type)
    if (desc?.isTerminal) break
    if (desc?.isTrigger) {
      const nextIds = getNextNodeIds(workflow, node.id, node, context, conditionEvaluator)
      queue.push(...nextIds)
      continue
    }
    if (desc?.isCondition) {
      const nextIds = getNextNodeIds(workflow, node.id, node, context, conditionEvaluator)
      queue.push(...nextIds)
      continue
    }
    try {
      const updates = await actionExecutor(node, context)
      if (updates && typeof updates === 'object') {
        context.payload = { ...context.payload, ...updates }
      }
      executedNodeIds.push(node.id)
      const nextIds = getNextNodeIds(workflow, node.id, node, context, conditionEvaluator)
      queue.push(...nextIds)
    } catch (err) {
      return {
        success: false,
        context,
        executedNodeIds,
        error: err instanceof Error ? err.message : String(err),
      }
    }
  }

  return {
    success: true,
    context,
    executedNodeIds,
  }
}

/** Default condition evaluator: simple expression (e.g. payload.x > 0). For production, use a safe expression evaluator. */
export function defaultConditionEvaluator(expression: string, context: ExecutionContext): boolean {
  if (!expression.trim()) return false
  try {
    const fn = new Function('payload', `return Boolean(${expression})`)
    return fn(context.payload)
  } catch {
    return false
  }
}
