import { createFileRoute } from '@tanstack/react-router'
import { WorkflowBuilder } from '@/components/workflow-builder'
import type { Workflow } from '@/lib/workflow-builder'

export const Route = createFileRoute('/settings/workflows/builder')({
  component: WorkflowBuilderPage,
})

function WorkflowBuilderPage() {
  const handleSave = (workflow: Workflow) => {
    console.log('Save workflow', workflow)
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-foreground">Workflow builder</h1>
      <p className="text-sm text-muted-foreground">
        Drag nodes from the palette onto the canvas. Connect nodes from source (bottom) to target
        (top) handles. Condition nodes have two outputs: true (green) and false (red). Exactly one
        trigger and no orphan nodes required.
      </p>
      <WorkflowBuilder initialName="New workflow" onSave={handleSave} allowCircular={false} />
    </div>
  )
}
