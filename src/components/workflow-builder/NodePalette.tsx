import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import type { NodeType } from '@/lib/workflow-builder/types'
import { Zap, MousePointerClick, GitBranch, Play, CircleX } from 'lucide-react'

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

export function NodePalette() {
  const types = nodeRegistry.getAll()

  function onDragStart(e: React.DragEvent, nodeType: NodeType) {
    e.dataTransfer.setData('application/reactflow-node-type', nodeType)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div className="w-52 rounded-xl border border-border bg-card p-3">
      <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-3">
        Nodes
      </h3>
      <div className="flex flex-col gap-1.5">
        {types.map((desc) => {
          const meta = NODE_META[desc.type]
          const Icon = meta?.icon
          return (
            <div
              key={desc.type}
              draggable
              onDragStart={(ev) => onDragStart(ev, desc.type)}
              className="flex items-center gap-2.5 rounded-lg border border-border bg-background px-3 py-2 cursor-grab active:cursor-grabbing text-sm font-medium text-foreground hover:bg-muted/40 hover:border-muted-foreground/20 transition-all duration-150 active:scale-[0.97]"
            >
              {Icon && <Icon className={`w-4 h-4 shrink-0 ${meta.color}`} />}
              <span className="text-[13px]">{desc.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
