import { useEffect, useState } from 'react'
import SubjectSelector from '@/components/subjects/SubjectSelector'
import { Button } from '@/components/ui/button'
import { optionsFromStrings, SingleSelectCombobox } from '@/components/ui/combobox'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { WORKFLOW_ACTION_TYPE_OPTIONS } from '@/lib/workflow-builder/action-types'
import {
  CONDITION_OPERATORS,
  type ConditionOperator,
  parseSimpleCondition,
  simpleConditionToExpression,
  validateConditionExpression,
} from '@/lib/workflow-builder/condition-builder'
import { nodeRegistry } from '@/lib/workflow-builder/node-registry'
import type { WorkflowNode } from '@/lib/workflow-builder/types'

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

  const needsValue = operator !== 'empty' && operator !== 'not_empty'

  const handleSimpleChange = (newField: string, newOp: ConditionOperator, newValue: string) => {
    const expr = simpleConditionToExpression(newField, newOp, newValue)
    if (expr) onUpdate({ expression: expr })
  }

  if (showAdvanced) {
    const validation = validateConditionExpression(expression)
    return (
      <div className="space-y-2">
        <label className="block text-xs font-medium text-muted-foreground">If… (advanced)</label>
        <Input
          value={expression}
          onChange={(e) => onUpdate({ expression: e.target.value })}
          placeholder="e.g. payload.amount > 100"
          className={`font-mono text-sm ${!validation.valid ? 'border-destructive' : ''}`}
        />
        {!validation.valid && <p className="text-xs text-destructive">{validation.error}</p>}
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
  workflowContext,
  onUpdate,
}: {
  actionType: string
  params: Record<string, unknown>
  eventTypes: string[]
  workflowContext?: import('@/hooks/useWorkflowEngineContext').WorkflowEngineContextValue
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
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Subject (optional)
          </label>
          <SubjectSelector
            value={subject_id}
            onChange={(v) => onUpdate({ params: { ...params, subject_id: v || undefined } })}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Extra payload (optional)
          </label>
          <Input
            value={payloadStr}
            onChange={(e) => {
              const raw = e.target.value.trim()
              if (!raw) {
                const next: Record<string, unknown> = {}
                if (params.event_type != null && params.event_type !== '')
                  next.event_type = params.event_type
                if (params.subject_id != null && params.subject_id !== '')
                  next.subject_id = params.subject_id
                onUpdate({ params: next })
                return
              }
              try {
                onUpdate({ params: { ...params, ...(JSON.parse(raw) as Record<string, unknown>) } })
              } catch {
                // allow typing
              }
            }}
            placeholder='{"key": "value"}'
            className="font-mono text-sm"
          />
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={() => setShowJson(true)}
        >
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
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={() => setShowJson(true)}
        >
          Edit as JSON
        </Button>
      </div>
    )
  }

  if (actionType === 'create_relationship') {
    const relationshipKinds = workflowContext?.relationshipKinds ?? []
    const relationship_kind = (params.relationship_kind as string) ?? ''
    const source_subject_id = (params.source_subject_id as string) ?? ''
    const target_subject_id = (params.target_subject_id as string) ?? ''
    const options = relationshipKinds.map((r) => ({
      value: r.kind,
      label: r.display_name || r.kind,
    }))
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Relationship kind
          </label>
          <SingleSelectCombobox
            value={relationship_kind}
            onValueChange={(v) =>
              onUpdate({ params: { ...params, relationship_kind: v || undefined } })
            }
            options={[{ value: '', label: 'Select kind' }, ...options]}
            placeholder="Select relationship kind"
            className="w-full"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Source subject
          </label>
          <SubjectSelector
            value={source_subject_id}
            onChange={(v) => onUpdate({ params: { ...params, source_subject_id: v || undefined } })}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Target subject
          </label>
          <SubjectSelector
            value={target_subject_id}
            onChange={(v) => onUpdate({ params: { ...params, target_subject_id: v || undefined } })}
          />
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={() => setShowJson(true)}
        >
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
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Attribute updates (optional)
          </label>
          <Input
            value={attributesStr}
            onChange={(e) => {
              const raw = e.target.value.trim()
              if (!raw) {
                onUpdate({ params: subject_id ? { subject_id } : {} })
                return
              }
              try {
                onUpdate({ params: { ...params, ...(JSON.parse(raw) as Record<string, unknown>) } })
              } catch {
                // allow typing
              }
            }}
            placeholder='{"status": "active"}'
            className="font-mono text-sm"
          />
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={() => setShowJson(true)}
        >
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
  /** @deprecated Prefer workflowContext. When workflowContext is provided, eventTypes come from it. */
  eventTypes?: string[]
  /** Entity lists for the workflow builder (from useWorkflowEngineContext). When provided, used for all dropdowns. */
  workflowContext?: import('@/hooks/useWorkflowEngineContext').WorkflowEngineContextValue
  /** Optional step-specific tip from a workflow template (Attio-style). */
  templateStepTip?: string
  onUpdate: (updates: Record<string, unknown>) => void
}

