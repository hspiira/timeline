/**
 * Orthogonal (smooth step) edge for clear, predictable connectors that attach
 * on the correct side of each node and avoid overlapping the card.
 */

import { getSmoothStepPath, BaseEdge, type EdgeProps } from '@xyflow/react'
import type { WorkflowEdgeData } from '@/lib/workflow-builder/flow-adapter'

export function FloatingEdge(props: EdgeProps<import('@xyflow/react').Edge<WorkflowEdgeData>>) {
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
    borderRadius: 8,
    offset: 12,
  })

  return (
    <BaseEdge
      path={path}
      labelX={labelX}
      labelY={labelY}
      label={props.label}
      labelStyle={props.labelStyle}
      labelShowBg={props.labelShowBg}
      labelBgStyle={props.labelBgStyle}
      labelBgPadding={props.labelBgPadding}
      labelBgBorderRadius={props.labelBgBorderRadius}
      markerEnd={props.markerEnd}
      markerStart={props.markerStart}
      style={props.style}
    />
  )
}
