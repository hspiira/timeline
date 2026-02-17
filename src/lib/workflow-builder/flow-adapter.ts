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
  const edges: Edge<WorkflowEdgeData>[] = workflow.edges.map((e) => {
    const isConditionEdge = e.label === 'true' || e.label === 'false'
    const conditionHandle = isConditionEdge ? `bottom-${e.label}` : undefined
    return {
      id: e.id,
      source: e.from,
      target: e.to,
      sourceHandle: conditionHandle ?? 'bottom',
      targetHandle: 'top',
      type: 'smoothstep',
      markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
      style: { strokeWidth: 1.5 },
      ...(isConditionEdge && {
        data: { label: e.label },
        label: e.label === 'true' ? 'is true' : 'is false',
        labelStyle: { fontSize: 10, fontWeight: 500 },
        labelBgStyle: { fill: 'var(--color-card)', fillOpacity: 0.95 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      }),
    }
  })
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
    const sh = String(e.sourceHandle ?? '')
    const labelFromHandle = sh === 'true' || sh.endsWith('-true') ? 'true' : sh === 'false' || sh.endsWith('-false') ? 'false' : undefined
    const label = e.data?.label ?? labelFromHandle
    return { id: e.id, from: e.source, to: e.target, ...(label != null && { label }) }
  })
  return {
    id: workflowId,
    name: workflowName,
    nodes: workflowNodes,
    edges: workflowEdges,
  }
}
