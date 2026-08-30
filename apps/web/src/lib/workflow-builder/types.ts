/**
 * Workflow Model Layer – types and data structures.
 * Clean separation: no UI or execution concerns.
 */

export const NODE_TYPES = [
  'trigger',
  'action',
  'integration_action',
  'condition',
  'terminal',
] as const

export type NodeType = (typeof NODE_TYPES)[number]

export interface Position {
  x: number
  y: number
}

/** Configuration is extensible per node type */
export type NodeConfiguration = Record<string, unknown>

export interface WorkflowNode {
  id: string
  type: NodeType
  position: Position
  configuration: NodeConfiguration
  /** Outgoing connection targets (node ids). For condition: ordered as [trueBranchId, falseBranchId] or use edge labels. */
  outgoingConnections?: string[]
}

export interface WorkflowEdge {
  id: string
  from: string
  to: string
  /** For condition nodes: "true" | "false". Omitted for other edges. */
  label?: 'true' | 'false'
  /** Persisted from flow so edges keep correct attachment on reopen. */
  sourceHandle?: string
  targetHandle?: string
}

export interface Workflow {
  id: string
  name: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  /** Optional trigger conditions (backend-specific). Passed through by adapters. */
  triggerConditions?: Record<string, unknown> | null
}

export function createEmptyWorkflow(id: string, name: string): Workflow {
  return { id, name, nodes: [], edges: [] }
}

/** Default trigger node id for new workflows (Attio-style: start by specifying the trigger). */
export const DEFAULT_TRIGGER_NODE_ID = 'trigger-default'

/** Creates a new workflow with a single trigger node so the user starts by specifying the trigger. */
export function createWorkflowWithDefaultTrigger(id: string, name: string): Workflow {
  const triggerNode = createNode(
    DEFAULT_TRIGGER_NODE_ID,
    'trigger',
    { x: 0, y: 0 },
    { eventType: '' },
  )
  return { id, name, nodes: [triggerNode], edges: [] }
}

export function createNode(
  id: string,
  type: NodeType,
  position: Position,
  configuration: NodeConfiguration = {},
): WorkflowNode {
  return {
    id,
    type,
    position,
    configuration,
    outgoingConnections: [],
  }
}

export function createEdge(
  id: string,
  from: string,
  to: string,
  label?: 'true' | 'false',
): WorkflowEdge {
  return { id, from, to, ...(label != null && { label }) }
}
