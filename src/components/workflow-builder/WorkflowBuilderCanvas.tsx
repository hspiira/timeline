import { useCallback, useEffect, useRef } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Node,
  type Edge,
  Panel,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  workflowToFlow,
  flowToWorkflow,
  type WorkflowNodeData,
  type WorkflowEdgeData,
} from '@/lib/workflow-builder/flow-adapter'
import type { Workflow } from '@/lib/workflow-builder/types'
import { createNode } from '@/lib/workflow-builder/types'
import { validateConnection, generateEdgeId } from '@/lib/workflow-builder/edge-manager'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import { TriggerNode } from './TriggerNode'
import { ActionNode } from './ActionNode'
import { IntegrationActionNode } from './IntegrationActionNode'
import { ConditionNode } from './ConditionNode'
import { TerminalNode } from './TerminalNode'
import type { NodeType } from '@/lib/workflow-builder/types'

const nodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  integration_action: IntegrationActionNode,
  condition: ConditionNode,
  terminal: TerminalNode,
}

export interface WorkflowBuilderCanvasProps {
  workflow: Workflow
  workflowId: string
  workflowName: string
  onWorkflowChange: (workflow: Workflow) => void
  allowCircular?: boolean
}

export function WorkflowBuilderCanvas({
  workflow,
  workflowId,
  workflowName,
  onWorkflowChange,
  allowCircular = false,
}: WorkflowBuilderCanvasProps) {
  const { nodes: initialNodes, edges: initialEdges } = workflowToFlow(workflow)
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const reactFlowRef = useRef<HTMLDivElement>(null)

  const onConnect = useCallback(
    (connection: Connection) => {
      const fromNode = nodes.find((n) => n.id === connection.source)
      const desc = fromNode ? nodeRegistry.getOptional(fromNode.type as NodeType) : undefined
      const label = desc?.isCondition
        ? (connection.sourceHandle as 'true' | 'false') ?? undefined
        : undefined
      const nextWorkflow = flowToWorkflow(workflowId, workflowName, nodes, edges)
      const validation = validateConnection(
        nextWorkflow,
        connection.source!,
        connection.target!,
        label,
        allowCircular
      )
      if (!validation.valid) {
        return
      }
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            id: generateEdgeId(),
            ...(label != null && { sourceHandle: label, data: { label }, label }),
          },
          eds
        )
      )
    },
    [nodes, edges, workflowId, workflowName, allowCircular, setEdges]
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const type = e.dataTransfer.getData('application/reactflow-node-type') as NodeType | ''
      if (!type || !nodeRegistry.has(type)) return
      const bounds = reactFlowRef.current?.getBoundingClientRect()
      if (!bounds) return
      const position = {
        x: e.clientX - bounds.left - 80,
        y: e.clientY - bounds.top - 20,
      }
      const desc = nodeRegistry.get(type)
      const id = `node-${crypto.randomUUID()}`
      const workflowNode = createNode(id, type, position, { ...desc.defaultConfiguration })
      const newNode: Node<WorkflowNodeData> = {
        id,
        type,
        position,
        data: { workflowNode, label: type },
      }
      setNodes((nds) => nds.concat(newNode))
    },
    [setNodes]
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  useEffect(() => {
    const w = flowToWorkflow(workflowId, workflowName, nodes, edges)
    onWorkflowChange(w)
  }, [workflowId, workflowName, nodes, edges, onWorkflowChange])

  return (
    <div ref={reactFlowRef} className="h-[500px] w-full rounded-xl border border-border bg-muted/30">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        fitView
        className="bg-muted/20"
      >
        <Background />
        <Controls />
        <Panel position="top-left" className="m-2 text-xs text-muted-foreground">
          Drag nodes from the palette and drop here. Connect from source handle to target handle.
        </Panel>
      </ReactFlow>
    </div>
  )
}
