import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  useUpdateNodeInternals,
  addEdge,
  MarkerType,
  type Connection,
  type Node,
  type ReactFlowInstance,
  Panel,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  workflowToFlow,
  flowToWorkflow,
  type WorkflowNodeData,
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
import { FloatingEdge } from './FloatingEdge'
import { CustomConnectionLine } from './CustomConnectionLine'
import type { NodeType } from '@/lib/workflow-builder/types'
import { ArrowRight, ArrowDown } from 'lucide-react'

const nodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  integration_action: IntegrationActionNode,
  condition: ConditionNode,
  terminal: TerminalNode,
}

const edgeTypes = {
  floating: FloatingEdge,
}

const defaultEdgeOptions = {
  type: 'floating',
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 16,
    height: 16,
    color: 'hsl(var(--foreground) / 0.6)',
  },
  style: { strokeWidth: 2, stroke: 'hsl(var(--foreground) / 0.6)' },
}

const connectionLineStyle = { stroke: 'hsl(var(--border))', strokeWidth: 1.5 }

export interface WorkflowBuilderCanvasProps {
  workflow: Workflow
  workflowId: string
  workflowName: string
  onWorkflowChange: (workflow: Workflow) => void
  allowCircular?: boolean
  /** Optional panel at top of canvas (e.g. horizontal node palette) */
  topPanel?: React.ReactNode
  className?: string
  height?: string
  /** Called when selection changes; receives selected node id or null */
  onSelectionChange?: (selectedNodeId: string | null) => void
}

