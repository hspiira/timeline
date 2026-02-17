import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { Zap } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

const HIDE_WHEN_NOT_CONNECTING = '!opacity-0 pointer-events-none'

export function TriggerNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const eventType = (data.workflowNode.configuration?.eventType as string) || ''
  const title = eventType || 'New trigger'
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true
  const showHandles = isConnecting || selected
  const sourceClass = `${HANDLE_CLASS} ${!showHandles ? HIDE_WHEN_NOT_CONNECTING : ''}`

  return (
    <WorkflowNodeShell
      badgeLabel="Launch action"
      badgeIcon={<Zap className="w-3 h-3" />}
      badgeVariant="emerald"
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
