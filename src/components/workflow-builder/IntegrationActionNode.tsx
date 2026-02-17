import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Play } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

export function IntegrationActionNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const integration = (w.configuration?.integration as string) ?? ''
  const operation = (w.configuration?.operation as string) ?? ''
  const title = integration || 'Integration'
  const description = operation || undefined

  return (
    <WorkflowNodeShell
      badgeLabel="3rd Party Action"
      badgeIcon={<Play className="w-3 h-3" />}
      badgeVariant="violet"
      title={title}
      description={description}
      selected={selected}
    >
      <Handle type="source" position={Position.Top} id="top" className={HANDLE_CLASS} />
      <Handle type="source" position={Position.Right} id="right" className={HANDLE_CLASS} />
      <Handle type="source" position={Position.Bottom} id="bottom" className={HANDLE_CLASS} />
      <Handle type="source" position={Position.Left} id="left" className={HANDLE_CLASS} />
    </WorkflowNodeShell>
  )
}
