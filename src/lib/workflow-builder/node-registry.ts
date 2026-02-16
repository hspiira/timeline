/**
 * Node Registry – extensible node types via registry pattern.
 * All node types are registered here; UI and execution consume the registry.
 */

import type { NodeType } from './types'
import { NODE_TYPES } from './types'

export interface NodeTypeDescriptor {
  type: NodeType
  label: string
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
    defaultConfiguration: { eventType: '' },
    isCondition: false,
    isTerminal: false,
    isTrigger: true,
  })
  register({
    type: 'action',
    label: 'Action',
    defaultConfiguration: { actionType: 'create_event', params: {} },
    isCondition: false,
    isTerminal: false,
    isTrigger: false,
  })
  register({
    type: 'integration_action',
    label: 'Integration Action',
    defaultConfiguration: { integration: '', operation: '', params: {} },
    isCondition: false,
    isTerminal: false,
    isTrigger: false,
  })
  register({
    type: 'condition',
    label: 'Condition',
    defaultConfiguration: { expression: '' },
    isCondition: true,
    isTerminal: false,
    isTrigger: false,
  })
  register({
    type: 'terminal',
    label: 'Terminal',
    defaultConfiguration: {},
    isCondition: false,
    isTerminal: true,
    isTrigger: false,
  })
}

registerBuiltins()

export const nodeRegistry = {
  register,
  get: (type: NodeType) => get(type)!,
  getOptional: get,
  getAll,
  has,
  /** All built-in types; custom types can be added via register() */
  nodeTypes: NODE_TYPES,
}
