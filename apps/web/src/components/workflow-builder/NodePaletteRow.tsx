import { CircleX, GitBranch, MousePointerClick, Play, Zap } from 'lucide-react'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import type { NodeType } from '@/lib/workflow-builder/types'

const NODE_META: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; color: string }
> = {
  trigger: { icon: Zap, color: 'text-emerald-600 dark:text-emerald-400' },
  action: { icon: MousePointerClick, color: 'text-amber-600 dark:text-amber-400' },
  condition: { icon: GitBranch, color: 'text-blue-600 dark:text-blue-400' },
  integration_action: { icon: Play, color: 'text-violet-600 dark:text-violet-400' },
  terminal: { icon: CircleX, color: 'text-rose-600 dark:text-rose-400' },
}

export function NodePaletteRow() {
  const types = nodeRegistry.getAll()

  function onDragStart(e: React.DragEvent, nodeType: NodeType) {
    e.dataTransfer.setData('application/reactflow-node-type', nodeType)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div className="flex flex-wrap items-center justify-center gap-1.5 rounded-lg border border-border bg-card/90 backdrop-blur-sm px-2 py-1.5">
      {types.map((desc) => {
        const meta = NODE_META[desc.type]
        const Icon = meta?.icon
        return (
          // biome-ignore lint/a11y/noStaticElementInteractions: a drag source; there is no click or key equivalent to give it.
          <div
            key={desc.type}
            draggable
            onDragStart={(ev) => onDragStart(ev, desc.type)}
            title={desc.label}
            className="flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1.5 cursor-grab active:cursor-grabbing text-muted-foreground hover:bg-muted/40 hover:text-foreground transition-all duration-150 shrink-0 touch-none active:scale-[0.97]"
          >
            {Icon && <Icon className={`w-3.5 h-3.5 shrink-0 ${meta.color}`} />}
            <span className="text-xs font-medium">{desc.label}</span>
          </div>
        )
      })}
    </div>
  )
}
