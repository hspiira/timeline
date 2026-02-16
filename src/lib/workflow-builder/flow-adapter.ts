/**
 * Adapter between our Workflow model and React Flow nodes/edges.
 * Single responsibility: convert workflow <-> flow state.
 */

import type { Workflow, WorkflowNode, WorkflowEdge } from './types'
import type { Node, Edge } from '@xyflow/react'
import { MarkerType } from '@xyflow/react'

export interface WorkflowNodeData extends Record<string, unknown> {
  workflowNode: WorkflowNode
  label?: string
}

export interface WorkflowEdgeData extends Record<string, unknown> {
  label?: 'true' | 'false'
}

export function workflowToFlow(workflow: Workflow): {
  nodes: Node<WorkflowNodeData>[]
  edges: Edge<WorkflowEdgeData>[]
} {
  const nodes: Node<WorkflowNodeData>[] = workflow.nodes.map((n) => ({
    id: n.id,
    type: n.type,
    position: n.position,
    data: { workflowNode: n, label: n.type },
  }))
  const edges: Edge<WorkflowEdgeData>[] = workflow.edges.map((e) => ({
    id: e.id,
    source: e.from,
    target: e.to,
    markerEnd: { type: MarkerType.ArrowClosed },
    ...(e.label != null && {
      sourceHandle: e.label,
      data: { label: e.label },
      label: e.label,
    }),
  }))
  return { nodes, edges }
}

export function flowToWorkflow(
  workflowId: string,
  workflowName: string,
  nodes: Node<WorkflowNodeData>[],
  edges: Edge<WorkflowEdgeData>[]
): Workflow {
  const workflowNodes: WorkflowNode[] = nodes.map((n) => {
    const w = (n.data as WorkflowNodeData).workflowNode
    return {
      ...w,
      id: n.id,
      type: w.type,
      position: n.position,
      configuration: w.configuration,
      outgoingConnections: edges.filter((e) => e.source === n.id).map((e) => e.target),
    }
  })
  const workflowEdges: WorkflowEdge[] = edges.map((e) => {
    const label = e.data?.label ?? (['true', 'false'].includes(String(e.sourceHandle)) ? (e.sourceHandle as 'true' | 'false') : undefined)
    return { id: e.id, from: e.source, to: e.target, ...(label != null && { label }) }
  })
  return {
    id: workflowId,
    name: workflowName,
    nodes: workflowNodes,
    edges: workflowEdges,
  }
}
