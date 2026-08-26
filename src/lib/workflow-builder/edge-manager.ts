/**
 * Edge Manager – add/remove edges, validate connections, optional cycle detection.
 */

import { nodeRegistry } from './node-registry'
import type { Workflow } from './types'

export interface ConnectionValidation {
  valid: boolean
  error?: string
}

/** Check if adding edge (fromId -> toId) would create a cycle (i.e. toId can reach fromId). */
function wouldCreateCycle(workflow: Workflow, fromId: string, toId: string): boolean {
  const visited = new Set<string>()
  function canReachFromTo(id: string): boolean {
    if (id === fromId) return true
    if (visited.has(id)) return false
    visited.add(id)
    for (const e of workflow.edges.filter((e) => e.from === id)) {
      if (canReachFromTo(e.to)) return true
    }
    return false
  }
  return canReachFromTo(toId)
}

/** Validate if an edge can be added. Set allowCircular to true to skip cycle check. */
export function validateConnection(
  workflow: Workflow,
  fromId: string,
  toId: string,
  label?: 'true' | 'false',
  allowCircular = false,
): ConnectionValidation {
  const fromNode = workflow.nodes.find((n) => n.id === fromId)
  const toNode = workflow.nodes.find((n) => n.id === toId)
  if (!fromNode) return { valid: false, error: 'Source node not found' }
  if (!toNode) return { valid: false, error: 'Target node not found' }
  if (fromId === toId) return { valid: false, error: 'Cannot connect node to itself' }

  const desc = nodeRegistry.getOptional(fromNode.type)
  if (desc?.isTerminal) return { valid: false, error: 'Terminal nodes cannot have outgoing edges' }
  if (desc?.isCondition && label == null)
    return { valid: false, error: 'Condition edges must have label "true" or "false"' }
  if (desc?.isCondition) {
    const existing = workflow.edges.filter((e) => e.from === fromId)
    const hasTrue = existing.some((e) => e.label === 'true')
    const hasFalse = existing.some((e) => e.label === 'false')
    if (label === 'true' && hasTrue)
      return { valid: false, error: 'Condition already has a "true" edge' }
    if (label === 'false' && hasFalse)
      return { valid: false, error: 'Condition already has a "false" edge' }
  }

  if (!allowCircular && wouldCreateCycle(workflow, fromId, toId)) {
    return { valid: false, error: 'Connection would create a cycle' }
  }
  return { valid: true }
}

export function generateEdgeId(): string {
  return `e-${crypto.randomUUID()}`
}
