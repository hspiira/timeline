import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { Plug } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'

export function IntegrationActionNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const connection = useConnection()
  const showTargetHandles = connection?.inProgress === true
  const w = data.workflowNode
  const integration = (w.configuration?.integration as string) ?? ''
  const operation = (w.configuration?.operation as string) ?? ''
  const label = [integration, operation].filter(Boolean).join(' · ') || 'Integration'
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border bg-background min-w-0 max-w-[180px] shrink-0 px-2 py-1.5 relative">
      {showTargetHandles && (
        <>
          <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-primary" />
          <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-primary" />
        </>
      )}
      <Plug className="w-5 h-5 shrink-0 text-primary" />
      <span className="text-xs font-medium text-foreground truncate" title={label}>{label}</span>
      <Handle type="source" position={Position.Bottom} className="!w-3 !h-3 !bg-primary" />
      <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-primary" />
    </div>
  )
}
