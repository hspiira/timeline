import type { NodeProps } from '@xyflow/react'
import { CircleX } from 'lucide-react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'
import { WorkflowNodeShell } from './WorkflowNodeShell'

export function TerminalNode({ selected }: NodeProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  return (
    <WorkflowNodeShell
      badgeLabel="End"
      badgeIcon={<CircleX className="w-3 h-3" />}
      badgeVariant="rose"
      title="End"
      selected={selected}
    >
      {/* Terminal — no source handles */}
    </WorkflowNodeShell>
  )
}
