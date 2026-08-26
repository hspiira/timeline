/**
 * Validation Service – workflow-level rules:
 * Exactly one trigger, all branches terminate or rejoin, no orphan nodes.
 * Condition nodes: exactly two outgoing edges with labels "true" and "false".
 */

import { nodeRegistry } from './node-registry'
import type { Workflow, WorkflowNode } from './types'

export interface ValidationResult {
  valid: boolean
  errors: string[]
}

function getTriggerNodes(workflow: Workflow): WorkflowNode[] {
  return workflow.nodes.filter((n) => nodeRegistry.getOptional(n.type)?.isTrigger)
}

function getTerminalNodes(workflow: Workflow): WorkflowNode[] {
  return workflow.nodes.filter((n) => nodeRegistry.getOptional(n.type)?.isTerminal)
}

function getConditionNodes(workflow: Workflow): WorkflowNode[] {
  return workflow.nodes.filter((n) => nodeRegistry.getOptional(n.type)?.isCondition)
}

/** All node ids that are targets of some edge (or trigger start). */
function reachableFromTrigger(workflow: Workflow): Set<string> {
  const triggerNodes = getTriggerNodes(workflow)
  if (triggerNodes.length === 0) return new Set()
  const reached = new Set<string>()
  const queue = triggerNodes.map((n) => n.id)
  queue.forEach((id) => {
    reached.add(id)
  })
  while (queue.length > 0) {
    const id = queue.shift()!
    const node = workflow.nodes.find((n) => n.id === id)
    if (!node) continue
    for (const toId of node.outgoingConnections ?? []) {
      if (!reached.has(toId)) {
        reached.add(toId)
        queue.push(toId)
      }
    }
    for (const e of workflow.edges.filter((e) => e.from === id)) {
      if (!reached.has(e.to)) {
        reached.add(e.to)
        queue.push(e.to)
      }
    }
  }
  return reached
}

/** Nodes that are not reachable from any trigger. */
function orphanNodes(workflow: Workflow): WorkflowNode[] {
  const reached = reachableFromTrigger(workflow)
  return workflow.nodes.filter((n) => !reached.has(n.id))
}

/** Check that every path from trigger eventually hits a terminal or rejoins a visited node (no infinite loops). */
function allBranchesTerminateOrRejoin(workflow: Workflow): boolean {
  const triggerNodes = getTriggerNodes(workflow)
  if (triggerNodes.length === 0) return true
  const terminals = new Set(getTerminalNodes(workflow).map((n) => n.id))
  const visited = new Set<string>()
  function dfs(id: string): boolean {
    if (terminals.has(id)) return true
    if (visited.has(id)) return true
    visited.add(id)
    const node = workflow.nodes.find((n) => n.id === id)
    if (!node) return true
    const desc = nodeRegistry.getOptional(node.type)
    if (desc?.isTerminal) return true
    const outgoing = [
      ...(node.outgoingConnections ?? []),
      ...workflow.edges.filter((e) => e.from === id).map((e) => e.to),
    ]
    const uniqueOut = [...new Set(outgoing)]
    if (uniqueOut.length === 0 && !desc?.isTerminal) return false
    return uniqueOut.every((toId) => dfs(toId))
  }
  return triggerNodes.every((t) => dfs(t.id))
}

/** User-facing validation messages for non-technical users. */
export function validateWorkflow(workflow: Workflow): ValidationResult {
  const errors: string[] = []
  const triggers = getTriggerNodes(workflow)
  if (triggers.length === 0) {
    errors.push(
      'Add a trigger (when an event happens), then add at least one step and connect them.',
    )
  }
  if (triggers.length > 1) {
    errors.push('Only one trigger is allowed. Remove the extra trigger or merge the workflow.')
  }

  for (const node of getConditionNodes(workflow)) {
    const edgesFrom = workflow.edges.filter((e) => e.from === node.id)
    const hasTrue = edgesFrom.some((e) => e.label === 'true')
    const hasFalse = edgesFrom.some((e) => e.label === 'false')
    if (!hasTrue || !hasFalse) {
      errors.push(
        'Connect both outcomes for this condition: one for when it’s true (Yes), one for when it’s false (No).',
      )
      break
    }
    if (edgesFrom.length > 2) {
      errors.push('A condition can only have two outcomes: Yes and No. Remove extra connections.')
      break
    }
  }

  const orphans = orphanNodes(workflow)
  if (orphans.length > 0) {
    errors.push(
      'Some steps aren’t connected from the start. Connect them from the trigger or remove them.',
    )
  }

  if (!allBranchesTerminateOrRejoin(workflow)) {
    errors.push(
      'Every path should eventually reach an end. Add an End step to any branch that doesn’t.',
    )
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}
