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

export function NodePalette() {
  const types = nodeRegistry.getAll()

  function onDragStart(e: React.DragEvent, nodeType: NodeType) {
    e.dataTransfer.setData('application/reactflow-node-type', nodeType)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div className="w-52 rounded-lg border border-border bg-background p-3 shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
        Nodes
      </h3>
      <div className="flex flex-col gap-1.5">
        {types.map((desc) => {
          const Icon = ICONS[desc.type]
          return (
            <div
              key={desc.type}
              draggable
              onDragStart={(ev) => onDragStart(ev, desc.type)}
              className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 cursor-grab active:cursor-grabbing text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
            >
              {Icon && <Icon className="w-4 h-4 shrink-0 text-muted-foreground" />}
              <span>{desc.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
