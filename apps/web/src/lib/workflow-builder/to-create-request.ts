/**
 * Convert graph Workflow to API WorkflowCreateRequest shape.
 * Traverses from trigger, emits actions + conditions in execution order.
 */

import type { components } from '@/lib/timeline-api'
import { nodeRegistry } from './node-registry'
import type { Workflow, WorkflowEdge } from './types'

export type ApiWorkflowAction =
  | components['schemas']['CreateEventAction']
  | components['schemas']['NotifyAction']
  | components['schemas']['CreateTaskAction']

export interface WorkflowActionItem {
  type: string
  params?: Record<string, unknown> | null
}

/**
 * Traverse from startId and append action items in order.
 * For conditions we emit one condition entry then recurse into true then false branches.
 */
function collectActions(workflow: Workflow, startId: string, out: WorkflowActionItem[]): void {
  const node = workflow.nodes.find((n) => n.id === startId)
  if (!node) return
  const desc = nodeRegistry.getOptional(node.type)
  if (desc?.isTrigger || desc?.isTerminal) return
  if (desc?.isCondition) {
    out.push({
      type: 'condition',
      params: { expression: (node.configuration?.expression as string) ?? '' },
    })
    const edges = workflow.edges.filter((e) => e.from === node.id) as WorkflowEdge[]
    const trueEdge = edges.find((e) => e.label === 'true')
    const falseEdge = edges.find((e) => e.label === 'false')
    if (trueEdge?.to) collectActions(workflow, trueEdge.to, out)
    if (falseEdge?.to) collectActions(workflow, falseEdge.to, out)
    return
  }
  // action or integration_action
  const type =
    node.type === 'integration_action'
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
  trigger_conditions?: Record<string, unknown> | null
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
  const result: {
    trigger_event_type: string
    actions: WorkflowActionItem[]
    trigger_conditions?: Record<string, unknown> | null
  } = { trigger_event_type, actions }
  if (workflow.triggerConditions !== undefined) {
    result.trigger_conditions = workflow.triggerConditions
  }
  return result
}

/**
 * Narrow builder actions to the three the API accepts, collecting a reason for each
 * one it rejects.
 *
 * The builder emits whatever a node was configured with, including condition nodes,
 * so an unsupported action reached the API as a 422 with no indication of which
 * step caused it.
 */
export function toApiActions(items: WorkflowActionItem[]): {
  actions: ApiWorkflowAction[]
  errors: string[]
} {
  const actions: ApiWorkflowAction[] = []
  const errors: string[] = []
  const params = (item: WorkflowActionItem) => (item.params ?? {}) as Record<string, unknown>
  const text = (value: unknown) => (typeof value === 'string' && value.trim() ? value : null)

  items.forEach((item, index) => {
    const at = `Step ${index + 1}`
    const p = params(item)

    if (item.type === 'create_event') {
      const eventType = text(p.event_type)
      if (!eventType) {
        errors.push(`${at}: create_event needs an event type`)
        return
      }
      actions.push({
        type: 'create_event',
        params: {
          event_type: eventType,
          schema_version: typeof p.schema_version === 'number' ? p.schema_version : 1,
          ...(p.payload ? { payload: p.payload as Record<string, unknown> } : {}),
        },
      })
      return
    }

    if (item.type === 'notify') {
      const role = text(p.role)
      const template = text(p.template)
      if (!role || !template) {
        errors.push(`${at}: notify needs a role and a template`)
        return
      }
      actions.push({
        type: 'notify',
        params: { role, template, ...(p.data ? { data: p.data as Record<string, unknown> } : {}) },
      })
      return
    }

    if (item.type === 'create_task') {
      const title = text(p.title)
      if (!title) {
        errors.push(`${at}: create_task needs a title`)
        return
      }
      actions.push({
        type: 'create_task',
        params: {
          title,
          ...(text(p.assigned_to_role) ? { assigned_to_role: p.assigned_to_role as string } : {}),
          ...(text(p.assigned_to_user_id)
            ? { assigned_to_user_id: p.assigned_to_user_id as string }
            : {}),
          ...(text(p.due_at) ? { due_at: p.due_at as string } : {}),
        },
      })
      return
    }

    errors.push(`${at}: the API does not accept "${item.type}" actions`)
  })

  return { actions, errors }
}
