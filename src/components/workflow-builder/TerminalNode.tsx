import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Square } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'

export function TerminalNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const desc = nodeRegistry.getOptional(w.type)
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-3 shadow-sm min-w-[120px]">
      <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground">
        <Square className="w-3.5 h-3.5" />
        {desc?.label ?? 'End'}
      </div>
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-primary" />
    </div>
  )
}
