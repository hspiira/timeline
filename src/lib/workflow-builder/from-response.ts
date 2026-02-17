/**
 * Convert API WorkflowResponse to our graph Workflow model.
 * Builds a linear chain: trigger -> step1 -> step2 -> ...
 * Conditions get true -> next step, false -> terminal.
 */

import type { Workflow, WorkflowNode, WorkflowEdge } from './types'
import { createNode, createEdge } from './types'

type ApiAction = { type?: string; params?: Record<string, unknown> | null }
type WorkflowResponseLike = {
  id: string
  name: string
  trigger_event_type: string
  actions: ApiAction[]
}

const STEP_DY = 140

function nodeId(prefix: string, index: number): string {
  return `${prefix}-${index}`
}

/**
 * Build a Workflow graph from an API workflow response.
 */
export function workflowFromResponse(res: WorkflowResponseLike): Workflow {
  const nodes: WorkflowNode[] = []
  const edges: WorkflowEdge[] = []
  const triggerId = nodeId('trigger', 0)
  const triggerNode = createNode(triggerId, 'trigger', { x: 0, y: 0 }, {
    eventType: res.trigger_event_type ?? '',
  })
  nodes.push(triggerNode)

  if (!res.actions?.length) {
    return { id: res.id, name: res.name, nodes, edges }
  }

  let prevId: string = triggerId
  let prevWasCondition = false
  let y = STEP_DY

  for (let i = 0; i < res.actions.length; i++) {
    const action = res.actions[i]
    const type = (action?.type as string) ?? 'create_event'
    const params = (action?.params as Record<string, unknown>) ?? {}
    const id = nodeId('step', i)

    if (type === 'condition') {
      const expression = (params?.expression as string) ?? ''
      const condNode = createNode(id, 'condition', { x: 0, y }, { expression })
      nodes.push(condNode)
      edges.push(createEdge(`e-${prevId}-${id}`, prevId, id, prevWasCondition ? 'true' : undefined))
      const falseTerminalId = nodeId('term-false', i)
      const falseTermNode = createNode(falseTerminalId, 'terminal', { x: 200, y: y + STEP_DY }, {})
      nodes.push(falseTermNode)
      edges.push(createEdge(`e-${id}-false`, id, falseTerminalId, 'false'))
      const hasNext = i + 1 < res.actions.length
      if (!hasNext) {
        const trueTerminalId = nodeId('term-true', i)
        const trueTermNode = createNode(trueTerminalId, 'terminal', { x: -200, y: y + STEP_DY }, {})
        nodes.push(trueTermNode)
        edges.push(createEdge(`e-${id}-true`, id, trueTerminalId, 'true'))
      }
      prevId = id
      prevWasCondition = true
      y += STEP_DY
      continue
    }

    const isIntegration = type !== 'create_event' && type !== 'send_email' && type !== 'update_subject'
    const nodeType = isIntegration ? 'integration_action' : 'action'
    const config: Record<string, unknown> = isIntegration
      ? { operation: type, integration: '', params }
      : { actionType: type, params }
    const stepNode = createNode(id, nodeType, { x: 0, y }, config)
    nodes.push(stepNode)
    edges.push(createEdge(`e-${prevId}-${id}`, prevId, id, prevWasCondition ? 'true' : undefined))
    prevId = id
    prevWasCondition = false
    y += STEP_DY
  }

  return { id: res.id, name: res.name, nodes, edges }
}
