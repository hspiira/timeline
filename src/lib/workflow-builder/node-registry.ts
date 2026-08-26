/**
 * Node Registry – extensible node types via registry pattern.
 * All node types are registered here; UI and execution consume the registry.
 */

import type { NodeType } from './types'
import { NODE_TYPES } from './types'

export interface NodeTypeDescriptor {
  type: NodeType
  label: string
  /** Optional short category for display (e.g. "Data", "Conditions", "Tasks"). Shown as tag on node. */
  category?: string
  /** Optional tip shown in the config panel when this node type is selected (Attio-style). */
  tip?: string
  /** Default configuration when creating a new node of this type */
  defaultConfiguration: Record<string, unknown>
  /** Condition nodes require exactly 2 outgoing edges with labels "true" and "false" */
  isCondition: boolean
  /** Terminal nodes have no outgoing edges */
  isTerminal: boolean
  /** Only one trigger per workflow */
  isTrigger: boolean
}

const registry = new Map<NodeType, NodeTypeDescriptor>()

function register(descriptor: NodeTypeDescriptor): void {
  registry.set(descriptor.type, descriptor)
}

function get(type: NodeType): NodeTypeDescriptor | undefined {
  return registry.get(type)
}

function getOrThrow(type: NodeType): NodeTypeDescriptor {
  const descriptor = registry.get(type)
  if (!descriptor) {
    throw new Error(`Unregistered workflow node type: ${type}`)
  }
  return descriptor
}

function getAll(): NodeTypeDescriptor[] {
  return Array.from(registry.values())
}

function has(type: NodeType): boolean {
  return registry.has(type)
}

/** Register built-in node types. Extensible: call register() for custom types. */
function registerBuiltins(): void {
  register({
    type: 'trigger',
    label: 'Trigger',
    category: 'Launch',
    tip: 'Pick the event type that starts this workflow. The workflow runs when an event of this type is created.',
    defaultConfiguration: { eventType: '' },
    isCondition: false,
    isTerminal: false,
    isTrigger: true,
  })
  register({
    type: 'action',
    label: 'Action',
    category: 'Capture action',
    defaultConfiguration: { actionType: 'create_event', params: {} },
    isCondition: false,
    isTerminal: false,
    isTrigger: false,
  })
  register({
    type: 'integration_action',
    label: 'Integration Action',
    category: 'Integrations',
    defaultConfiguration: { integration: '', operation: '', params: {} },
    isCondition: false,
    isTerminal: false,
    isTrigger: false,
  })
  register({
    type: 'condition',
    label: 'Condition',
    category: 'Conditions',
    tip: 'When the expression is true, the workflow follows the Yes path; otherwise it follows the No path. Connect both outcomes.',
    defaultConfiguration: { expression: '' },
    isCondition: true,
    isTerminal: false,
    isTrigger: false,
  })
  register({
    type: 'terminal',
    label: 'Terminal',
    category: 'End',
    defaultConfiguration: {},
    isCondition: false,
    isTerminal: true,
    isTrigger: false,
  })
}

registerBuiltins()

export const nodeRegistry = {
  register,
  get: getOrThrow,
  getOptional: get,
  getAll,
  has,
  /** All built-in types; custom types can be added via register() */
  nodeTypes: NODE_TYPES,
}
