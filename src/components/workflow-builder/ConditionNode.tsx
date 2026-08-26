import { Handle, type NodeProps, Position, useConnection } from '@xyflow/react'
import { CircleDot } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import { HANDLE_CLASS, WorkflowNodeShell } from './WorkflowNodeShell'

const HIDE_WHEN_NOT_CONNECTING = '!opacity-0 pointer-events-none'

export function ConditionNode({
  data,
  selected,
}: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const node = data.workflowNode
  const expression = (node.configuration?.expression as string) ?? ''
  const title = expression || 'Check condition'
  const description = (node.configuration?.description as string) || undefined
  const desc = nodeRegistry.getOptional(node.type)
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true
  const showHandles = isConnecting || selected
  const hide = !showHandles ? HIDE_WHEN_NOT_CONNECTING : ''

  const trueClass = `${HANDLE_CLASS} !bg-emerald-500/70 ${hide}`
  const falseClass = `${HANDLE_CLASS} !bg-rose-500/70 ${hide}`

  return (
    <WorkflowNodeShell
      badgeLabel="Check if / else"
      badgeIcon={<CircleDot className="w-3 h-3" />}
      badgeVariant="blue"
      title={title}
      description={description}
      tag={desc?.category}
      selected={selected}
    >
      {/* Yes/no on all 4 sides; target handles (for incoming) only show when connecting (in shell) */}
      {/* Top */}
      <Handle
        type="source"
        position={Position.Top}
        id="top-true"
        className={`!left-[48%] ${trueClass}`}
      />
      <Handle
        type="source"
        position={Position.Top}
        id="top-false"
        className={`!left-[52%] ${falseClass}`}
      />
      {/* Bottom */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom-true"
        className={`!left-[48%] ${trueClass}`}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom-false"
        className={`!left-[52%] ${falseClass}`}
      />
      {/* Left */}
      <Handle
        type="source"
        position={Position.Left}
        id="left-true"
        className={`!top-[48%] ${trueClass}`}
      />
      <Handle
        type="source"
        position={Position.Left}
        id="left-false"
        className={`!top-[52%] ${falseClass}`}
      />
      {/* Right */}
      <Handle
        type="source"
        position={Position.Right}
        id="right-true"
        className={`!top-[48%] ${trueClass}`}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right-false"
        className={`!top-[52%] ${falseClass}`}
      />
    </WorkflowNodeShell>
  )
}
