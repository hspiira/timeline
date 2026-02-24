import { useState, useEffect } from 'react'
import type { WorkflowNode } from '@/lib/workflow-builder/types'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import { WORKFLOW_ACTION_TYPE_OPTIONS } from '@/lib/workflow-builder/action-types'
import {
  CONDITION_OPERATORS,
  simpleConditionToExpression,
  parseSimpleCondition,
  validateConditionExpression,
  type ConditionOperator,
} from '@/lib/workflow-builder/condition-builder'
import { Input } from '@/components/ui/input'
import { SingleSelectCombobox, optionsFromStrings } from '@/components/ui/combobox'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import SubjectSelector from '@/components/subjects/SubjectSelector'

function ConditionConfig({
  nodeId,
  expression,
  onUpdate,
}: {
  nodeId: string
  expression: string
  onUpdate: (updates: Record<string, unknown>) => void
}) {
  const [forceAdvanced, setForceAdvanced] = useState(false)
  useEffect(() => {
    setForceAdvanced(false)
  }, [nodeId])

  const parsed = expression.trim() ? parseSimpleCondition(expression) : null
  const showAdvanced = forceAdvanced || (expression.trim() !== '' && parsed === null)
  const field = parsed?.field ?? ''
  const operator: ConditionOperator = parsed?.operator ?? 'not_empty'
  const value = parsed?.value ?? ''

  const needsValue =
    operator !== 'empty' && operator !== 'not_empty'

  const handleSimpleChange = (newField: string, newOp: ConditionOperator, newValue: string) => {
    const expr = simpleConditionToExpression(newField, newOp, newValue)
    if (expr) onUpdate({ expression: expr })
  }

  if (showAdvanced) {
    const validation = validateConditionExpression(expression)
    return (
      <div className="space-y-2">
        <label className="block text-xs font-medium text-muted-foreground">
          If… (advanced)
        </label>
        <Input
          value={expression}
          onChange={(e) => onUpdate({ expression: e.target.value })}
          placeholder="e.g. payload.amount > 100"
          className={`font-mono text-sm ${!validation.valid ? 'border-destructive' : ''}`}
        />
        {!validation.valid && (
          <p className="text-xs text-destructive">{validation.error}</p>
        )}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={() => setForceAdvanced(false)}
        >
          Use simple rule
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-muted-foreground">
        When… (then follow Yes, else follow No)
      </label>
      <div className="space-y-1.5">
        <Input
          value={field}
          onChange={(e) => handleSimpleChange(e.target.value, operator, value)}
          placeholder="e.g. amount or status"
          className="text-sm"
        />
        <SingleSelectCombobox
          value={operator}
          onValueChange={(v) => handleSimpleChange(field, v as ConditionOperator, value)}
          options={CONDITION_OPERATORS.map((o) => ({ value: o.value, label: o.label }))}
          placeholder="Operator"
          className="w-full"
        />
        {needsValue && (
          <Input
            value={value}
            onChange={(e) => handleSimpleChange(field, operator, e.target.value)}
            placeholder={operator === 'contains' ? 'e.g. pending' : 'e.g. 100'}
            className="text-sm"
          />
        )}
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 text-xs text-muted-foreground"
        onClick={() => setForceAdvanced(true)}
      >
        Edit as expression
      </Button>
    </div>
  )
}

function ActionConfig({
  actionType,
  params,
  eventTypes,
  onUpdate,
}: {
  actionType: string
  params: Record<string, unknown>
  eventTypes: string[]
  onUpdate: (updates: Record<string, unknown>) => void
}) {
  const [showJson, setShowJson] = useState(false)
  const paramsStr = Object.keys(params).length === 0 ? '' : JSON.stringify(params, null, 2)

  if (showJson) {
    return (
      <div className="space-y-2">
        <label className="block text-xs font-medium text-muted-foreground">Settings (JSON)</label>
        <Textarea
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
          className="font-mono text-sm min-h-20"
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={() => setShowJson(false)}
        >
          Use form
        </Button>
      </div>
    )
  }

  if (actionType === 'create_event') {
    const event_type = (params.event_type as string) ?? ''
    const subject_id = (params.subject_id as string) ?? ''
    const rest = { ...params }
    delete rest.event_type
    delete rest.subject_id
    const payloadStr = Object.keys(rest).length === 0 ? '' : JSON.stringify(rest, null, 0)
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Event type</label>
          <SingleSelectCombobox
            value={event_type}
            onValueChange={(v) => onUpdate({ params: { ...params, event_type: v || undefined } })}
            options={optionsFromStrings(eventTypes, { value: '', label: 'Select event type' })}
            placeholder="Select event type"
            className="w-full"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Subject (optional)</label>
          <SubjectSelector
            value={subject_id}
            onChange={(v) => onUpdate({ params: { ...params, subject_id: v || undefined } })}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Extra payload (optional)</label>
          <Input
            value={payloadStr}
            onChange={(e) => {
              const raw = e.target.value.trim()
              if (!raw) {
                const next: Record<string, unknown> = {}
                if (params.event_type != null && params.event_type !== '') next.event_type = params.event_type
                if (params.subject_id != null && params.subject_id !== '') next.subject_id = params.subject_id
                onUpdate({ params: next })
                return
              }
              try {
                onUpdate({ params: { ...params, ...JSON.parse(raw) as Record<string, unknown> } })
              } catch {
                // allow typing
              }
            }}
            placeholder='{"key": "value"}'
            className="font-mono text-sm"
          />
        </div>
        <Button type="button" variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground" onClick={() => setShowJson(true)}>
          Edit as JSON
        </Button>
      </div>
    )
  }

  if (actionType === 'send_email') {
    const to = (params.to as string) ?? ''
    const subject = (params.subject as string) ?? ''
    const body = (params.body as string) ?? ''
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">To</label>
          <Input
            value={to}
            onChange={(e) => onUpdate({ params: { ...params, to: e.target.value } })}
            placeholder="email@example.com"
            className="text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Subject</label>
          <Input
            value={subject}
            onChange={(e) => onUpdate({ params: { ...params, subject: e.target.value } })}
            placeholder="Email subject"
            className="text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Body</label>
          <Textarea
            value={body}
            onChange={(e) => onUpdate({ params: { ...params, body: e.target.value } })}
            placeholder="Email body or template"
            className="text-sm min-h-16"
          />
        </div>
        <Button type="button" variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground" onClick={() => setShowJson(true)}>
          Edit as JSON
        </Button>
      </div>
    )
  }

  if (actionType === 'update_subject') {
    const subject_id = (params.subject_id as string) ?? ''
    const rest = { ...params }
    delete rest.subject_id
    const attributesStr = Object.keys(rest).length === 0 ? '' : JSON.stringify(rest, null, 0)
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Subject</label>
          <SubjectSelector
            value={subject_id}
            onChange={(v) => onUpdate({ params: { ...params, subject_id: v || undefined } })}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Attribute updates (optional)</label>
          <Input
            value={attributesStr}
            onChange={(e) => {
              const raw = e.target.value.trim()
              if (!raw) {
                onUpdate({ params: subject_id ? { subject_id } : {} })
                return
              }
              try {
                onUpdate({ params: { ...params, ...JSON.parse(raw) as Record<string, unknown> } })
              } catch {
                // allow typing
              }
            }}
            placeholder='{"status": "active"}'
            className="font-mono text-sm"
          />
        </div>
        <Button type="button" variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground" onClick={() => setShowJson(true)}>
          Edit as JSON
        </Button>
      </div>
    )
  }

  // Fallback: show JSON for unknown action types
  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-muted-foreground">Params (JSON)</label>
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
  )
}

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
        <label className="block text-xs font-medium text-muted-foreground">When event type</label>
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
      <ConditionConfig
        nodeId={node.id}
        expression={(node.configuration?.expression as string) ?? ''}
        onUpdate={onUpdate}
      />
    )
  }

  if (node.type === 'action') {
    const actionType = (node.configuration?.actionType as string) ?? 'create_event'
    const params = (node.configuration?.params as Record<string, unknown>) ?? {}
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">What this step does</label>
          <SingleSelectCombobox
            value={actionType}
            onValueChange={(v) => onUpdate({ actionType: v })}
            options={WORKFLOW_ACTION_TYPE_OPTIONS}
            placeholder="Action type"
            className="w-full"
          />
        </div>
        <ActionConfig
          actionType={actionType}
          params={params}
          eventTypes={eventTypes}
          onUpdate={onUpdate}
        />
      </div>
    )
  }

  if (node.type === 'integration_action') {
    const integration = (node.configuration?.integration as string) ?? ''
    const operation = (node.configuration?.operation as string) ?? ''
    return (
      <div className="space-y-2">
        <p className="text-[11px] text-muted-foreground/80">
          Connect to an external service (e.g. Slack, webhooks). Enter the integration name and the operation to run.
        </p>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Integration</label>
          <Input
            value={integration}
            onChange={(e) => onUpdate({ integration: e.target.value })}
            placeholder="e.g. slack, webhook, salesforce"
            className="text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Operation</label>
          <Input
            value={operation}
            onChange={(e) => onUpdate({ operation: e.target.value })}
            placeholder="e.g. post_message, send, create_record"
            className="text-sm"
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
