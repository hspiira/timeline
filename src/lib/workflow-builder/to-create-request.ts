/**
 * Convert graph Workflow to API WorkflowCreateRequest shape.
 * Traverses from trigger, emits actions + conditions in execution order.
 */

import type { Workflow, WorkflowEdge } from './types'
import { nodeRegistry } from './node-registry'

export interface WorkflowActionItem {
  type: string
  params?: Record<string, unknown> | null
}

/**
 * Traverse from startId and append action items in order.
 * For conditions we emit one condition entry then recurse into true then false branches.
 */
function collectActions(
  workflow: Workflow,
  startId: string,
  out: WorkflowActionItem[]
): void {
  const node = workflow.nodes.find((n) => n.id === startId)
  if (!node) return
  const desc = nodeRegistry.getOptional(node.type)
  if (desc?.isTrigger || desc?.isTerminal) return
  if (desc?.isCondition) {
    out.push({ type: 'condition', params: { expression: (node.configuration?.expression as string) ?? '' } })
    const edges = workflow.edges.filter((e) => e.from === node.id) as WorkflowEdge[]
    const trueEdge = edges.find((e) => e.label === 'true')
    const falseEdge = edges.find((e) => e.label === 'false')
    if (trueEdge?.to) collectActions(workflow, trueEdge.to, out)
    if (falseEdge?.to) collectActions(workflow, falseEdge.to, out)
    return
  }
  // action or integration_action
  const type = node.type === 'integration_action'
    ? (node.configuration?.operation as string) || node.type
    : (node.configuration?.actionType as string) || node.type
  const params = (node.configuration?.params as Record<string, unknown>) ?? {}
  out.push({ type, params: Object.keys(params).length ? params : null })
  const nextIds = [
    ...(node.outgoingConnections ?? []),
    ...workflow.edges.filter((e) => e.from === node.id).map((e) => e.to),
  ]
  const seen = new Set<string>()
  for (const toId of nextIds) {
    if (seen.has(toId)) continue
    seen.add(toId)
    collectActions(workflow, toId, out)
  }
}

export function workflowGraphToCreateRequest(workflow: Workflow): {
  trigger_event_type: string
  actions: WorkflowActionItem[]
} | null {
  const trigger = workflow.nodes.find((n) => nodeRegistry.getOptional(n.type)?.isTrigger)
  if (!trigger) return null
  const trigger_event_type = (trigger.configuration?.eventType as string) ?? ''
  const actions: WorkflowActionItem[] = []
  const nextIds = [
    ...(trigger.outgoingConnections ?? []),
    ...workflow.edges.filter((e) => e.from === trigger.id).map((e) => e.to),
  ]
  const seen = new Set<string>()
  for (const toId of nextIds) {
    if (seen.has(toId)) continue
    seen.add(toId)
    collectActions(workflow, toId, actions)
  }
  return { trigger_event_type, actions }
}
