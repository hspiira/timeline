import { Handle, Position, useConnection } from '@xyflow/react'
import type { ReactNode } from 'react'

export type BadgeVariant = 'emerald' | 'amber' | 'blue' | 'violet' | 'rose'

const BADGE_COLORS: Record<BadgeVariant, string> = {
  emerald:
    'bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60',
  amber:
    'bg-amber-50 text-amber-700 border-amber-200/80 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60',
  blue:
    'bg-blue-50 text-blue-700 border-blue-200/80 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/60',
  violet:
    'bg-violet-50 text-violet-700 border-violet-200/80 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-800/60',
  rose:
    'bg-rose-50 text-rose-700 border-rose-200/80 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60',
}

export const HANDLE_CLASS =
  '!w-[9px] !h-[9px] !bg-muted-foreground/40 !border-2 !border-card !transition-all !duration-150'
export const HANDLE_TARGET_CLASS =
  '!w-[9px] !h-[9px] !bg-primary/50 !border-2 !border-card !transition-all !duration-150'

interface WorkflowNodeShellProps {
  badgeLabel: string
  badgeIcon: ReactNode
  badgeVariant: BadgeVariant
  title: string
  description?: string
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
  selected,
  children,
}: WorkflowNodeShellProps) {
  const connection = useConnection()
  const isConnecting = connection?.inProgress === true

  return (
    <div
      className={`workflow-node-card relative w-[220px] rounded-xl border bg-card px-4 pt-2 pb-3 text-center ${
        selected ? 'border-ring/60 ring-2 ring-ring/30' : 'border-border'
      }`}
    >
      {/* Badge inside card so node bounds = card */}
      <span
        className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-[3px] text-[10px] font-semibold leading-none select-none ${BADGE_COLORS[badgeVariant]}`}
      >
        {badgeIcon}
        {badgeLabel}
      </span>

      <p className="mt-2 text-[13px] font-medium text-card-foreground leading-snug">{title}</p>
      {description && (
        <p className="mt-1.5 text-[11px] text-muted-foreground leading-relaxed">{description}</p>
      )}

      {/* Target handles on all four sides — explicit ids so edges can resolve; always in DOM */}
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className={`${HANDLE_TARGET_CLASS} ${!isConnecting ? '!opacity-0 pointer-events-none' : ''}`}
      />
      <Handle
        type="target"
        position={Position.Right}
        id="right"
        className={`${HANDLE_TARGET_CLASS} ${!isConnecting ? '!opacity-0 pointer-events-none' : ''}`}
      />
      <Handle
        type="target"
        position={Position.Bottom}
        id="bottom"
        className={`${HANDLE_TARGET_CLASS} ${!isConnecting ? '!opacity-0 pointer-events-none' : ''}`}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className={`${HANDLE_TARGET_CLASS} ${!isConnecting ? '!opacity-0 pointer-events-none' : ''}`}
      />

      {/* Source handles — provided by each node (all four sides where applicable) */}
      {children}
    </div>
  )
}
