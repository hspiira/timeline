import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { Play } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

export function IntegrationActionNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const w = data.workflowNode
  const integration = (w.configuration?.integration as string) ?? ''
  const operation = (w.configuration?.operation as string) ?? ''
  const title = integration || 'Integration'
  const description = operation || undefined
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true
  const showHandles = isConnecting || selected

  return (
    <WorkflowNodeShell
      badgeLabel="3rd Party Action"
      badgeIcon={<Play className="w-3 h-3" />}
      badgeVariant="violet"
      title={title}
      description={description}
      selected={selected}
    >
      <Handle
        type="source"
        position={Position.Top}
        id="top"
        className={`!absolute !top-0 !left-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !-translate-x-1/2 !-translate-y-1/2 ${showHandles ? HANDLE_CLASS : '!bg-muted-foreground/30 hover:!bg-muted-foreground/50'}`}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className={`!absolute !right-0 !top-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !translate-x-1/2 !-translate-y-1/2 ${showHandles ? HANDLE_CLASS : '!bg-muted-foreground/30 hover:!bg-muted-foreground/50'}`}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className={`!absolute !bottom-0 !left-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !-translate-x-1/2 !translate-y-1/2 ${showHandles ? HANDLE_CLASS : '!bg-muted-foreground/30 hover:!bg-muted-foreground/50'}`}
      />
      <Handle
        type="source"
        position={Position.Left}
        id="left"
        className={`!absolute !left-0 !top-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !-translate-x-1/2 !-translate-y-1/2 ${showHandles ? HANDLE_CLASS : '!bg-muted-foreground/30 hover:!bg-muted-foreground/50'}`}
      />
    </WorkflowNodeShell>
  )
}
