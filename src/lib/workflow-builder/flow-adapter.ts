/**
 * Adapter between our Workflow model and React Flow nodes/edges.
 * Single responsibility: convert workflow <-> flow state.
 */

import type { Edge, Node } from '@xyflow/react'
import { MarkerType } from '@xyflow/react'
import type { Workflow, WorkflowEdge, WorkflowNode } from './types'

/** Approximate node size so we can pick the target side that faces the source */
const NODE_WIDTH = 220
const NODE_HEIGHT = 80

export interface WorkflowNodeData extends Record<string, unknown> {
  workflowNode: WorkflowNode
  label?: string
}

export interface WorkflowEdgeData extends Record<string, unknown> {
  label?: 'true' | 'false'
}

/** Pick handle side (top/right/bottom/left) so the edge attaches on the side of the node that faces the other. */
function sideFacing(
  fromPos: { x: number; y: number },
  towardPos: { x: number; y: number },
): 'top' | 'right' | 'bottom' | 'left' {
  const fx = fromPos.x + NODE_WIDTH / 2
  const fy = fromPos.y + NODE_HEIGHT / 2
  const tx = towardPos.x + NODE_WIDTH / 2
  const ty = towardPos.y + NODE_HEIGHT / 2
  const dx = tx - fx
  const dy = ty - fy
  if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? 'right' : 'left'
  return dy > 0 ? 'bottom' : 'top'
}

/** Side of target node that faces the source (for target handle). */
function targetSideFacingSource(
  targetPos: { x: number; y: number },
  sourcePos: { x: number; y: number },
): 'top' | 'right' | 'bottom' | 'left' {
  return sideFacing(targetPos, sourcePos)
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
    dragHandle: '.workflow-node-drag-handle',
  }))
  const nodePos = (id: string) => workflow.nodes.find((n) => n.id === id)?.position
  const edges: Edge<WorkflowEdgeData>[] = workflow.edges.map((e) => {
    const isConditionEdge = e.label === 'true' || e.label === 'false'
    const sourcePos = nodePos(e.from)
    const targetPos = nodePos(e.to)
    const sourceSide = sourcePos && targetPos ? sideFacing(sourcePos, targetPos) : 'bottom'
    const targetSide = sourcePos && targetPos ? targetSideFacingSource(targetPos, sourcePos) : 'top'
    const conditionHandle = isConditionEdge ? `${sourceSide}-${e.label}` : undefined
    const sourceHandle = e.sourceHandle ?? conditionHandle ?? sourceSide
    const targetHandle = e.targetHandle ?? targetSide
    return {
      id: e.id,
      source: e.from,
      target: e.to,
      sourceHandle,
      targetHandle,
      type: 'floating',
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        color: 'hsl(var(--foreground) / 0.6)',
      },
      style: { strokeWidth: 2, stroke: 'hsl(var(--foreground) / 0.6)' },
      ...(isConditionEdge && {
        data: { label: e.label },
        label: e.label === 'true' ? 'is true' : 'is false',
        labelStyle: { fontSize: 10, fontWeight: 500 },
        labelBgStyle: { fill: 'var(--color-card)', fillOpacity: 0.95 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 12,
      }),
    }
  })
  return { nodes, edges }
}

export function flowToWorkflow(
  workflowId: string,
  workflowName: string,
  nodes: Node<WorkflowNodeData>[],
  edges: Edge<WorkflowEdgeData>[],
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
    const labelFromHandle =
      sh === 'true' || sh.endsWith('-true')
        ? 'true'
        : sh === 'false' || sh.endsWith('-false')
          ? 'false'
          : undefined
    const label = e.data?.label ?? labelFromHandle
    return {
      id: e.id,
      from: e.source,
      to: e.target,
      ...(label != null && { label }),
      ...(e.sourceHandle != null && { sourceHandle: e.sourceHandle }),
      ...(e.targetHandle != null && { targetHandle: e.targetHandle }),
    }
  })
  return {
    id: workflowId,
    name: workflowName,
    nodes: workflowNodes,
    edges: workflowEdges,
  }
}
