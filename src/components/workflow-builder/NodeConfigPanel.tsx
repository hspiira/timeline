import type { WorkflowNode } from '@/lib/workflow-builder/types'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'

const ACTION_TYPE_OPTIONS = [
  { value: 'create_event', label: 'Create Event' },
  { value: 'send_email', label: 'Send Email' },
  { value: 'update_subject', label: 'Update Subject' },
] as const

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
        <Select
          value={(node.configuration?.eventType as string) ?? ''}
          onChange={(e) => onUpdate({ eventType: e.target.value })}
          className="w-full"
        >
          <option value="">When event type…</option>
          {eventTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
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
          <Select
            value={actionType}
            onChange={(e) => onUpdate({ actionType: e.target.value })}
            className="w-full"
          >
            {ACTION_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
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
