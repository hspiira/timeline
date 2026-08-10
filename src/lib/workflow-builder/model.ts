/**
 * Workflow Model Layer – immutable workflow updates.
 * Single responsibility: workflow CRUD in memory.
 */

import type { Workflow, WorkflowNode, WorkflowEdge, Position } from './types'
import { createNode, createEdge } from './types'

export function addNode(
  workflow: Workflow,
  node: WorkflowNode
): Workflow {
  if (workflow.nodes.some((n) => n.id === node.id)) return workflow
  return {
    ...workflow,
    nodes: [...workflow.nodes, node],
  }
}

export function updateNode(
  workflow: Workflow,
  nodeId: string,
  updates: Partial<Pick<WorkflowNode, 'position' | 'configuration' | 'outgoingConnections'>>
): Workflow {
  const nodes = workflow.nodes.map((n) =>
    n.id === nodeId ? { ...n, ...updates } : n
  )
  return { ...workflow, nodes }
}

export function removeNode(workflow: Workflow, nodeId: string): Workflow {
  const nodes = workflow.nodes.filter((n) => n.id !== nodeId)
  const edges = workflow.edges.filter((e) => e.from !== nodeId && e.to !== nodeId)
  return { ...workflow, nodes, edges }
}

export function addEdge(
  workflow: Workflow,
  edge: WorkflowEdge
): Workflow {
  if (workflow.edges.some((e) => e.id === edge.id)) return workflow
  const fromNode = workflow.nodes.find((n) => n.id === edge.from)
  const updatedNodes = fromNode
    ? workflow.nodes.map((n) =>
        n.id === edge.from
          ? {
              ...n,
              outgoingConnections: [...(n.outgoingConnections ?? []), edge.to],
            }
          : n
      )
    : workflow.nodes
  return {
    ...workflow,
    nodes: updatedNodes,
    edges: [...workflow.edges, edge],
  }
}

export function removeEdge(workflow: Workflow, edgeId: string): Workflow {
  const edge = workflow.edges.find((e) => e.id === edgeId)
  if (!edge) return workflow
  const edges = workflow.edges.filter((e) => e.id !== edgeId)
  const nodes = workflow.nodes.map((n) => {
    if (n.id !== edge.from) return n
    const outgoing = (n.outgoingConnections ?? []).filter((id) => id !== edge.to)
    return { ...n, outgoingConnections: outgoing }
  })
  return { ...workflow, nodes, edges }
}

export function setNodePosition(
  workflow: Workflow,
  nodeId: string,
  position: Position
): Workflow {
  return updateNode(workflow, nodeId, { position })
}

export function setWorkflowName(workflow: Workflow, name: string): Workflow {
  return { ...workflow, name }
}

/** Factory helpers for model layer (no UI) */
export const modelHelpers = {
  createNode,
  createEdge,
}
