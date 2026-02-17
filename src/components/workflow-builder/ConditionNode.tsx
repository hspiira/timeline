import { Handle, Position, type NodeProps } from '@xyflow/react'
import { CircleDot } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

export function ConditionNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const expression = (data.workflowNode.configuration?.expression as string) ?? ''
  const title = expression || 'Check condition'

  return (
    <WorkflowNodeShell
      badgeLabel="Check if / else"
      badgeIcon={<CircleDot className="w-3 h-3" />}
      badgeVariant="blue"
      title={title}
      selected={selected}
    >
      {/* True/false branches on bottom — placed close together */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        className={`!left-[48%] ${HANDLE_CLASS} !bg-emerald-500/70`}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="false"
        className={`!left-[52%] ${HANDLE_CLASS} !bg-rose-500/70`}
      />
    </WorkflowNodeShell>
  )
}
