import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import type { NodeType } from '@/lib/workflow-builder/types'
import { Zap, GitBranch, Plug, Square } from 'lucide-react'

const ICONS: Partial<Record<NodeType, React.ComponentType<{ className?: string }>>> = {
  trigger: Zap,
  action: Zap,
  integration_action: Plug,
  condition: GitBranch,
  terminal: Square,
}

export function NodePaletteRow() {
  const types = nodeRegistry.getAll()

  function onDragStart(e: React.DragEvent, nodeType: NodeType) {
    e.dataTransfer.setData('application/reactflow-node-type', nodeType)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div className="flex flex-wrap items-center justify-center gap-1.5 rounded-lg border border-border bg-background/95 px-2 py-1.5">
      {types.map((desc) => {
        const Icon = ICONS[desc.type]
        return (
          <div
            key={desc.type}
            role="button"
            draggable
            onDragStart={(ev) => onDragStart(ev, desc.type)}
            title={desc.label}
            className="flex items-center gap-1.5 rounded-md border border-border bg-muted/30 px-2 py-1.5 cursor-grab active:cursor-grabbing text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors shrink-0 touch-none"
          >
            {Icon && <Icon className="w-4 h-4 shrink-0" />}
            <span className="text-xs font-medium">{desc.label}</span>
          </div>
        )
      })}
    </div>
  )
}
