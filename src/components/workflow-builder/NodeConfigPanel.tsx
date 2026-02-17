import type { WorkflowNode } from '@/lib/workflow-builder/types'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import { WORKFLOW_ACTION_TYPE_OPTIONS } from '@/lib/workflow-builder/action-types'
import { Input } from '@/components/ui/input'
import { SingleSelectCombobox, optionsFromStrings } from '@/components/ui/combobox'

export interface NodeConfigPanelProps {
  node: WorkflowNode
  eventTypes: string[]
  onUpdate: (updates: Record<string, unknown>) => void
}

export function NodeConfigPanel({ node, eventTypes, onUpdate }: NodeConfigPanelProps) {
  const desc = nodeRegistry.getOptional(node.type)
  if (!desc) return null

  if (desc.isTrigger) {
    return (
      <div className="space-y-2">
        <label className="block text-xs font-medium text-muted-foreground">Trigger event type</label>
        <SingleSelectCombobox
          value={(node.configuration?.eventType as string) ?? ''}
          onValueChange={(v) => onUpdate({ eventType: v })}
          options={optionsFromStrings(eventTypes, { value: '', label: 'When event type…' })}
          placeholder="When event type…"
          className="w-full"
        />
      </div>
    )
  }

  if (desc.isCondition) {
    return (
      <div className="space-y-2">
        <label className="block text-xs font-medium text-muted-foreground">Condition expression</label>
        <Input
          value={(node.configuration?.expression as string) ?? ''}
          onChange={(e) => onUpdate({ expression: e.target.value })}
          placeholder="e.g. payload.amount > 100"
          className="font-mono text-sm"
        />
      </div>
    )
  }

  if (node.type === 'action') {
    const actionType = (node.configuration?.actionType as string) ?? 'create_event'
    const params = (node.configuration?.params as Record<string, unknown>) ?? {}
    const paramsStr = Object.keys(params).length === 0 ? '' : JSON.stringify(params, null, 0)
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Action type</label>
          <SingleSelectCombobox
            value={actionType}
            onValueChange={(v) => onUpdate({ actionType: v })}
            options={WORKFLOW_ACTION_TYPE_OPTIONS}
            placeholder="Action type"
            className="w-full"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Params (JSON)</label>
          <Input
            value={paramsStr}
            onChange={(e) => {
              const raw = e.target.value.trim()
              if (!raw) {
                onUpdate({ params: {} })
                return
              }
              try {
                onUpdate({ params: JSON.parse(raw) as Record<string, unknown> })
              } catch {
                // allow typing
              }
            }}
            placeholder='{"key": "value"}'
            className="font-mono text-sm"
          />
        </div>
      </div>
    )
  }

  if (node.type === 'integration_action') {
    const integration = (node.configuration?.integration as string) ?? ''
    const operation = (node.configuration?.operation as string) ?? ''
    return (
      <div className="space-y-2">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Integration</label>
          <Input
            value={integration}
            onChange={(e) => onUpdate({ integration: e.target.value })}
            placeholder="e.g. slack"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Operation</label>
          <Input
            value={operation}
            onChange={(e) => onUpdate({ operation: e.target.value })}
            placeholder="e.g. post_message"
          />
        </div>
      </div>
    )
  }

  return (
    <p className="text-xs text-muted-foreground">
      {desc.label} – no configuration.
    </p>
  )
}
