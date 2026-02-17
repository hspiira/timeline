import { Handle, Position, type NodeProps } from '@xyflow/react'
import { MousePointerClick } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

const ACTION_LABELS: Record<string, string> = {
  create_event: 'Create Event',
  send_email: 'Send Email',
  update_subject: 'Update Subject',
}

export function ActionNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const actionType = (data.workflowNode.configuration?.actionType as string) ?? 'create_event'
  const title = ACTION_LABELS[actionType] ?? actionType

  return (
    <WorkflowNodeShell
      badgeLabel="Capture action"
      badgeIcon={<MousePointerClick className="w-3 h-3" />}
      badgeVariant="amber"
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
