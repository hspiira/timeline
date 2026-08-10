import { Handle, Position, useConnection, type NodeProps } from '@xyflow/react'
import { MousePointerClick } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { getActionTypeLabel } from '@/lib/workflow-builder/action-types'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import { WorkflowNodeShell, HANDLE_CLASS } from './WorkflowNodeShell'

export function ActionNode({ data, selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const node = data.workflowNode
  const actionType = (node.configuration?.actionType as string) ?? 'create_event'
  const title = getActionTypeLabel(actionType)
  const description = (node.configuration?.description as string) || undefined
  const desc = nodeRegistry.getOptional(node.type)
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true
  const showHandles = isConnecting || selected

  return (
    <WorkflowNodeShell
      badgeLabel="Capture action"
      badgeIcon={<MousePointerClick className="w-3 h-3" />}
      badgeVariant="amber"
      title={title}
      description={description}
      tag={desc?.category}
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
