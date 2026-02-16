import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Plug } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'

export function IntegrationActionNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const desc = nodeRegistry.getOptional(w.type)
  const integration = (w.configuration?.integration as string) ?? ''
  const operation = (w.configuration?.operation as string) ?? ''
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-3 shadow-sm min-w-[180px]">
      <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground mb-1">
        <Plug className="w-3.5 h-3.5" />
        {desc?.label ?? 'Integration'}
      </div>
      <p className="text-sm font-medium text-foreground">
        {integration || 'Integration'} {operation && `· ${operation}`}
      </p>
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-primary" />
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-primary" />
    </div>
  )
}
