import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { Square } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'

export function TerminalNode({ data }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const connection = useConnection()
  const showTargetHandles = connection?.inProgress === true
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border bg-background min-w-0 max-w-[140px] shrink-0 px-2 py-1.5 relative" data-node-id={data.workflowNode.id}>
      {showTargetHandles && (
        <>
          <Handle type="target" position={Position.Top} className="!w-3 !h-3 !bg-primary" />
          <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-primary" />
        </>
      )}
      <Square className="w-5 h-5 shrink-0 text-primary" />
      <span className="text-xs font-medium text-foreground">End</span>
    </div>
  )
}