function TipBlock({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-blue-200/80 bg-blue-50/80 dark:border-blue-800/60 dark:bg-blue-950/30 px-2.5 py-2 mb-3">
      <p className="text-[11px] text-blue-800 dark:text-blue-200 leading-relaxed">{text}</p>
    </div>
  )
}

export function NodeConfigPanel({
  node,
  eventTypes: eventTypesProp,
  workflowContext,
  templateStepTip,
  onUpdate,
}: NodeConfigPanelProps) {
  const desc = nodeRegistry.getOptional(node.type)
  if (!desc) return null

  const eventTypes = workflowContext?.eventTypes ?? eventTypesProp ?? []
  const tip = templateStepTip ?? desc.tip

  if (desc.isTrigger) {
    const eventType = (node.configuration?.eventType as string) ?? ''
    const transitionRule = workflowContext?.transitionRules?.find((r) => r.event_type === eventType)
    const requiredPrior = transitionRule?.required_prior_event_types ?? []
    return (
      <div className="space-y-2">
        {tip && <TipBlock text={tip} />}
        <label className="block text-xs font-medium text-muted-foreground">When event type</label>
        <SingleSelectCombobox
          value={eventType}
          onValueChange={(v) => onUpdate({ eventType: v })}
          options={optionsFromStrings(eventTypes, { value: '', label: 'When event type…' })}
          placeholder="When event type…"
          className="w-full"
        />
        {requiredPrior.length > 0 && (
          <p className="text-[11px] text-muted-foreground">
            Required prior events: {requiredPrior.join(', ')}
          </p>
        )}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Description (optional)
          </label>
          <Input
            value={(node.configuration?.description as string) ?? ''}
            onChange={(e) => onUpdate({ description: e.target.value })}
            placeholder="e.g. When subscription is cancelled"
            className="text-sm"
          />
        </div>
      </div>
    )
  }

  if (desc.isCondition) {
    return (
      <>
        {tip && <TipBlock text={tip} />}
        <ConditionConfig
          nodeId={node.id}
          expression={(node.configuration?.expression as string) ?? ''}
          onUpdate={onUpdate}
        />
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1 mt-2">
            Description (optional)
          </label>
          <Input
            value={(node.configuration?.description as string) ?? ''}
            onChange={(e) => onUpdate({ description: e.target.value })}
            placeholder="e.g. Did status change to cancelled?"
            className="text-sm"
          />
        </div>
      </>
    )
  }

  if (node.type === 'action') {
    const actionType = (node.configuration?.actionType as string) ?? 'create_event'
    const params = (node.configuration?.params as Record<string, unknown>) ?? {}
    return (
      <div className="space-y-3">
        {tip && <TipBlock text={tip} />}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            What this step does
          </label>
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
          workflowContext={workflowContext}
          onUpdate={onUpdate}
        />
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Description (optional)
          </label>
          <Input
            value={(node.configuration?.description as string) ?? ''}
            onChange={(e) => onUpdate({ description: e.target.value })}
            placeholder="e.g. Create follow-up event"
            className="text-sm"
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
        <p className="text-[11px] text-muted-foreground/80">
          Connect to an external service (e.g. Slack, webhooks). Enter the integration name and the
          operation to run.
        </p>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Integration
          </label>
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

  return <p className="text-xs text-muted-foreground">{desc.label} – no configuration.</p>
}
