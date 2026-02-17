import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { MousePointerClick } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { getActionTypeLabel } from '@/lib/workflow-builder/action-types'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

const HIDE_WHEN_NOT_CONNECTING = '!opacity-0 pointer-events-none'

export function ActionNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const actionType = (data.workflowNode.configuration?.actionType as string) ?? 'create_event'
  const title = getActionTypeLabel(actionType)
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true
  const showHandles = isConnecting || selected
  const sourceClass = `${HANDLE_CLASS} ${!showHandles ? HIDE_WHEN_NOT_CONNECTING : ''}`

  return (
    <WorkflowNodeShell
      badgeLabel="Capture action"
      badgeIcon={<MousePointerClick className="w-3 h-3" />}
      badgeVariant="amber"
      title={title}
      selected={selected}
    >
      <Handle type="source" position={Position.Top} id="top" className={sourceClass} />
      <Handle type="source" position={Position.Right} id="right" className={sourceClass} />
      <Handle type="source" position={Position.Bottom} id="bottom" className={sourceClass} />
      <Handle type="source" position={Position.Left} id="left" className={sourceClass} />
    </WorkflowNodeShell>
  )
}
