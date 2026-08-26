import { Handle, Position, useConnection } from '@xyflow/react'
import { GripVertical } from 'lucide-react'
import type { ReactNode } from 'react'

export type BadgeVariant = 'emerald' | 'amber' | 'blue' | 'violet' | 'rose'

const BADGE_COLORS: Record<BadgeVariant, string> = {
  emerald:
    'bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60',
  amber:
    'bg-amber-50 text-amber-700 border-amber-200/80 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60',
  blue: 'bg-blue-50 text-blue-700 border-blue-200/80 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/60',
  violet:
    'bg-violet-50 text-violet-700 border-violet-200/80 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-800/60',
  rose: 'bg-rose-50 text-rose-700 border-rose-200/80 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60',
}

export const HANDLE_CLASS =
  '!w-2.5 !h-2.5 !rounded-full !bg-muted-foreground/50 !border-2 !border-card hover:!bg-primary/40 !transition-all !duration-150'
export const HANDLE_TARGET_CLASS =
  '!w-2.5 !h-2.5 !rounded-full !bg-primary/40 !border-2 !border-card hover:!bg-primary/60 !transition-all !duration-150'

interface WorkflowNodeShellProps {
  badgeLabel: string
  badgeIcon: ReactNode
  badgeVariant: BadgeVariant
  title: string
  description?: string
  /** Optional status badge (e.g. "Completed", "Running") when execution state is available */
  status?: string
  /** Optional tag on the right (e.g. integration name, category) */
  tag?: string
  selected?: boolean
  children?: ReactNode
}

/**
 * Single card = node bounds so React Flow places handles on the card edges.
 * Badge and content live inside; no shadows. Handles sit on the border midline.
 */
export function WorkflowNodeShell({
  badgeLabel,
  badgeIcon,
  badgeVariant,
  title,
  description,
  status,
  tag,
  selected,
  children,
}: WorkflowNodeShellProps) {
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true
  const showTargetHandles = isConnecting || selected
  const targetHandleVisible = showTargetHandles
    ? HANDLE_TARGET_CLASS
    : '!bg-muted-foreground/30 !border-2 !border-card'

  return (
    <div
      className={`workflow-node-card relative w-[220px] rounded-xl border bg-card px-4 pt-2 pb-3 text-center nodrag ${
        selected ? 'border-ring/60 ring-2 ring-ring/30' : 'border-border'
      }`}
    >
      {/* Drag handle: only this area triggers node drag (React Flow dragHandle) */}
      <div
        className="workflow-node-drag-handle absolute left-1 top-1/2 -translate-y-1/2 cursor-grab active:cursor-grabbing rounded p-0.5 text-muted-foreground hover:bg-muted/50 hover:text-foreground z-10"
        title="Drag to move"
      >
        <GripVertical className="w-3.5 h-3.5" />
      </div>

      {/* Badge inside card so node bounds = card */}
      <span
        className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-[3px] text-[10px] font-semibold leading-none select-none ${BADGE_COLORS[badgeVariant]}`}
      >
        {badgeIcon}
        {badgeLabel}
      </span>

      <div className="mt-2 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1 text-left">
          <p className="text-[13px] font-medium text-card-foreground leading-snug">{title}</p>
          {description && (
            <p className="mt-1.5 text-[11px] text-muted-foreground leading-relaxed">
              {description}
            </p>
          )}
          {status && (
            <span className="mt-1.5 inline-block rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              {status}
            </span>
          )}
        </div>
        {tag && (
          <span className="shrink-0 rounded border border-border bg-muted/50 px-1.5 py-0.5 text-[10px] text-muted-foreground">
            {tag}
          </span>
        )}
      </div>

      {/* Target handles: visible dots at midpoint of each side (always visible so connectors are clear) */}
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className={`!top-0 !left-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !-translate-x-1/2 !-translate-y-1/2 ${targetHandleVisible}`}
        style={showTargetHandles ? { background: 'hsl(var(--primary) / 0.5)' } : undefined}
      />
      <Handle
        type="target"
        position={Position.Right}
        id="right"
        className={`!right-0 !top-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !translate-x-1/2 !-translate-y-1/2 ${targetHandleVisible}`}
        style={showTargetHandles ? { background: 'hsl(var(--primary) / 0.5)' } : undefined}
      />
      <Handle
        type="target"
        position={Position.Bottom}
        id="bottom"
        className={`!bottom-0 !left-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !-translate-x-1/2 !translate-y-1/2 ${targetHandleVisible}`}
        style={showTargetHandles ? { background: 'hsl(var(--primary) / 0.5)' } : undefined}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className={`!left-0 !top-1/2 !w-2.5 !h-2.5 !rounded-full !border-2 !border-card !-translate-x-1/2 !-translate-y-1/2 ${targetHandleVisible}`}
        style={showTargetHandles ? { background: 'hsl(var(--primary) / 0.5)' } : undefined}
      />

      {/* Source handles — provided by each node (single full-node handle or condition true/false) */}
      {children}
    </div>
  )
}
