import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Zap } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

export function TriggerNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const eventType = (data.workflowNode.configuration?.eventType as string) || ''
  const title = eventType || 'New trigger'

  return (
    <WorkflowNodeShell
      badgeLabel="Launch action"
      badgeIcon={<Zap className="w-3 h-3" />}
      badgeVariant="emerald"
      title={title}
      selected={selected}
    >
      <Handle type="source" position={Position.Top} id="top" className={HANDLE_CLASS} />
      <Handle type="source" position={Position.Right} id="right" className={HANDLE_CLASS} />
      <Handle type="source" position={Position.Bottom} id="bottom" className={HANDLE_CLASS} />
      <Handle type="source" position={Position.Left} id="left" className={HANDLE_CLASS} />
    </WorkflowNodeShell>
  )
}
