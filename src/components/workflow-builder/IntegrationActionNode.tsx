import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { Play } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

const HIDE_WHEN_NOT_CONNECTING = '!opacity-0 pointer-events-none'

export function IntegrationActionNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const integration = (w.configuration?.integration as string) ?? ''
  const operation = (w.configuration?.operation as string) ?? ''
  const title = integration || 'Integration'
  const description = operation || undefined
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true
  const showHandles = isConnecting || selected
  const sourceClass = `${HANDLE_CLASS} ${!showHandles ? HIDE_WHEN_NOT_CONNECTING : ''}`

  return (
    <WorkflowNodeShell
      badgeLabel="3rd Party Action"
      badgeIcon={<Play className="w-3 h-3" />}
      badgeVariant="violet"
      title={title}
      description={description}
      selected={selected}
    >
      <Handle type="source" position={Position.Top} id="top" className={sourceClass} />
      <Handle type="source" position={Position.Right} id="right" className={sourceClass} />
      <Handle type="source" position={Position.Bottom} id="bottom" className={sourceClass} />
      <Handle type="source" position={Position.Left} id="left" className={sourceClass} />
    </WorkflowNodeShell>
  )
}
