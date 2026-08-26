import { useCallback, useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { createEmptyWorkflow, validateWorkflow, type Workflow } from '@/lib/workflow-builder'
import { NodePalette } from './NodePalette'
import { WorkflowBuilderCanvas } from './WorkflowBuilderCanvas'

export interface WorkflowBuilderProps {
  workflowId?: string
  initialName?: string
  onSave?: (workflow: Workflow) => void
  allowCircular?: boolean
}

export function WorkflowBuilder({
  workflowId = `wf-${crypto.randomUUID()}`,
  initialName = 'Untitled workflow',
  onSave,
  allowCircular = false,
}: WorkflowBuilderProps) {
  const workflowNameId = useId()
  const [workflow, setWorkflow] = useState<Workflow>(() =>
    createEmptyWorkflow(workflowId, initialName),
  )
  const [name, setName] = useState(initialName)

  const validation = validateWorkflow({ ...workflow, name })
  const handleWorkflowChange = useCallback((w: Workflow) => setWorkflow(w), [])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-[200px]">
          <label
            htmlFor={workflowNameId}
            className="block text-xs font-medium text-muted-foreground mb-1"
          >
            Workflow name
          </label>
          <Input
            id={workflowNameId}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Workflow name"
          />
        </div>
        {onSave && (
          <Button
            variant="primary"
            onClick={() => onSave({ ...workflow, name })}
            disabled={!validation.valid}
          >
            Save workflow
          </Button>
        )}
      </div>
      {!validation.valid && validation.errors.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
          <p className="font-medium mb-1">Validation</p>
          <ul className="list-disc list-inside space-y-0.5">
            {validation.errors.map((err) => (
              <li key={err}>{err}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-4">
        <NodePalette />
        <div className="flex-1 min-w-0">
          <WorkflowBuilderCanvas
            workflow={workflow}
            workflowId={workflowId}
            workflowName={name}
            onWorkflowChange={handleWorkflowChange}
            allowCircular={allowCircular}
          />
        </div>
      </div>
    </div>
  )
}