function WorkflowBuilderCanvasInner({
  workflow,
  workflowId,
  workflowName,
  onWorkflowChange,
  allowCircular = false,
  topPanel,
  className,
  height = '600px',
  onSelectionChange,
}: WorkflowBuilderCanvasProps) {
  const { nodes: initialNodes, edges: initialEdges } = workflowToFlow(workflow)
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const updateNodeInternals = useUpdateNodeInternals()
  const reactFlowRef = useRef<HTMLDivElement>(null)
  const flowInstanceRef = useRef<ReactFlowInstance<Node<WorkflowNodeData>> | null>(null)
  const lastPushedWorkflowRef = useRef<Workflow | null>(null)
  const [layoutDirection, setLayoutDirection] = useState<'horizontal' | 'vertical'>('vertical')

  useEffect(() => {
    if (workflow === lastPushedWorkflowRef.current) return
    const { nodes: wNodes, edges: wEdges } = workflowToFlow(workflow)
    setNodes(wNodes)
    setEdges(wEdges)
    const ids = wNodes.map((n) => n.id)
    // Run after layout so node dimensions (e.g. title change) are correct and edges don’t distort
    let cancelled = false
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!cancelled) ids.forEach((id) => updateNodeInternals(id))
      })
    })
    // After reopen, layout may not be final until the modal has opened; run again so edges stay correct
    const t = setTimeout(() => {
      if (!cancelled) ids.forEach((id) => updateNodeInternals(id))
    }, 400)
    return () => {
      cancelled = true
      cancelAnimationFrame(raf)
      clearTimeout(t)
    }
  }, [workflow, setNodes, setEdges, updateNodeInternals])

  const onConnect = useCallback(
    (connection: Connection) => {
      const fromNode = nodes.find((n) => n.id === connection.source)
      const desc = fromNode ? nodeRegistry.getOptional(fromNode.type as NodeType) : undefined
      const sh = String(connection.sourceHandle ?? '')
      const label: 'true' | 'false' | undefined = desc?.isCondition
        ? sh === 'true' || sh.endsWith('-true')
          ? 'true'
          : sh === 'false' || sh.endsWith('-false')
            ? 'false'
            : undefined
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
      const displayLabel =
        label === 'true' ? 'is true' : label === 'false' ? 'is false' : label
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            id: generateEdgeId(),
            ...(label != null && {
              data: { label },
              label: displayLabel,
            }),
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
      const instance = flowInstanceRef.current
      const position = instance
        ? instance.screenToFlowPosition({ x: e.clientX, y: e.clientY })
        : { x: e.clientX - 80, y: e.clientY - 20 }
      const desc = nodeRegistry.get(type)
      const id = `node-${crypto.randomUUID()}`
      const workflowNode = createNode(id, type, position, { ...desc.defaultConfiguration })
      const newNode: Node<WorkflowNodeData> = {
        id,
        type,
        position,
        data: { workflowNode, label: type },
        dragHandle: '.workflow-node-drag-handle',
      }
      setNodes((nds) => nds.concat(newNode))
      onSelectionChange?.(id)
    },
    [setNodes, onSelectionChange]
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  useEffect(() => {
    const w = flowToWorkflow(workflowId, workflowName, nodes, edges)
    lastPushedWorkflowRef.current = w
    onWorkflowChange(w)
  }, [workflowId, workflowName, nodes, edges, onWorkflowChange])

  const handleInit = useCallback((instance: ReactFlowInstance<Node<WorkflowNodeData>>) => {
    flowInstanceRef.current = instance
    // Fit entire workflow in view with padding for a minimal zoomed work area
    instance.fitView({ padding: 0.25, duration: 200, minZoom: 0.15, maxZoom: 1.5 })
  }, [])

  // Re-fit view when workflow structure changes (e.g. template load) so model stays in view
  useEffect(() => {
    const instance = flowInstanceRef.current
    if (!instance) return
    const t = setTimeout(() => {
      flowInstanceRef.current?.fitView({ padding: 0.25, duration: 300, minZoom: 0.15, maxZoom: 1.5 })
    }, 100)
    return () => clearTimeout(t)
  }, [workflow.nodes.length, workflow.edges.length])

  const handleSelectionChange = useCallback(
    (params: { nodes: Node<WorkflowNodeData>[] }) => {
      const selected = params.nodes.find((n) => n.selected)
      onSelectionChange?.(selected?.id ?? null)
    },
    [onSelectionChange]
  )

  const applyLayout = useCallback(
    (direction: 'horizontal' | 'vertical') => {
      const triggerIds = nodes
        .filter((n) => nodeRegistry.getOptional(n.type as NodeType)?.isTrigger)
        .map((n) => n.id)
      const order: string[] = []
      const visited = new Set<string>()
      const queue = [...triggerIds]
      while (queue.length > 0) {
        const id = queue.shift()!
        if (visited.has(id)) continue
        visited.add(id)
        order.push(id)
        for (const e of edges) {
          if (e.source === id && !visited.has(e.target)) queue.push(e.target)
        }
      }
      nodes.forEach((n) => {
        if (!visited.has(n.id)) order.push(n.id)
      })
      const spacing = direction === 'horizontal' ? 320 : 160
      setNodes((nds) =>
        nds.map((node) => {
          const i = order.indexOf(node.id)
          const pos =
            i >= 0
              ? direction === 'horizontal'
                ? { x: i * spacing, y: 0 }
                : { x: 0, y: i * spacing }
              : node.position
          return { ...node, position: pos }
        })
      )
      setLayoutDirection(direction)
      setTimeout(() => flowInstanceRef.current?.fitView({ padding: 0.25, duration: 300 }), 50)
    },
    [nodes, edges, setNodes]
  )

  return (
    <div
      ref={reactFlowRef}
      className={`workflow-canvas w-full shrink-0 rounded-xl border border-border bg-muted/20 overflow-hidden ${className ?? ''}`}
      style={{ height, minHeight: height, maxHeight: height }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onInit={handleInit}
        onSelectionChange={handleSelectionChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineComponent={CustomConnectionLine}
        connectionLineStyle={connectionLineStyle}
        noDragClassName="workflow-node-drag-handle"
        fitView={false}
        minZoom={0.15}
        maxZoom={1.5}
        className="bg-muted/10"
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <Controls showInteractive={false} />
        <Panel position="top-center" className="w-full max-w-full pt-0 px-2 pb-2">
          <div className="flex items-center justify-between gap-4 w-full">
            {topPanel != null ? (
              <div className="flex items-center">{topPanel}</div>
            ) : (
              <span className="text-[11px] text-muted-foreground/70">
                Drag nodes from the palette and drop here
              </span>
            )}
            <div className="flex rounded-lg border border-border bg-card/90 backdrop-blur-sm overflow-hidden shrink-0">
              <button
                type="button"
                onClick={() => applyLayout('horizontal')}
                title="Horizontal layout"
                className={`p-1.5 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors ${layoutDirection === 'horizontal' ? 'bg-muted/50 text-foreground' : ''}`}
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => applyLayout('vertical')}
                title="Vertical layout"
                className={`p-1.5 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors border-l border-border ${layoutDirection === 'vertical' ? 'bg-muted/50 text-foreground' : ''}`}
              >
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  )
}

export function WorkflowBuilderCanvas(props: WorkflowBuilderCanvasProps) {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderCanvasInner {...props} />
    </ReactFlowProvider>
  )
}
