import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Zap } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'

export function ActionNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const desc = nodeRegistry.getOptional(w.type)
  const actionType = (w.configuration?.actionType as string) ?? 'create_event'
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-3 shadow-sm min-w-[180px]">
      <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground mb-1">
        <Zap className="w-3.5 h-3.5" />
        {desc?.label ?? 'Action'}
      </div>
      <p className="text-sm font-medium text-foreground">{actionType}</p>
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-primary" />
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-primary" />
    </div>
  )
}
