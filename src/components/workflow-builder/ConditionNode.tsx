import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { GitBranch } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'

export function ConditionNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const connection = useConnection()
  const showTargetHandles = connection?.inProgress === true
  const expression = (data.workflowNode.configuration?.expression as string) ?? ''
  const label = expression ? (expression.length > 12 ? `${expression.slice(0, 12)}…` : expression) : 'Condition'
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border bg-background min-w-0 max-w-[180px] shrink-0 px-2 py-1.5 relative">
      {showTargetHandles && (
        <>
          <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-primary" />
          <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-primary" />
        </>
      )}
      <GitBranch className="w-5 h-5 shrink-0 text-primary" />
      <span className="text-xs font-medium text-foreground truncate" title={expression || 'Condition'}>{label}</span>
      <Handle type="source" position={Position.Bottom} id="true" className="!left-[30%] !w-3 !h-3 !bg-green-600" />
      <Handle type="source" position={Position.Bottom} id="false" className="!left-[70%] !w-3 !h-3 !bg-red-600" />
      <Handle type="source" position={Position.Right} id="right" className="!w-3 !h-3 !bg-primary" />
    </div>
  )
}
