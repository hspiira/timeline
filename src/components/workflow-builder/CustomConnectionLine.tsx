/**
 * Custom connection line shown while dragging to create a new edge.
 * Uses smooth-step path for consistency with FloatingEdge.
 */

import { type ConnectionLineComponentProps, getSmoothStepPath } from '@xyflow/react'
import type { WorkflowNodeData } from '@/lib/workflow-builder/flow-adapter'

export function CustomConnectionLine({
  fromX,
  fromY,
  fromPosition,
  toX,
  toY,
  toPosition,
  connectionLineStyle,
}: ConnectionLineComponentProps<import('@xyflow/react').Node<WorkflowNodeData>>) {
  const [path] = getSmoothStepPath({
    sourceX: fromX,
    sourceY: fromY,
    sourcePosition: fromPosition,
    targetX: toX,
    targetY: toY,
    targetPosition: toPosition,
    borderRadius: 8,
    offset: 12,
  })

  return (
    <g>
      <path
        fill="none"
        stroke={connectionLineStyle?.stroke ?? 'var(--color-border)'}
        strokeWidth={connectionLineStyle?.strokeWidth ?? 1.5}
        className="react-flow__connection-path"
        d={path}
      />
    </g>
  )
}
