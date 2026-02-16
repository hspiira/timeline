import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Zap } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'

export function TriggerNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const eventType = (w.configuration?.eventType as string) ?? 'When event…'
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-3 shadow-sm min-w-[160px]">
      <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground mb-1">
        <Zap className="w-3.5 h-3.5" />
        Trigger
      </div>
      <p className="text-sm font-medium text-foreground">{eventType || 'When event…'}</p>
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-primary" />
    </div>
  )
}
