import { Handle, Position, type NodeProps } from '@xyflow/react'
import { GitBranch } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'

export function ConditionNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const desc = nodeRegistry.getOptional(w.type)
  const expression = (w.configuration?.expression as string) ?? ''
  return (
    <div className="rounded-xl border border-border bg-background px-4 py-3 shadow-sm min-w-[160px]">
      <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground mb-1">
        <GitBranch className="w-3.5 h-3.5" />
        {desc?.label ?? 'Condition'}
      </div>
      <p className="text-sm font-mono text-foreground truncate max-w-[140px]" title={expression}>
        {expression || 'expression'}
      </p>
      <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-primary" />
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        className="!left-[30%] !w-3 !h-3 !bg-green-600"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="false"
        className="!left-[70%] !w-3 !h-3 !bg-red-600"
      />
    </div>
  )
}
